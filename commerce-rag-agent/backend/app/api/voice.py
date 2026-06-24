from typing import Literal
import os

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.responses import Response

from app.api.security import CurrentUser, require_current_user
from app.services.rate_limit_service import limiter
from app.services.voice_service import (
    VoiceInputError,
    VoiceProviderNotConfigured,
    VoiceServiceError,
    synthesize_speech,
    transcribe_audio,
    voice_capabilities,
)


router = APIRouter(prefix="/api/voice", tags=["voice"])


class TtsRequest(BaseModel):
    text: str = Field(min_length=1)
    voice: str | None = None
    format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] | None = None


@router.get("/capabilities")
def read_voice_capabilities() -> dict:
    return voice_capabilities()


@router.post("/asr")
def asr(
    file: UploadFile = File(...),
    language: str | None = None,
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    _enforce_voice_limit(current_user, "asr")
    try:
        return transcribe_audio(file, language=language).as_dict()
    except VoiceInputError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except VoiceProviderNotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except httpx.HTTPStatusError as error:
        detail = error.response.text[:500] if error.response is not None else str(error)
        raise HTTPException(status_code=502, detail=f"ASR provider error: {detail}") from error
    except VoiceServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/tts")
def tts(
    payload: TtsRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> Response:
    _enforce_voice_limit(current_user, "tts")
    try:
        result = synthesize_speech(payload.text, voice=payload.voice, audio_format=payload.format)
    except VoiceInputError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except VoiceProviderNotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except httpx.HTTPStatusError as error:
        detail = error.response.text[:500] if error.response is not None else str(error)
        raise HTTPException(status_code=502, detail=f"TTS provider error: {detail}") from error
    except VoiceServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return Response(
        content=result.audio,
        media_type=result.media_type,
        headers={
            "X-Voice-Provider": result.provider,
            "X-Voice-Model": result.model,
            "X-Voice-Name": result.voice,
            "Content-Disposition": f'inline; filename="agent-reply.{result.file_extension}"',
        },
    )


def _enforce_voice_limit(current_user: CurrentUser, action: str) -> None:
    decision = limiter.check(
        f"voice:{action}:{current_user.user_id}",
        limit=_voice_rate_limit_per_minute(action),
        window_seconds=60,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "voice rate limit exceeded",
                "retry_after_seconds": decision.retry_after_seconds,
            },
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )


def _voice_rate_limit_per_minute(action: str) -> int:
    env_name = "VOICE_TTS_RATE_LIMIT_PER_MINUTE" if action == "tts" else "VOICE_ASR_RATE_LIMIT_PER_MINUTE"
    default = 30 if action == "tts" else 12
    try:
        return max(int(os.getenv(env_name, str(default))), 1)
    except ValueError:
        return default
