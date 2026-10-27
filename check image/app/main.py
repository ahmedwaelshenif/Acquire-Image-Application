from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.face_service import FaceAnalysisError, analyze_image

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"

app = FastAPI(
    title="Face Liveness & Quality API",
    description="Detect face, assess image quality, and run passive anti-spoofing.",
    version="1.0.0",
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    index_path = STATIC_DIR / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    return {"message": "Upload POST /api/verify with form field 'image'"}


@app.post("/api/verify")
async def verify_face(image: UploadFile = File(...)):
    if not image.content_type or not image.content_type.startswith("image/"):
        return JSONResponse(
            status_code=400,
            content={"error": "Upload must be an image (image/jpeg, image/png, etc.)"},
        )

    data = await image.read()
    try:
        result = analyze_image(data)
    except FaceAnalysisError as exc:
        return JSONResponse(status_code=exc.status_code, content={"error": str(exc)})

    return {
        "success": True,
        "passed": result.get("acceptable_for_enrollment", False),
        **result,
    }
