import os
import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from fastapi import UploadFile


ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".mp4", ".mpeg", ".mpga"}
ALLOWED_AUDIO_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp4",
    "audio/webm",
    "audio/ogg",
    "video/mp4",
}
DEFAULT_ASR_BASE_URL = ""
DEFAULT_TTS_BASE_URL = ""
DEFAULT_DOUBAO_BASE_URL = ""
DEFAULT_DASHSCOPE_COMPATIBLE_BASE_URL = ""
DEFAULT_ALIBABA_TTS_URL = ""


class VoiceServiceError(RuntimeError):
    pass


class VoiceProviderNotConfigured(VoiceServiceError):
    pass


class VoiceInputError(VoiceServiceError):
    pass


@dataclass
class AsrResult:
    text: str
    provider: str
    model: str
    language: str = ""
    duration: float | None = None
    raw: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "provider": self.provider,
            "model": self.model,
            "language": self.language,
            "duration": self.duration,
            "raw": self.raw or {},
        }


@dataclass
class TtsResult:
    audio: bytes
    media_type: str
    provider: str
    model: str
    voice: str
    file_extension: str


def voice_capabilities() -> dict[str, Any]:
    asr_provider = _provider("ASR_PROVIDER")
    tts_provider = _provider("TTS_PROVIDER")
    return {
        "asr": {
            "provider": asr_provider,
            "configured": _is_supported_asr_provider(asr_provider)
            and bool(_asr_api_key(asr_provider))
            and bool(_asr_model(asr_provider)),
            "model": _asr_model(asr_provider),
            "mode": _asr_mode(asr_provider),
            "max_audio_mb": _max_audio_mb(),
        },
        "tts": {
            "provider": tts_provider,
            "configured": _is_supported_tts_provider(tts_provider)
            and bool(_tts_api_key())
            and bool(_tts_model(tts_provider))
            and bool(_tts_voice(tts_provider)),
            "model": _tts_model(tts_provider),
            "voice": _tts_voice(tts_provider),
            "format": os.getenv("TTS_FORMAT", "mp3"),
            "mode": _tts_mode(tts_provider),
            "max_text_chars": _max_tts_chars(),
        },
        "browser_fallback": {
            "asr": True,
            "tts": True,
        },
    }


def transcribe_audio(file: UploadFile, *, language: str | None = None) -> AsrResult:
    provider = _provider("ASR_PROVIDER")
    if not _is_supported_asr_provider(provider):
        raise VoiceProviderNotConfigured(
            "ASR_PROVIDER must be doubao_multimodal/ark_multimodal/openai_compatible/openai"
        )

    content, filename = _read_upload_audio(file)
    api_key = _asr_api_key(provider)
    if not api_key:
        raise VoiceProviderNotConfigured("ASR_API_KEY, OPENAI_API_KEY, ARK_API_KEY or DOUBAO_API_KEY is required")

    if _is_chat_audio_asr_provider(provider):
        return _transcribe_with_chat_audio(
            content,
            filename,
            provider=provider,
            api_key=api_key,
            language=language,
        )

    return _transcribe_with_audio_transcriptions(
        content,
        filename,
        provider=provider,
        api_key=api_key,
        language=language,
    )


def _transcribe_with_audio_transcriptions(
    content: bytes,
    filename: str,
    *,
    provider: str,
    api_key: str,
    language: str | None,
) -> AsrResult:
    base_url = _base_url("ASR_BASE_URL", DEFAULT_ASR_BASE_URL)
    model = _asr_model(provider)
    if not model:
        raise VoiceProviderNotConfigured("ASR_MODEL is required")
    resolved_language = language or os.getenv("ASR_LANGUAGE", "zh")
    timeout = float(os.getenv("ASR_TIMEOUT_SECONDS", "60"))

    data = {"model": model, "language": resolved_language}
    response_format = os.getenv("ASR_RESPONSE_FORMAT", "json").strip()
    if response_format:
        data["response_format"] = response_format

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            f"{base_url}/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            data=data,
            files={"file": (filename, content, _audio_media_type(filename))},
        )
    response.raise_for_status()
    payload = response.json()
    text = str(payload.get("text") or "").strip()
    if not text:
        raise VoiceServiceError("ASR provider returned empty text")
    return AsrResult(
        text=text,
        provider=provider,
        model=model,
        language=str(payload.get("language") or resolved_language or ""),
        duration=_float_or_none(payload.get("duration")),
        raw=payload,
    )


def _transcribe_with_chat_audio(
    content: bytes,
    filename: str,
    *,
    provider: str,
    api_key: str,
    language: str | None,
) -> AsrResult:
    base_url = _base_url("ASR_BASE_URL", _default_chat_audio_base_url(provider))
    model = _asr_model(provider)
    if not model:
        raise VoiceProviderNotConfigured("ASR_MODEL is required")
    resolved_language = language or os.getenv("ASR_LANGUAGE", "zh")
    timeout = float(os.getenv("ASR_TIMEOUT_SECONDS", "60"))
    payload = {
        "model": model,
        "temperature": float(os.getenv("ASR_TEMPERATURE", "0")),
        "modalities": ["text"],
        "stream": True,
        "stream_options": {"include_usage": True},
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是电商导购系统里的语音识别模块。"
                    "请只输出用户语音转写后的文字，不要解释，不要添加标点以外的额外内容。"
                    "如果音频没有清晰人声，输出空字符串。"
                ),
            },
            {
                "role": "user",
                "content": [
                    _chat_audio_content_item(content, filename),
                    {
                        "type": "text",
                        "text": (
                            f"请把这段音频转写为{resolved_language or '中文'}文本。"
                            "保留购物意图、商品名、预算、数量和确认/取消等关键口语。"
                        ),
                    },
                ],
            },
        ],
    }
    chunks: list[str] = []
    usage: dict[str, Any] = {}
    with httpx.Client(timeout=timeout) as client:
        with client.stream(
            "POST",
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                parsed = _parse_sse_json(line)
                if not parsed:
                    continue
                if parsed.get("usage"):
                    usage = parsed.get("usage") or {}
                for choice in parsed.get("choices") or []:
                    delta = choice.get("delta") or {}
                    content_delta = delta.get("content")
                    if content_delta:
                        chunks.append(str(content_delta))
                    message = choice.get("message") or {}
                    if message.get("content"):
                        chunks.append(str(message["content"]))
    content_text = "".join(chunks).strip()
    text = _clean_asr_text(content_text)
    if not text:
        raise VoiceServiceError("ASR provider returned empty text")
    return AsrResult(
        text=text,
        provider=provider,
        model=model,
        language=resolved_language or "",
        raw={"content": content_text, "usage": usage},
    )


def synthesize_speech(text: str, *, voice: str | None = None, audio_format: str | None = None) -> TtsResult:
    provider = _provider("TTS_PROVIDER")
    if not _is_supported_tts_provider(provider):
        raise VoiceProviderNotConfigured("TTS_PROVIDER must be alibaba_cosyvoice/openai_compatible/openai")

    clean_text = _normalize_tts_text(text)
    api_key = _tts_api_key()
    if not api_key:
        raise VoiceProviderNotConfigured("TTS_API_KEY or DASHSCOPE_API_KEY is required")

    if _is_alibaba_cosyvoice_provider(provider):
        return _synthesize_with_alibaba_cosyvoice(
            clean_text,
            provider=provider,
            api_key=api_key,
            voice=voice,
            audio_format=audio_format,
        )

    return _synthesize_with_openai_audio(
        clean_text,
        provider=provider,
        api_key=api_key,
        voice=voice,
        audio_format=audio_format,
    )


def _synthesize_with_openai_audio(
    clean_text: str,
    *,
    provider: str,
    api_key: str,
    voice: str | None,
    audio_format: str | None,
) -> TtsResult:
    base_url = _base_url("TTS_BASE_URL", DEFAULT_TTS_BASE_URL)
    model = _tts_model(provider)
    if not model:
        raise VoiceProviderNotConfigured("TTS_MODEL is required")
    resolved_voice = (voice or _tts_voice(provider)).strip()
    resolved_format = (audio_format or os.getenv("TTS_FORMAT", "mp3")).strip().lower() or "mp3"
    timeout = float(os.getenv("TTS_TIMEOUT_SECONDS", "60"))

    payload = {
        "model": model,
        "voice": resolved_voice,
        "input": clean_text,
        "response_format": resolved_format,
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            f"{base_url}/audio/speech",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    response.raise_for_status()
    audio = response.content
    if not audio:
        raise VoiceServiceError("TTS provider returned empty audio")
    media_type = response.headers.get("content-type") or _tts_media_type(resolved_format)
    return TtsResult(
        audio=audio,
        media_type=media_type,
        provider=provider,
        model=model,
        voice=resolved_voice,
        file_extension=_tts_extension(resolved_format),
    )


def _synthesize_with_alibaba_cosyvoice(
    clean_text: str,
    *,
    provider: str,
    api_key: str,
    voice: str | None,
    audio_format: str | None,
) -> TtsResult:
    model = _tts_model(provider)
    if not model:
        raise VoiceProviderNotConfigured("TTS_MODEL is required")
    resolved_voice = (voice or _tts_voice(provider)).strip()
    if not resolved_voice:
        raise VoiceProviderNotConfigured(
            "TTS_VOICE is required for cosyvoice-v3.5-flash. Use a voice_id created by Alibaba voice design/cloning."
        )

    resolved_format = (audio_format or os.getenv("TTS_FORMAT", "mp3")).strip().lower() or "mp3"
    sample_rate = int(os.getenv("TTS_SAMPLE_RATE", "24000"))
    timeout = float(os.getenv("TTS_TIMEOUT_SECONDS", "60"))
    payload = {
        "model": model,
        "input": {
            "text": clean_text,
            "voice": resolved_voice,
            "format": resolved_format,
            "sample_rate": sample_rate,
        },
    }
    instruction = os.getenv("TTS_INSTRUCTION", "").strip()
    if instruction:
        payload["input"]["instruction"] = instruction

    endpoint = _base_url("TTS_BASE_URL", DEFAULT_ALIBABA_TTS_URL)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        audio = ((data.get("output") or {}).get("audio") or {})
        audio_data = str(audio.get("data") or "")
        audio_url = str(audio.get("url") or "")
        if audio_data:
            try:
                decoded_audio = base64.b64decode(audio_data)
            except Exception as error:
                raise VoiceServiceError("Alibaba CosyVoice returned invalid base64 audio data") from error
        elif audio_url:
            audio_response = client.get(audio_url)
            audio_response.raise_for_status()
            decoded_audio = audio_response.content
        else:
            raise VoiceServiceError("Alibaba CosyVoice response did not include audio data or url")

    if not decoded_audio:
        raise VoiceServiceError("Alibaba CosyVoice returned empty audio")
    return TtsResult(
        audio=decoded_audio,
        media_type=_tts_media_type(resolved_format),
        provider=provider,
        model=model,
        voice=resolved_voice,
        file_extension=_tts_extension(resolved_format),
    )


def _read_upload_audio(file: UploadFile) -> tuple[bytes, str]:
    filename = file.filename or "audio.webm"
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise VoiceInputError("Only wav, mp3, m4a, webm, ogg, mp4 and mpeg audio are supported")
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type and content_type not in ALLOWED_AUDIO_MIME_TYPES:
        raise VoiceInputError("Uploaded file MIME type is not an allowed audio type")
    max_bytes = _max_audio_mb() * 1024 * 1024
    content = file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise VoiceInputError(f"Audio size must be <= {_max_audio_mb()}MB")
    if not content:
        raise VoiceInputError("Audio file is empty")
    return content, filename


def _normalize_tts_text(text: str) -> str:
    clean_text = " ".join(str(text or "").split())
    if not clean_text:
        raise VoiceInputError("TTS text is required")
    max_chars = _max_tts_chars()
    if len(clean_text) > max_chars:
        clean_text = clean_text[:max_chars]
    return clean_text


def _provider(env_name: str) -> str:
    return os.getenv(env_name, "disabled").strip().lower()


def _is_supported_asr_provider(provider: str) -> bool:
    return _is_openai_audio_provider(provider) or _is_chat_audio_asr_provider(provider)


def _is_openai_audio_provider(provider: str) -> bool:
    return provider in {"openai", "openai_compatible", "compatible"}


def _is_supported_tts_provider(provider: str) -> bool:
    return _is_openai_audio_provider(provider) or _is_alibaba_cosyvoice_provider(provider)


def _is_alibaba_cosyvoice_provider(provider: str) -> bool:
    return provider in {"alibaba", "aliyun", "dashscope", "alibaba_cosyvoice", "cosyvoice"}


def _is_chat_audio_asr_provider(provider: str) -> bool:
    return provider in {
        "alibaba_omni",
        "aliyun_omni",
        "dashscope_omni",
        "qwen_omni",
        "qwen3_5_omni",
        "doubao",
        "ark",
        "volcengine",
        "doubao_multimodal",
        "ark_multimodal",
        "multimodal_chat",
        "chat_completions",
    }


def _api_key(primary_env: str) -> str:
    return _env_first(
        primary_env,
        "DASHSCOPE_API_KEY",
        "ALIBABA_API_KEY",
        "OPENAI_API_KEY",
        "ARK_API_KEY",
        "DOUBAO_API_KEY",
    )


def _asr_api_key(provider: str) -> str:
    if _is_alibaba_omni_provider(provider):
        return _env_first("ASR_API_KEY", "DASHSCOPE_API_KEY", "ALIBABA_API_KEY")
    if _is_chat_audio_asr_provider(provider):
        return _env_first("ASR_API_KEY", "ARK_API_KEY", "DOUBAO_API_KEY", "OPENAI_API_KEY")
    return _env_first("ASR_API_KEY", "OPENAI_API_KEY")


def _tts_api_key() -> str:
    return _env_first("TTS_API_KEY", "DASHSCOPE_API_KEY", "ALIBABA_API_KEY", "OPENAI_API_KEY")


def _base_url(primary_env: str, default: str) -> str:
    value = (
        _env_first(primary_env, "DASHSCOPE_BASE_URL", "OPENAI_BASE_URL", "DOUBAO_BASE_URL") or default
    ).rstrip("/")
    if not value:
        raise VoiceProviderNotConfigured(f"{primary_env} is required")
    return value


def _asr_model(provider: str) -> str:
    if _is_alibaba_omni_provider(provider):
        return _env_first("ASR_MODEL")
    if _is_chat_audio_asr_provider(provider):
        return _env_first("ASR_MODEL", "DOUBAO_MODEL") or ""
    return _env_first("ASR_MODEL")


def _asr_mode(provider: str) -> str:
    if _is_alibaba_omni_provider(provider):
        return "dashscope_omni_stream_audio"
    if _is_chat_audio_asr_provider(provider):
        return "chat_completions_audio"
    if _is_openai_audio_provider(provider):
        return "audio_transcriptions"
    return "disabled"


def _tts_model(provider: str) -> str:
    return _env_first("TTS_MODEL")


def _tts_voice(provider: str) -> str:
    if _is_alibaba_cosyvoice_provider(provider):
        return _env_first("TTS_VOICE", "DASHSCOPE_VOICE_ID", "COSYVOICE_VOICE_ID")
    return _env_first("TTS_VOICE")


def _tts_mode(provider: str) -> str:
    if _is_alibaba_cosyvoice_provider(provider):
        return "dashscope_speech_synthesizer"
    if _is_openai_audio_provider(provider):
        return "audio_speech"
    return "disabled"


def _env_first(*names: str) -> str:
    for name in names:
        value = _resolve_env_reference(os.getenv(name, ""))
        if value:
            return value
    return ""


def _resolve_env_reference(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("${") and text.endswith("}"):
        return os.getenv(text[2:-1], "").strip()
    return text


def _is_alibaba_omni_provider(provider: str) -> bool:
    return provider in {"alibaba_omni", "aliyun_omni", "dashscope_omni", "qwen_omni", "qwen3_5_omni"}


def _default_chat_audio_base_url(provider: str) -> str:
    if _is_alibaba_omni_provider(provider):
        return DEFAULT_DASHSCOPE_COMPATIBLE_BASE_URL
    return DEFAULT_DOUBAO_BASE_URL


def _parse_sse_json(line: str) -> dict[str, Any] | None:
    text = str(line or "").strip()
    if not text:
        return None
    if text.startswith("data:"):
        text = text.removeprefix("data:").strip()
    if text == "[DONE]":
        return None
    try:
        import json

        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _max_audio_mb() -> int:
    return max(1, int(os.getenv("VOICE_MAX_AUDIO_MB", "20")))


def _max_tts_chars() -> int:
    return max(100, int(os.getenv("TTS_MAX_TEXT_CHARS", "1200")))


def _audio_media_type(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    return {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".mpeg": "audio/mpeg",
        ".mpga": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
    }.get(extension, "application/octet-stream")


def _chat_audio_content_item(content: bytes, filename: str) -> dict[str, Any]:
    encoded = base64.b64encode(content).decode("ascii")
    data_url = f"data:;base64,{encoded}"
    audio_format = _audio_format(filename)
    content_type = os.getenv("ASR_CHAT_AUDIO_CONTENT_TYPE", "input_audio").strip()
    if content_type == "audio_url":
        return {
            "type": "audio_url",
            "audio_url": {"url": data_url},
        }
    return {
        "type": "input_audio",
        "input_audio": {
            "data": data_url,
            "format": audio_format,
        },
    }


def _audio_format(filename: str) -> str:
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension in {"mpeg", "mpga"}:
        return "mp3"
    if extension == "m4a":
        return "mp4"
    return extension or "wav"


def _clean_asr_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            import json

            payload = json.loads(cleaned)
            if isinstance(payload, dict):
                cleaned = str(payload.get("text") or payload.get("transcript") or "").strip()
        except Exception:
            pass
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def _tts_media_type(audio_format: str) -> str:
    return {
        "mp3": "audio/mpeg",
        "opus": "audio/ogg",
        "aac": "audio/aac",
        "flac": "audio/flac",
        "wav": "audio/wav",
        "pcm": "audio/L16",
    }.get(audio_format, "application/octet-stream")


def _tts_extension(audio_format: str) -> str:
    return "ogg" if audio_format == "opus" else audio_format


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
