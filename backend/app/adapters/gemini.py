from __future__ import annotations

import asyncio
import base64
import logging
import os
import tempfile
from pathlib import Path
from typing import Any


logger = logging.getLogger("openhr.providers.gemini")


class GeminiProviderError(RuntimeError):
    """A provider failure without request content or credentials in the message."""


class GeminiLLMProvider:
    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    async def generate(self, *, system_prompt: str, user_prompt: str, language: str) -> str:
        language_name = {"vi": "Vietnamese", "en": "English"}.get(language, language)
        prompt = (
            f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n"
            f"The interview session language is {language_name}. Write the response only in {language_name}.\n\n"
            f"USER CONTEXT:\n{user_prompt}"
        )
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt,
            )
        except Exception as exc:
            logger.warning("Gemini LLM request failed (%s)", type(exc).__name__)
            raise GeminiProviderError("LLM provider request failed") from exc
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise GeminiProviderError("LLM provider returned an empty response")
        return text.strip()


class GeminiSpeechToTextProvider:
    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    async def transcribe(
        self, *, audio: bytes, language: str, mime_type: str = "audio/wav"
    ) -> str:
        if not audio:
            raise ValueError("Audio payload must not be empty")
        language_code = {"vi": "vi-VN", "en": "en-US"}.get(language)
        suffix = {"audio/wav": ".wav", "audio/mpeg": ".mp3", "audio/mp4": ".mp4"}.get(
            mime_type, ".audio"
        )
        uploaded = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as audio_file:
                audio_file.write(audio)
                temp_path = Path(audio_file.name)
            uploaded = await asyncio.to_thread(self.client.files.upload, file=str(temp_path))
            config = {"transcription_config": {"language_codes": [language_code]}} if language_code else None
            kwargs = {
                "model": self.model,
                "input": [{"type": "audio", "uri": uploaded.uri, "mime_type": uploaded.mime_type}],
            }
            if config:
                kwargs["generation_config"] = config
            interaction = await asyncio.to_thread(self.client.interactions.create, **kwargs)
            text = getattr(interaction, "output_text", None)
            if not isinstance(text, str) or not text.strip():
                raise GeminiProviderError("STT provider returned an empty transcript")
            return text.strip()
        except GeminiProviderError:
            raise
        except Exception as exc:
            logger.warning("Gemini STT request failed (%s)", type(exc).__name__)
            raise GeminiProviderError("STT provider request failed") from exc
        finally:
            if "temp_path" in locals():
                temp_path.unlink(missing_ok=True)
            if uploaded is not None:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded.name)
                except Exception as exc:
                    logger.warning("Gemini temporary file cleanup failed (%s)", type(exc).__name__)


class GeminiTextToSpeechProvider:
    def __init__(self, client: Any, model: str, voice: str = "Kore"):
        self.client = client
        self.model = model
        self.voice = voice

    async def synthesize(self, *, text: str, language: str) -> bytes:
        language_name = {"vi": "Vietnamese", "en": "English"}.get(language, language)
        try:
            interaction = await asyncio.to_thread(
                self.client.interactions.create,
                model=self.model,
                input=[{
                    "type": "user_input",
                    "content": [{
                        "type": "text",
                        "text": text,
                        "annotations": [{
                            "type": "speech_metadata",
                            "style": f"Speak naturally in {language_name} with a professional interviewer tone.",
                        }],
                    }],
                }],
                response_format={"type": "audio"},
                generation_config={"speech_config": [{"voice": self.voice}]},
            )
            output_audio = getattr(interaction, "output_audio", None)
            encoded = getattr(output_audio, "data", None)
            if not isinstance(encoded, str) or not encoded:
                raise GeminiProviderError("TTS provider returned no audio payload")
            return base64.b64decode(encoded, validate=True)
        except GeminiProviderError:
            raise
        except Exception as exc:
            logger.warning("Gemini TTS request failed (%s)", type(exc).__name__)
            raise GeminiProviderError("TTS provider request failed") from exc


def build_gemini_providers() -> dict[str, object]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENHR_PROVIDER_MODE=gemini requires GEMINI_API_KEY in local environment")
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Install backend dependencies to enable Gemini provider mode") from exc
    client = genai.Client(api_key=api_key)
    return {
        "llm": GeminiLLMProvider(
            client, os.getenv("OPENHR_GEMINI_LLM_MODEL", "gemini-3.5-flash-lite")
        ),
        "stt": GeminiSpeechToTextProvider(
            client, os.getenv("OPENHR_GEMINI_STT_MODEL", "gemini-3.5-transcribe")
        ),
        "tts": GeminiTextToSpeechProvider(
            client,
            os.getenv("OPENHR_GEMINI_TTS_MODEL", "gemini-3.8-flash-lite-tts"),
            os.getenv("OPENHR_GEMINI_TTS_VOICE", "Kore"),
        ),
    }
