"""Face detection, quality, and liveness analysis."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image
from insightface.app import FaceAnalysis

# Ensure DEEPFACE_HOME points to existing local weights if default user path is restricted
_local_deepface = Path(__file__).resolve().parent.parent / ".deepface"
if _local_deepface.is_dir() and "DEEPFACE_HOME" not in os.environ:
    os.environ["DEEPFACE_HOME"] = str(_local_deepface)

from deepface import DeepFace

from app.quality import assess_face_quality


_face_analyzer: FaceAnalysis | None = None


def _get_face_analyzer() -> FaceAnalysis:
    """Load InsightFace's SCRFD-10G detector once per process."""
    global _face_analyzer
    if _face_analyzer is None:
        # The buffalo_l model pack uses SCRFD-10GF for face detection. InsightFace
        # downloads the pack on first use into its standard model cache.
        _face_analyzer = FaceAnalysis(
            name="buffalo_l",
            allowed_modules=["detection"],
            providers=["CPUExecutionProvider"],
        )
        # SCRFD scores can vary substantially with input scale. Run both a
        # smaller and standard input and let SCRFD's NMS keep the strongest box.
        _face_analyzer.prepare(ctx_id=-1, det_size=[(320, 320), (640, 640)])
    return _face_analyzer


class FaceAnalysisError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _read_image(file_bytes: bytes) -> np.ndarray:
    if not file_bytes:
        raise FaceAnalysisError("Empty upload", 400)
    if len(file_bytes) > 10 * 1024 * 1024:
        raise FaceAnalysisError("Image too large (max 10 MB)", 413)

    try:
        pil = Image.open(io.BytesIO(file_bytes))
        pil = pil.convert("RGB")
    except Exception as exc:
        raise FaceAnalysisError("Invalid image file") from exc

    rgb = np.array(pil)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _xy(point: Any) -> tuple[int, int] | None:
    if point is None or len(point) < 2:
        return None
    return int(point[0]), int(point[1])


def analyze_image(file_bytes: bytes) -> dict[str, Any]:
    image_bgr = _read_image(file_bytes)
    img_h, img_w = image_bgr.shape[:2]

    try:
        detected_faces = _get_face_analyzer().get(image_bgr)
    except Exception as exc:
        raise FaceAnalysisError(f"Face analysis failed: {exc}", 500) from exc

    if not detected_faces:
        return {
            "face_detected": False,
            "face_count": 0,
            "image_size": {"width": img_w, "height": img_h},
            "quality": None,
            "liveness": None,
            "acceptable_for_enrollment": False,
            "message": "No face detected. Use a clear front-facing photo with good lighting.",
        }

    if len(detected_faces) > 1:
        return {
            "face_detected": True,
            "face_count": len(detected_faces),
            "image_size": {"width": img_w, "height": img_h},
            "quality": {"acceptable": False, "issues": ["Multiple faces detected (only 1 face allowed)"]},
            "liveness": None,
            "acceptable_for_enrollment": False,
            "message": "Exactly one face is required.",
        }

    face = detected_faces[0]
    x1, y1, x2, y2 = (int(round(float(value))) for value in face.bbox)
    x, y = max(0, x1), max(0, y1)
    w, h = min(img_w, x2) - x, min(img_h, y2) - y
    confidence = float(face.det_score)
    landmarks = face.kps
    left_eye = _xy(landmarks[0]) if landmarks is not None else None
    right_eye = _xy(landmarks[1]) if landmarks is not None else None

    quality = assess_face_quality(
        image_bgr,
        x,
        y,
        w,
        h,
        confidence,
        left_eye=left_eye,
        right_eye=right_eye,
    )
    # Keep DeepFace's FasNet liveness check, running it on the SCRFD face crop.
    crop = image_bgr[y : y + h, x : x + w]
    try:
        spoof_result = DeepFace.extract_faces(
            img_path=crop,
            detector_backend="skip",
            enforce_detection=False,
            align=False,
            anti_spoofing=True,
        )[0]
    except Exception as exc:
        raise FaceAnalysisError(f"Liveness analysis failed: {exc}", 500) from exc
    is_real = bool(spoof_result.get("is_real", False))
    antispoof_score = float(spoof_result.get("antispoof_score") or 0.0)

    liveness_passed = is_real
    enrollment_ok = quality.acceptable and liveness_passed and quality.eyes_open

    if not liveness_passed:
        message = "Spoof or non-live face detected. Use a real person, not a photo or screen."
    elif not quality.eyes_open:
        message = "Image rejected: Eyes are closed or not looking at the camera. Both eyes must be clearly open."
    elif not quality.acceptable:
        message = "Face detected but image quality is not good enough for enrollment."
    else:
        message = "Face passed quality and liveness checks."

    return {
        "face_detected": True,
        "face_count": 1,
        "image_size": {"width": img_w, "height": img_h},
        "facial_area": {"x": x, "y": y, "width": w, "height": h},
        "quality": {
            "acceptable": quality.acceptable,
            "score": quality.score,
            "issues": quality.issues,
            "blur_variance": quality.blur_variance,
            "brightness": quality.brightness,
            "face_size_px": {"width": quality.face_width, "height": quality.face_height},
            "face_area_ratio": quality.face_area_ratio,
            "detection_confidence": quality.detection_confidence,
            "eyes_open": quality.eyes_open,
            "left_eye_open": quality.left_eye_open,
            "right_eye_open": quality.right_eye_open,
            "left_eye_score": quality.left_eye_score,
            "right_eye_score": quality.right_eye_score,
            "eyes_detected": quality.eyes_detected,
            "eye_openness": quality.eye_openness,
        },
        "liveness": {
            "is_live": is_real,
            "is_real": is_real,
            "antispoof_score": round(antispoof_score, 4),
            "passed": liveness_passed,
        },
        "acceptable_for_enrollment": enrollment_ok,
        "message": message,
    }
