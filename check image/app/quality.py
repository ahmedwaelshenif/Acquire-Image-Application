"""Face-image quality and eye openness assessment for enrollment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

MIN_FACE_WIDTH = 80
MIN_FACE_HEIGHT = 80
MIN_FACE_AREA_RATIO = 0.04
MIN_BLUR_VARIANCE = 50.0
BRIGHTNESS_MIN = 45.0
BRIGHTNESS_MAX = 215.0
MIN_DETECTION_CONFIDENCE = 0.80

# Threshold for eyes to be considered open (0.0 to 1.0 probability)
MIN_EYE_OPEN_SCORE = 0.50

_EYE_CASCADE: cv2.CascadeClassifier | None = None
_ONNX_SESSION: Any = None
_ONNX_INPUT_NAME: str | None = None


@dataclass
class QualityResult:
    acceptable: bool
    score: float
    issues: list[str] = field(default_factory=list)
    blur_variance: float = 0.0
    brightness: float = 0.0
    face_width: int = 0
    face_height: int = 0
    face_area_ratio: float = 0.0
    detection_confidence: float = 0.0
    eyes_open: bool = False
    left_eye_open: bool = False
    right_eye_open: bool = False
    left_eye_score: float = 0.0
    right_eye_score: float = 0.0
    eyes_detected: int = 0
    eye_openness: float = 0.0


def _laplacian_variance(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _eye_cascade() -> cv2.CascadeClassifier | None:
    global _EYE_CASCADE
    if _EYE_CASCADE is not None:
        return _EYE_CASCADE

    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir / "haarcascade_eye.xml",
        base_dir / "models" / "haarcascade_eye.xml",
        base_dir.parent / "app" / "haarcascade_eye.xml",
        base_dir.parent / ".deepface" / "weights" / "haarcascade_eye.xml",
        base_dir.parent / ".deepface" / ".deepface" / "weights" / "haarcascade_eye.xml",
        Path.home() / ".deepface" / "weights" / "haarcascade_eye.xml",
        Path(getattr(cv2.data, "haarcascades", "")) / "haarcascade_eye.xml",
    ]
    for path in candidates:
        if path.is_file():
            cascade = cv2.CascadeClassifier(str(path))
            if not cascade.empty():
                _EYE_CASCADE = cascade
                return cascade
    return None


def _get_onnx_eye_session() -> tuple[Any, str | None]:
    """Load the ONNX eye-state MobileNetV2 classifier."""
    global _ONNX_SESSION, _ONNX_INPUT_NAME
    if _ONNX_SESSION is not None:
        return _ONNX_SESSION, _ONNX_INPUT_NAME

    try:
        import onnxruntime as ort

        base_dir = Path(__file__).resolve().parent
        model_paths = [
            base_dir / "models" / "eye_state_mobilenet_v2.onnx",
            base_dir / "eye_state_mobilenet_v2.onnx",
            base_dir.parent / "app" / "models" / "eye_state_mobilenet_v2.onnx",
        ]
        for p in model_paths:
            if p.is_file():
                opts = ort.SessionOptions()
                opts.intra_op_num_threads = 2
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                session = ort.InferenceSession(
                    str(p), opts, providers=["CPUExecutionProvider"]
                )
                input_name = session.get_inputs()[0].name
                _ONNX_SESSION = session
                _ONNX_INPUT_NAME = input_name
                return session, input_name
    except Exception:
        pass
    return None, None


def _classify_eye_onnx(crop_bgr: np.ndarray) -> float | None:
    """Classify eye crop as open (0.0 to 1.0) using MobileNetV2 ONNX model."""
    session, input_name = _get_onnx_eye_session()
    if session is None or input_name is None:
        return None

    h, w = crop_bgr.shape[:2]
    if h < 6 or w < 6:
        return 0.0

    try:
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        # MobileNetV2 image processor: resize shortest edge to 256, center crop 224
        if h < w:
            new_h = 256
            new_w = max(224, int(w * (256.0 / max(h, 1))))
        else:
            new_w = 256
            new_h = max(224, int(h * (256.0 / max(w, 1))))
        resized = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        start_y = max(0, (new_h - 224) // 2)
        start_x = max(0, (new_w - 224) // 2)
        crop = resized[start_y : start_y + 224, start_x : start_x + 224].astype(np.float32)
        if crop.shape[0] != 224 or crop.shape[1] != 224:
            crop = cv2.resize(crop, (224, 224), interpolation=cv2.INTER_LINEAR)

        # Rescale [0, 255] -> [0.0, 1.0] and normalize with mean=0.5, std=0.5
        norm = (crop * 0.00392156862745098 - 0.5) / 0.5
        chw = np.transpose(norm, (2, 0, 1))
        tensor = np.expand_dims(chw, axis=0)

        outputs = session.run(None, {input_name: tensor})
        logits = outputs[0][0]
        # Softmax
        exp = np.exp(logits - np.max(logits))
        probs = exp / np.sum(exp)
        # Class 0: Closed, Class 1: Open
        open_prob = float(probs[1])
        return max(0.0, min(1.0, open_prob))
    except Exception:
        return None


def _cv_eye_openness_heuristic(eye_bgr: np.ndarray) -> float:
    """Analyze eye crop using computer vision gradients and iris contrast."""
    if eye_bgr.size == 0:
        return 0.0
    gray = cv2.cvtColor(eye_bgr, cv2.COLOR_BGR2GRAY) if eye_bgr.ndim == 3 else eye_bgr
    h, w = gray.shape
    if h < 8 or w < 8:
        return 0.0

    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # 1. Edge orientation ratio:
    # Closed eyes have a horizontal eyelid line (high dy, very low dx).
    # Open eyes have strong vertical edges at the iris margins (high dx).
    dy = np.abs(cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3))
    dx = np.abs(cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3))
    dx_mean = float(dx.mean())
    dy_mean = float(dy.mean())
    edge_ratio = dx_mean / (dy_mean + 1e-6)

    # 2. Horizontal iris contrast (center dark pupil vs lateral sclera/skin):
    c1, c2 = int(w * 0.30), int(w * 0.70)
    center = gray[:, c1:c2]
    sides = np.hstack([gray[:, : int(w * 0.25)], gray[:, int(w * 0.75) :]])
    iris_contrast = float(sides.mean() - center.mean())

    # Map edge ratio (0.5 to 1.1) and contrast (0 to 30) to [0, 1]
    er_score = max(0.0, min(1.0, (edge_ratio - 0.55) / 0.40))
    contrast_score = max(0.0, min(1.0, (iris_contrast - 10.0) / 25.0))

    combined = 0.6 * er_score + 0.4 * contrast_score
    return round(float(combined), 3)


def _score_single_eye(crop: np.ndarray) -> float:
    """Evaluate openness score (0.0 to 1.0) for an eye crop."""
    if crop is None or crop.size == 0:
        return 0.0

    onnx_score = _classify_eye_onnx(crop)
    heuristic_score = _cv_eye_openness_heuristic(crop)

    if onnx_score is not None:
        # Give primary weight to trained deep learning model, with heuristic guard
        final_score = 0.75 * onnx_score + 0.25 * heuristic_score
    else:
        final_score = heuristic_score

    return round(float(max(0.0, min(1.0, final_score))), 3)


def assess_eyes(
    image_bgr: np.ndarray,
    x: int,
    y: int,
    w: int,
    h: int,
    left_eye: tuple[int, int] | None = None,
    right_eye: tuple[int, int] | None = None,
) -> tuple[bool, bool, bool, float, float, int, list[str]]:
    """Assess whether both eyes are open.

    Returns:
        (both_open, left_open, right_open, left_score, right_score, detected_count, issues)
    """
    img_h, img_w = image_bgr.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(img_w, x + w), min(img_h, y + h)
    face = image_bgr[y0:y1, x0:x1]
    if face.size == 0:
        return False, False, False, 0.0, 0.0, 0, ["Could not crop face region to check eyes"]

    fh, fw = face.shape[:2]

    # Anatomical eye ROIs in a standard face crop:
    # Eyes are located between 0.32 and 0.52 of face height (below eyebrows, above cheekbones).
    # Viewer-left eye: x: 0.16 to 0.44 of face width.
    # Viewer-right eye: x: 0.56 to 0.84 of face width.
    ey1, ey2 = int(0.32 * fh), int(0.52 * fh)
    left_x1, left_x2 = int(0.16 * fw), int(0.44 * fw)
    right_x1, right_x2 = int(0.56 * fw), int(0.84 * fw)

    left_roi = face[ey1:ey2, left_x1:left_x2]
    right_roi = face[ey1:ey2, right_x1:right_x2]

    # If landmarks are provided, also crop around landmark points
    if left_eye is not None:
        lx, ly = left_eye
        rw, rh = max(16, w // 8), max(12, h // 10)
        l_crop = image_bgr[
            max(0, ly - rh) : min(img_h, ly + rh),
            max(0, lx - rw) : min(img_w, lx + rw),
        ]
        if l_crop.size > 0:
            left_roi = l_crop

    if right_eye is not None:
        rx, ry = right_eye
        rw, rh = max(16, w // 8), max(12, h // 10)
        r_crop = image_bgr[
            max(0, ry - rh) : min(img_h, ry + rh),
            max(0, rx - rw) : min(img_w, rx + rw),
        ]
        if r_crop.size > 0:
            right_roi = r_crop

    # Score each eye independently
    left_score = _score_single_eye(left_roi)
    right_score = _score_single_eye(right_roi)

    # Check Haar detector detections
    cascade = _eye_cascade()
    detected_count = 0
    if cascade is not None:
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        min_size = (max(12, fw // 10), max(8, fh // 14))
        eyes = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=min_size,
        )
        # Keep detections within the eye vertical band (0.25 to 0.58)
        valid_boxes = [b for b in eyes if 0.25 * fh <= (b[1] + b[3] / 2) <= 0.58 * fh]
        detected_count = len(valid_boxes)

    left_open = left_score >= MIN_EYE_OPEN_SCORE
    right_open = right_score >= MIN_EYE_OPEN_SCORE
    both_open = left_open and right_open

    issues: list[str] = []
    if not both_open:
        if not left_open and not right_open:
            issues.append(
                f"Eyes appear closed (openness scores: Left {left_score:.2f}, Right {right_score:.2f}; need >= {MIN_EYE_OPEN_SCORE:.2f}). Please keep both eyes open."
            )
        elif not left_open:
            issues.append(
                f"Left eye appears closed or looking down (openness {left_score:.2f}; need >= {MIN_EYE_OPEN_SCORE:.2f}). Please look directly at camera with both eyes open."
            )
        elif not right_open:
            issues.append(
                f"Right eye appears closed or looking down (openness {right_score:.2f}; need >= {MIN_EYE_OPEN_SCORE:.2f}). Please look directly at camera with both eyes open."
            )

    return (
        both_open,
        left_open,
        right_open,
        left_score,
        right_score,
        detected_count,
        issues,
    )


def assess_face_quality(
    image_bgr: np.ndarray,
    x: int,
    y: int,
    w: int,
    h: int,
    detection_confidence: float,
    left_eye: tuple[int, int] | None = None,
    right_eye: tuple[int, int] | None = None,
) -> QualityResult:
    img_h, img_w = image_bgr.shape[:2]
    issues: list[str] = []
    score_parts: list[float] = []

    face_width, face_height = w, h
    face_area_ratio = (w * h) / max(img_w * img_h, 1)

    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(img_w, x + w), min(img_h, y + h)
    crop = image_bgr[y0:y1, x0:x1]
    if crop.size == 0:
        return QualityResult(
            acceptable=False,
            score=0.0,
            issues=["Invalid face crop"],
            detection_confidence=detection_confidence,
        )

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blur_var = _laplacian_variance(gray)
    brightness = float(np.mean(gray))

    if face_width < MIN_FACE_WIDTH or face_height < MIN_FACE_HEIGHT:
        issues.append(
            f"Face too small ({face_width}x{face_height}px; need at least {MIN_FACE_WIDTH}x{MIN_FACE_HEIGHT})"
        )
    else:
        score_parts.append(min(1.0, face_width / 200.0))

    if face_area_ratio < MIN_FACE_AREA_RATIO:
        issues.append(
            f"Face occupies too little of the frame ({face_area_ratio:.1%}; need at least {MIN_FACE_AREA_RATIO:.0%})"
        )
    else:
        score_parts.append(min(1.0, face_area_ratio / 0.2))

    if blur_var < MIN_BLUR_VARIANCE:
        issues.append(f"Image appears blurry (sharpness {blur_var:.1f}; need at least {MIN_BLUR_VARIANCE:.0f})")
    else:
        score_parts.append(min(1.0, blur_var / 300.0))

    if brightness < BRIGHTNESS_MIN:
        issues.append(f"Too dark (brightness {brightness:.0f}; need at least {BRIGHTNESS_MIN:.0f})")
    elif brightness > BRIGHTNESS_MAX:
        issues.append(f"Too bright or washed out (brightness {brightness:.0f}; max is {BRIGHTNESS_MAX:.0f})")
    else:
        score_parts.append(1.0)

    if detection_confidence < MIN_DETECTION_CONFIDENCE:
        issues.append(f"Low face detection confidence ({detection_confidence:.2f})")
    else:
        score_parts.append(detection_confidence)

    # Eye openness validation
    (
        both_open,
        left_open,
        right_open,
        left_score,
        right_score,
        eyes_detected,
        eye_issues,
    ) = assess_eyes(image_bgr, x, y, w, h, left_eye=left_eye, right_eye=right_eye)

    issues.extend(eye_issues)
    avg_openness = round(float((left_score + right_score) / 2.0), 3)

    if both_open:
        score_parts.append(avg_openness)

    score = sum(score_parts) / len(score_parts) if score_parts else 0.0
    acceptable = len(issues) == 0 and both_open

    return QualityResult(
        acceptable=acceptable,
        score=round(score, 3),
        issues=issues,
        blur_variance=round(blur_var, 2),
        brightness=round(brightness, 1),
        face_width=face_width,
        face_height=face_height,
        face_area_ratio=round(face_area_ratio, 4),
        detection_confidence=round(detection_confidence, 3),
        eyes_open=both_open,
        left_eye_open=left_open,
        right_eye_open=right_open,
        left_eye_score=left_score,
        right_eye_score=right_score,
        eyes_detected=eyes_detected,
        eye_openness=avg_openness,
    )
