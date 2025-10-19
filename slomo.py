#!/usr/bin/env python3
"""
Smooth Slow-Motion Video Converter (Free, No Limits)

- Uses FFmpeg's minterpolate for motion-compensated frame interpolation
- Preserves audio pitch using chained atempo filters
- Ships its own static FFmpeg via imageio-ffmpeg (installed into ./vendor)

Example:
  python3 slomo.py input.mp4 --factor 4 --out output_4x.mp4 --out-fps 30
"""
from __future__ import annotations

import argparse
import math
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


def find_ffmpeg_executable() -> str:
    """
    Returns a usable FFmpeg executable path.
    Preference order:
    1) imageio-ffmpeg vendored binary in ./vendor/
    2) imageio-ffmpeg from user/site packages
    3) 'ffmpeg' on PATH
    """
    # Try vendored imageio-ffmpeg first
    try:
        script_dir = Path(__file__).resolve().parent
        vendor_dir = script_dir / "vendor"
        if vendor_dir.exists():
            sys.path.insert(0, str(vendor_dir))
            import imageio_ffmpeg as iio

            return iio.get_ffmpeg_exe()
    except Exception:
        pass

    # Try site imageio-ffmpeg
    try:
        import imageio_ffmpeg as iio  # type: ignore

        return iio.get_ffmpeg_exe()
    except Exception:
        pass

    # Fallback to system ffmpeg
    return "ffmpeg"


@dataclass
class SlomoOptions:
    input_path: Path
    output_path: Path
    factor: float
    out_fps: Optional[float]
    video_preset: str
    video_crf: int
    video_codec: str
    audio_mode: str  # 'keep' | 'mute'
    audio_bitrate: str
    threads: Optional[int]


FPS_PARSE_REGEX = re.compile(r",\s*(?P<fps>\d+(?:\.\d+)?)\s*fps[,\s]")


def probe_input_fps(ffmpeg: str, input_path: Path) -> Optional[float]:
    """Attempt to parse input FPS using ffmpeg's banner output. Returns None if not found."""
    try:
        # We intentionally invoke ffmpeg -i to print stream info to stderr without running.
        # This is a heuristic: we parse the 'fps' token from the stream line.
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", str(input_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
        m = FPS_PARSE_REGEX.search(proc.stdout)
        if m:
            return float(m.group("fps"))
    except Exception:
        return None
    return None


def build_atempo_chain(target_tempo: float) -> List[float]:
    """
    Build a list of atempo factors (each between 0.5 and 2.0) whose product
    approximates target_tempo (e.g., 0.25 -> [0.5, 0.5]).
    """
    if target_tempo <= 0:
        raise ValueError("target_tempo must be > 0")

    chain: List[float] = []
    remaining = target_tempo

    # For values < 0.5, multiply by 2.0 repeatedly by appending 0.5 to the chain
    while remaining < 0.5:
        chain.append(0.5)
        remaining /= 0.5  # equivalently remaining *= 2

    # For values > 2.0, divide by 2.0 repeatedly by appending 2.0 to the chain
    while remaining > 2.0:
        chain.append(2.0)
        remaining /= 2.0

    # Append the remainder if it's sufficiently far from 1.0
    if not math.isclose(remaining, 1.0, rel_tol=1e-6, abs_tol=1e-6):
        # Clamp for safety to valid range (0.5..2.0)
        remaining = max(0.5, min(2.0, remaining))
        chain.append(remaining)

    # If chain would be empty (target ~1), still return [1.0] to keep logic simple upstream
    if not chain:
        chain = [1.0]

    return chain


def build_ffmpeg_filters(
    factor: float, out_fps: float, interpolation_quality: str = "high"
) -> str:
    """
    Build FFmpeg video filter chain string using minterpolate for smooth slomo.

    interpolation_quality selects motion estimation parameters:
    - 'fast' -> quicker, less accurate
    - 'balanced' -> default
    - 'high' -> more accurate (slower)
    """
    # Map quality to minterpolate parameters
    # See `ffmpeg -h filter=minterpolate` for valid options.
    # - mi_mode: dup | blend | mci
    # - mc_mode: obmc | aobmc
    # - me_mode: bidir | bilat
    # - me:      esa|tss|tdls|ntss|fss|ds|hexbs|epzs|umh
    if interpolation_quality == "fast":
        me_mode = "bilat"
        me = "hexbs"
        mc_mode = "obmc"
        mi_mode = "mci"
        vsbmc = 0
    elif interpolation_quality == "high":
        me_mode = "bidir"
        me = "umh"
        mc_mode = "aobmc"
        mi_mode = "mci"
        vsbmc = 1
    else:  # balanced
        me_mode = "bilat"
        me = "hexbs"
        mc_mode = "aobmc"
        mi_mode = "mci"
        vsbmc = 1

    interp_fps = out_fps * factor

    vf_parts = [
        (
            "minterpolate="
            f"fps={interp_fps:.6f}:"
            f"mi_mode={mi_mode}:"
            f"mc_mode={mc_mode}:"
            f"me_mode={me_mode}:"
            f"me={me}:"
            f"vsbmc={vsbmc}"
        ),
        f"setpts={factor:.6f}*PTS",
        f"fps={out_fps:.6f}",  # ensure constant, final fps
    ]
    return ",".join(vf_parts)


def run_ffmpeg_command(args: Sequence[str]) -> int:
    print("Running:", " ".join(shlex.quote(a) for a in args))
    proc = subprocess.run(args)
    return proc.returncode


def derive_output_path(input_path: Path, factor: float, output_path: Optional[Path]) -> Path:
    if output_path is not None:
        return output_path
    stem = input_path.stem
    return input_path.with_name(f"{stem}.slomo{factor}x.mp4")


def convert_to_slomo(opts: SlomoOptions) -> None:
    ffmpeg = find_ffmpeg_executable()

    # Determine final output fps
    input_fps = probe_input_fps(ffmpeg, opts.input_path)
    base_out_fps = opts.out_fps or input_fps or 30.0

    # Build video filter chain
    vf = build_ffmpeg_filters(factor=opts.factor, out_fps=base_out_fps, interpolation_quality="high")

    # Build audio filter args
    audio_args: List[str]
    if opts.audio_mode == "mute":
        audio_args = ["-an"]
    else:
        target_tempo = 1.0 / opts.factor
        atempos = build_atempo_chain(target_tempo)
        atempo_filter = ",".join(f"atempo={t:.8f}" for t in atempos)
        audio_args = [
            "-filter:a",
            atempo_filter,
            "-c:a",
            "aac",
            "-b:a",
            opts.audio_bitrate,
        ]

    # Video encoding args
    v_args = [
        "-vf",
        vf,
        "-c:v",
        opts.video_codec,
        "-preset",
        opts.video_preset,
        "-crf",
        str(opts.video_crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
    ]

    t_args: List[str] = []
    if opts.threads and opts.threads > 0:
        t_args = ["-threads", str(opts.threads)]

    cmd: List[str] = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-i",
        str(opts.input_path),
        *v_args,
        *audio_args,
        *t_args,
        str(opts.output_path),
    ]

    rc = run_ffmpeg_command(cmd)
    if rc != 0:
        raise SystemExit(rc)


def parse_args(argv: Optional[Sequence[str]] = None) -> SlomoOptions:
    p = argparse.ArgumentParser(description="Smooth slow-motion video converter (FFmpeg-based)")
    p.add_argument("input", type=Path, help="Input video file path")
    p.add_argument("--out", dest="output", type=Path, default=None, help="Output video file path (default: <input>.slomo<factor>x.mp4)")
    p.add_argument("--factor", type=float, default=2.0, help="Slowdown factor (e.g., 2.0 = 2x slower)")
    p.add_argument("--out-fps", type=float, default=None, help="Final output FPS (default: input FPS if detectable, else 30)")
    p.add_argument("--video-preset", default="slow", help="x264 preset (ultrafast..veryslow)")
    p.add_argument("--video-crf", type=int, default=18, help="x264 CRF quality (lower is better; 18 is visually lossless)")
    p.add_argument("--video-codec", default="libx264", help="Video codec (e.g., libx264, libx265)")
    p.add_argument("--audio", choices=["keep", "mute"], default="keep", help="Audio handling: keep (pitch-preserving) or mute")
    p.add_argument("--audio-bitrate", default="192k", help="Audio bitrate when keeping audio")
    p.add_argument("--threads", type=int, default=None, help="Limit encoder threads (optional)")

    ns = p.parse_args(argv)

    if ns.factor <= 0:
        p.error("--factor must be > 0")

    input_path: Path = ns.input
    if not input_path.exists():
        p.error(f"Input does not exist: {input_path}")

    output_path = derive_output_path(input_path, ns.factor, ns.output)

    return SlomoOptions(
        input_path=input_path,
        output_path=output_path,
        factor=float(ns.factor),
        out_fps=float(ns.out_fps) if ns.out_fps is not None else None,
        video_preset=str(ns.video_preset),
        video_crf=int(ns.video_crf),
        video_codec=str(ns.video_codec),
        audio_mode=str(ns.audio),
        audio_bitrate=str(ns.audio_bitrate),
        threads=int(ns.threads) if ns.threads is not None else None,
    )


def main(argv: Optional[Sequence[str]] = None) -> None:
    opts = parse_args(argv)
    convert_to_slomo(opts)


if __name__ == "__main__":
    main()
