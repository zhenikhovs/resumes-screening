"""Извлечение моно WAV 16 kHz из видео или копирование готового аудио."""
import shutil
import subprocess
from pathlib import Path

from config.interview_config import AUDIO_CHANNELS, AUDIO_SAMPLE_RATE


def _run_ffmpeg(args: list[str]) -> None:
    try:
        subprocess.run(
            ["ffmpeg", "-y", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "ffmpeg не найден. Установите ffmpeg и добавьте в PATH."
        ) from e
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        raise RuntimeError(f"ffmpeg завершился с ошибкой: {stderr}") from e


def extract_audio_from_video(video_path: Path, output_wav: Path) -> Path:
    """Видео → PCM WAV 16 kHz mono."""
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg(
        [
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(AUDIO_SAMPLE_RATE),
            "-ac",
            str(AUDIO_CHANNELS),
            str(output_wav),
        ]
    )
    return output_wav


def prepare_audio(input_path: Path, output_wav: Path) -> Path:
    """
    Если вход — видео, извлекает аудио. Если уже .wav/.mp3/.m4a/.flac — конвертирует в WAV 16k mono.
    """
    suffix = input_path.suffix.lower()
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    if suffix in {".wav", ".wave"} and input_path.resolve() != output_wav.resolve():
        _run_ffmpeg(
            [
                "-i",
                str(input_path),
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(AUDIO_SAMPLE_RATE),
                "-ac",
                str(AUDIO_CHANNELS),
                str(output_wav),
            ]
        )
        return output_wav

    if suffix in {".mp3", ".m4a", ".flac", ".ogg", ".aac"}:
        _run_ffmpeg(
            [
                "-i",
                str(input_path),
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(AUDIO_SAMPLE_RATE),
                "-ac",
                str(AUDIO_CHANNELS),
                str(output_wav),
            ]
        )
        return output_wav

    if suffix in {".mp4", ".webm", ".mov", ".mkv", ".avi"}:
        return extract_audio_from_video(input_path, output_wav)

    if input_path.resolve() == output_wav.resolve():
        return output_wav

    shutil.copy2(input_path, output_wav)
    return output_wav
