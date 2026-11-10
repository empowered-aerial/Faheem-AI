
import logging
import os
import tempfile
import threading

from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

MODEL_SIZE = os.getenv("FAHEEM_WHISPER_MODEL", "small")
DEVICE = os.getenv("FAHEEM_WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("FAHEEM_WHISPER_COMPUTE_TYPE", "int8")

MAX_AUDIO_BYTES = 25 * 1024 * 1024

MIME_SUFFIXES = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".mp4",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/aac": ".aac",
    "audio/3gpp": ".3gp"
}

ALLOWED_SUFFIXES = set(MIME_SUFFIXES.values())

_model = None
_model_lock = threading.Lock()
_transcription_lock = threading.Lock()


def get_whisper_model():
    global _model

    if _model is None:
        with _model_lock:
            if _model is None:
                from faster_whisper import WhisperModel

                _model = WhisperModel(
                    MODEL_SIZE,
                    device=DEVICE,
                    compute_type=COMPUTE_TYPE
                )

    return _model


def transcribe_file(path):
    model = get_whisper_model()

    with _transcription_lock:
        segments, info = model.transcribe(
            path,
            language="ar",
            task="transcribe",
            beam_size=5,
            temperature=0,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=(
                "بلاغات مدنية في أبوظبي: البطين، الخالدية، "
                "مدينة خليفة، مصفح، جزيرة الريم، الحفر، "
                "الطرق، النفايات، إنارة الشوارع."
            )
        )

        transcript = " ".join(
            segment.text.strip() for segment in segments
        ).strip()

    if not transcript:
        raise ValueError("لم يتم التعرف على كلام واضح في التسجيل.")

    return {
        "transcript": transcript,
        "language": info.language,
        "model": MODEL_SIZE
    }


def create_speech_router():
    router = APIRouter()

    @router.post("/api/transcribe")
    async def transcribe_audio(audio: UploadFile = File(...)):
        content_type = (
            audio.content_type or ""
        ).split(";")[0].strip().lower()

        suffix = MIME_SUFFIXES.get(content_type)

        if suffix is None:
            uploaded_suffix = Path(
                audio.filename or ""
            ).suffix.lower()

            if uploaded_suffix not in ALLOWED_SUFFIXES:
                raise HTTPException(
                    status_code=415,
                    detail="صيغة التسجيل غير مدعومة."
                )

            suffix = uploaded_suffix

        data = await audio.read(MAX_AUDIO_BYTES + 1)
        await audio.close()

        if not data:
            raise HTTPException(
                status_code=400,
                detail="ملف التسجيل فارغ."
            )

        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(
                status_code=413,
                detail="حجم التسجيل كبير جداً. حاول تسجيل مقطع أقصر."
            )

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix
            ) as temp_file:
                temp_file.write(data)
                temp_path = temp_file.name

            result = await run_in_threadpool(
                transcribe_file,
                temp_path
            )

            return result

        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail=str(error)
            ) from error

        except Exception as error:
            logger.exception("FAHEEM Whisper transcription failed")

            raise HTTPException(
                status_code=500,
                detail=(
                    "تعذر تحويل التسجيل إلى نص. "
                    "تحقق من Whisper واتصال الإنترنت عند تنزيل النموذج لأول مرة."
                )
            ) from error

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    return router
