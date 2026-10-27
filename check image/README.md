# Face liveness & quality API

FastAPI service that detects a face, checks whether the image is good enough for enrollment (size, sharpness, lighting), and runs passive anti-spoofing (DeepFace FasNet).

## Setup

```powershell
cd "C:\Users\Ahmed Hashem\Desktop\check image"
py -3 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

The first run downloads face detection and anti-spoof model weights (may take a few minutes).

## Run

On Windows, use the helper script (sets UTF-8 so DeepFace can download models):

```powershell
.\run.ps1
```

Or manually:

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) for the test page.

## API

**POST** `/api/verify` — multipart form field `image` (JPEG/PNG).

**GET** `/health` — readiness check.

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
