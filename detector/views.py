from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .utils import predict_image, predict_video
import cv2
import numpy as np
from django.middleware.csrf import get_token
import tempfile
import os

def home(request):
    # ensure CSRF cookie is set on the response so JS can read it
    get_token(request)
    return render(request, "index.html")

def upload_image(request):
    if request.method == "POST":
        file = request.FILES["file"]
        img = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(img, cv2.IMREAD_COLOR)

        result = predict_image(img)

        _, buffer = cv2.imencode(".jpg", result)
        return HttpResponse(buffer.tobytes(), content_type="image/jpeg")

    return JsonResponse({"error": "POST only"})


def upload_video(request):
    """Process uploaded video with YOLO and return a processed MP4.

    Workflow:
    - Save uploaded file to a temporary file.
    - Probe FPS from the original video (fallback to 25.0).
    - Call `predict_video(path)` which returns a list of processed frames (numpy arrays).
    - Encode these frames into a temporary MP4 using OpenCV `VideoWriter` and return it.

    Note: this can be slow depending on video length and model performance.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"})

    upload = request.FILES.get('file')
    if not upload:
        return JsonResponse({"error": "no file uploaded"}, status=400)

    # Save uploaded file to a temp file
    suffix = os.path.splitext(upload.name)[1] or '.mp4'
    in_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        in_tmp.write(upload.read())
        in_tmp.flush()
        in_tmp_path = in_tmp.name
    finally:
        in_tmp.close()

    out_tmp_path = None
    try:
        # Probe FPS from original video (best-effort)
        cap = cv2.VideoCapture(in_tmp_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        try:
            fps = float(fps) if fps and fps > 0 else 25.0
        except Exception:
            fps = 25.0
        cap.release()

        # Run YOLO processing which returns a list of frames (numpy arrays)
        frames = predict_video(in_tmp_path)
        if not frames:
            return JsonResponse({"error": "no frames produced by predict_video"}, status=500)

        h, w = frames[0].shape[:2]

        # Prepare output temp file
        out_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        out_tmp_path = out_tmp.name
        out_tmp.close()

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out_tmp_path, fourcc, fps, (w, h))
        if not writer.isOpened():
            raise RuntimeError('VideoWriter failed to open; check codecs')

        for fr in frames:
            # ensure uint8 and shape (h,w,3)
            if fr is None:
                continue
            if fr.dtype != 'uint8':
                fr = fr.astype('uint8')
            if fr.ndim == 2:
                fr = cv2.cvtColor(fr, cv2.COLOR_GRAY2BGR)
            if fr.shape[2] == 4:
                fr = fr[:, :, :3]
            writer.write(fr)

        writer.release()

        # Return the MP4
        with open(out_tmp_path, 'rb') as f:
            data = f.read()

        return HttpResponse(data, content_type='video/mp4')

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        # cleanup temp files if they exist
        try:
            os.remove(in_tmp_path)
        except Exception:
            pass
        if out_tmp_path:
            try:
                os.remove(out_tmp_path)
            except Exception:
                pass
