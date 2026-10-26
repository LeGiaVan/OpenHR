"""Small live-provider smoke check using synthetic text and optional synthetic audio.

Run from backend after setting OPENHR_PROVIDER_MODE=gemini and GEMINI_API_KEY in .env:
    python scripts/gemini_smoke.py --audio-file path/to/synthetic.wav
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapters.gemini import GeminiProviderError, build_gemini_providers


async def run(args: argparse.Namespace) -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    language = args.language
    if args.stt_only:
        if not args.audio_file:
            raise RuntimeError(
                "--stt-only requires --audio-file; create a sample first with --tts-only --tts-output <path>."
            )
        audio_input = Path(args.audio_file)
        if not audio_input.is_file():
            raise RuntimeError(
                f"Audio sample not found: {audio_input.resolve()}. "
                "Create it first with --tts-only --tts-output <same path>."
            )
        providers = build_gemini_providers()
        started = time.perf_counter()
        transcript = await providers["stt"].transcribe(
            audio=audio_input.read_bytes(), language=language, mime_type=args.mime_type
        )
        print(f"STT ({time.perf_counter() - started:.2f}s): {transcript}")
        return

    providers = build_gemini_providers()
    if args.tts_only:
        text = (
            "Trong dự án môn học, em phụ trách kiểm tra dữ liệu đầu vào và xử lý trường hợp bỏ trống thông tin bắt buộc."
            if language == "vi"
            else "For my course project, I handled input validation and missing required information."
        )
        question = text
    else:
        system_prompt = (
            "Act as a professional practice interviewer for an intern candidate. "
            "Ask exactly one concise question, do not score or coach the candidate."
        )
        user_prompt = (
            "Synthetic test context only. The candidate built a small course project "
            "with a three-person team and personally implemented input validation. "
            "Ask a follow-up that clarifies their own contribution."
        )

        started = time.perf_counter()
        question = await providers["llm"].generate(
            system_prompt=system_prompt, user_prompt=user_prompt, language=language
        )
        print(f"LLM ({time.perf_counter() - started:.2f}s): {question}")
        if args.llm_only:
            return

    started = time.perf_counter()
    audio = await providers["tts"].synthesize(text=question, language=language)
    print(f"TTS ({time.perf_counter() - started:.2f}s): {len(audio)} audio bytes")
    if args.tts_output:
        output = Path(args.tts_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(audio)
        print(f"Saved TTS sample: {output}")

    if args.audio_file and not args.tts_only:
        audio_input = Path(args.audio_file)
        started = time.perf_counter()
        transcript = await providers["stt"].transcribe(
            audio=audio_input.read_bytes(), language=language, mime_type=args.mime_type
        )
        print(f"STT ({time.perf_counter() - started:.2f}s): {transcript}")
    elif not args.tts_only:
        print("STT skipped; provide a synthetic audio sample with --audio-file.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("vi", "en"), default="vi")
    parser.add_argument("--audio-file", help="Synthetic WAV/MP3/MP4 sample for the STT call")
    parser.add_argument("--mime-type", default="audio/wav")
    parser.add_argument("--tts-output", help="Optional path to save generated WAV audio for listening")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--stt-only", action="store_true", help="Run only STT on --audio-file")
    modes.add_argument("--tts-only", action="store_true", help="Run TTS on a fixed synthetic sentence")
    modes.add_argument("--llm-only", action="store_true", help="Run only LLM with synthetic context")
    try:
        asyncio.run(run(parser.parse_args()))
    except (GeminiProviderError, RuntimeError) as exc:
        print(f"Gemini smoke test could not complete: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
