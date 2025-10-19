#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

# Lazy import to allow --help without requiring package installed yet
try:
    import replicate  # type: ignore
except Exception:  # pragma: no cover
    replicate = None  # type: ignore


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        print(
            "ERROR: ffmpeg is not installed or not on PATH. Please install ffmpeg.",
            file=sys.stderr,
        )
        sys.exit(2)


def load_json_or_empty(text: Optional[str]) -> Dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON for --model-input: {exc}", file=sys.stderr)
        sys.exit(2)


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def stream_download(url: str, dest_path: Path) -> None:
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        bytes_done = 0
        chunk_size = 1024 * 1024
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    bytes_done += len(chunk)
                    if total:
                        pct = bytes_done * 100 // total
                        print(f"Downloading: {pct}% ({bytes_done}/{total} bytes)", end="\r")
        print()


def normalize_replicate_output(result: Any) -> List[str]:
    """
    Normalize Replicate output to a list of downloadable URLs.
    Accepts:
      - single URL string
      - list of URL strings
      - dict containing a likely URL under common keys
    """
    if isinstance(result, str):
        return [result]
    if isinstance(result, list):
        # filter only URL-ish strings
        return [x for x in result if isinstance(x, str) and is_url(x)]
    if isinstance(result, dict):
        for key in ("video", "output", "result", "url"):
            val = result.get(key)
            if isinstance(val, str) and is_url(val):
                return [val]
            if isinstance(val, list):
                return [x for x in val if isinstance(x, str) and is_url(x)]
    raise RuntimeError(
        "Could not interpret Replicate model output; please specify a compatible model."
    )


def pick_best_video_url(urls: List[str]) -> str:
    # Prefer MP4 if present, else last URL
    mp4s = [u for u in urls if ".mp4" in u.split("?")[0].lower()]
    if mp4s:
        return mp4s[-1]
    return urls[-1]


def derive_output_path(input_path: str, suffix: str, output: Optional[str]) -> Path:
    if output:
        return Path(output).resolve()
    if is_url(input_path):
        base = Path("downloaded_input")
    else:
        base = Path(input_path).resolve()
    return base.with_suffix("") .with_name(base.stem + suffix + ".mp4")


def build_audio_tempo_chain(factor: float) -> str:
    """
    Build a valid ffmpeg atempo chain to match a playback factor.
    ffmpeg atempo accepts values in [0.5, 2.0]. We decompose the factor
    into a comma-separated chain of atempo filters whose product equals factor.
    """
    if factor <= 0:
        raise ValueError("factor must be > 0")

    tempos: List[float] = []
    tempo = factor
    # If we want to slow down (factor < 1), chain 0.5 until within range
    if tempo < 0.5:
        while tempo < 0.5:
            tempos.append(0.5)
            tempo *= 2.0
        if 0.5 <= tempo <= 2.0:
            tempos.append(tempo)
    elif tempo > 2.0:
        # Speed up drastically: chain 2.0 until within range
        while tempo > 2.0:
            tempos.append(2.0)
            tempo /= 2.0
        if 0.5 <= tempo <= 2.0:
            tempos.append(tempo)
    else:
        tempos.append(tempo)

    return ",".join(f"atempo={t:.6g}" for t in tempos)


def run_ffmpeg_slowmo(
    input_video: Path,
    output_video: Path,
    factor: float,
    target_fps: int,
    audio_mode: str,
    crf: int,
    preset: str,
) -> None:
    ensure_ffmpeg_available()

    # Video filter: slow down by factor and set desired fps
    vf = f"setpts=PTS/{factor},fps={target_fps}"

    cmd: List[str] = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-movflags",
        "+faststart",
    ]

    if audio_mode == "mute":
        cmd += ["-an"]
    elif audio_mode == "stretch":
        af = build_audio_tempo_chain(factor)
        cmd += [
            "-filter:a",
            af,
            "-c:a",
            "aac",
            "-b:a",
            "192k",
        ]
    else:
        raise ValueError("audio_mode must be 'mute' or 'stretch'")

    cmd.append(str(output_video))

    print("Running ffmpeg:")
    print(" ", " ".join(cmd))
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed")


def run_replicate_interpolation(
    input_media: str,
    model: str,
    model_version: Optional[str],
    video_key: str,
    model_input_json: Optional[str],
) -> Path:
    if replicate is None:
        print(
            "The 'replicate' package is not installed. Run: pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(2)

    api_token = os.environ.get("REPLICATE_API_TOKEN")
    if not api_token:
        print(
            "Set REPLICATE_API_TOKEN in your environment before running.",
            file=sys.stderr,
        )
        sys.exit(2)

    inputs: Dict[str, Any] = load_json_or_empty(model_input_json)

    file_obj = None
    if not is_url(input_media) and Path(input_media).exists():
        file_obj = open(input_media, "rb")
        inputs[video_key] = file_obj
    else:
        inputs[video_key] = input_media

    # Build the identifier for replicate.run
    run_id = None
    if model_version:
        run_id = f"{model}:{model_version}"
    else:
        # If user already provided colon version in model, accept it
        if ":" in model:
            run_id = model
        else:
            # Resolve latest version dynamically
            m = replicate.models.get(model)
            v = next(iter(m.versions.list()))  # latest first
            run_id = f"{model}:{v.id}"

    print(f"Running Replicate model: {run_id}")
    try:
        result = replicate.run(run_id, input=inputs)
    finally:
        if file_obj is not None:
            file_obj.close()

    urls = normalize_replicate_output(result)
    url = pick_best_video_url(urls)

    tmp_dir = Path(tempfile.mkdtemp(prefix="slomo_intermediate_"))
    # Try to infer extension from URL path
    ext = Path(url.split("?")[0]).suffix or ".mp4"
    out_path = tmp_dir / f"interpolated{ext}"
    print(f"Downloading model output -> {out_path}")
    stream_download(url, out_path)
    return out_path


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Convert any video into smooth slow motion using Replicate frame "
            "interpolation (default RIFE) and ffmpeg speed adjustment."
        )
    )
    p.add_argument("--input", "-i", required=True, help="Input video file path or URL")
    p.add_argument("--output", "-o", help="Output video file path (default: <input>.slomo.mp4)")
    p.add_argument(
        "--factor",
        "-f",
        type=float,
        default=0.25,
        help="Playback speed factor (e.g., 0.25 for 4x slower)",
    )
    p.add_argument(
        "--target-fps",
        type=int,
        default=60,
        help="Target output FPS after interpolation (used in ffmpeg stage)",
    )
    p.add_argument(
        "--audio-mode",
        choices=["stretch", "mute"],
        default="stretch",
        help="'stretch' to time-stretch audio to match, or 'mute'",
    )
    p.add_argument(
        "--model",
        default="cjwbw/rife",
        help=(
            "Replicate model slug (optionally with :version). "
            "Example: 'cjwbw/rife:abcd1234...'."
        ),
    )
    p.add_argument(
        "--model-version",
        help="Explicit model version hash (overrides slug version if set)",
    )
    p.add_argument(
        "--video-key",
        default="video",
        help="Input key name for the model's video field (default: 'video')",
    )
    p.add_argument(
        "--model-input",
        help=(
            "JSON string of extra model inputs, merged with video key. "
            "Example: '{\"multiplier\": 4}'"
        ),
    )
    p.add_argument(
        "--crf",
        type=int,
        default=18,
        help="x264 CRF quality (lower is better, 18 is visually lossless)",
    )
    p.add_argument(
        "--preset",
        default="medium",
        help="x264 preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)",
    )
    p.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="Keep intermediate interpolated file (for debugging)",
    )
    p.add_argument(
        "--skip-interpolation",
        action="store_true",
        help="Skip Replicate interpolation and only apply ffmpeg slow motion",
    )

    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.factor <= 0:
        print("--factor must be > 0", file=sys.stderr)
        return 2

    output_path = derive_output_path(args.input, ".slomo", args.output)

    # Stage 1: Run frame interpolation unless skipped
    if args.skip_interpolation:
        print("Skipping interpolation stage as requested.")
        interpolated_path = Path(args.input if not is_url(args.input) else "downloaded_input.mp4")
        if is_url(args.input):
            # download input locally to feed ffmpeg
            tmp_dir = Path(tempfile.mkdtemp(prefix="slomo_input_"))
            interpolated_path = tmp_dir / "input.mp4"
            print(f"Downloading input -> {interpolated_path}")
            stream_download(args.input, interpolated_path)
    else:
        interpolated_path = run_replicate_interpolation(
            input_media=args.input,
            model=args.model,
            model_version=args.model_version,
            video_key=args.video_key,
            model_input_json=args.model_input,
        )

    # Stage 2: ffmpeg slow-mo
    try:
        run_ffmpeg_slowmo(
            input_video=interpolated_path,
            output_video=output_path,
            factor=args.factor,
            target_fps=args.target_fps,
            audio_mode=args.audio_mode,
            crf=args.crf,
            preset=args.preset,
        )
    finally:
        if not args.keep_intermediate and interpolated_path.exists():
            # Attempt to delete the intermediate folder if it was ours
            try:
                tmp_parent = interpolated_path.parent
                if tmp_parent.name.startswith("slomo_intermediate_"):
                    for child in tmp_parent.iterdir():
                        try:
                            child.unlink()
                        except Exception:
                            pass
                    tmp_parent.rmdir()
            except Exception:
                pass

    print(f"Done. Output saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
