"""
Recognition backends.

Available implementations:
- `dlib_recognizer.DlibRecognizer`          — face_recognition library (Phase 1)
- `insightface_recognizer.InsightFaceRecognizer`  — ArcFace embeddings (Phase 2)

Selected via settings.recognizer_backend.
"""
from app.recognition.base import Recognizer, RecognitionResult

__all__ = ["Recognizer", "RecognitionResult"]