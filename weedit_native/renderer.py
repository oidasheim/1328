"""Backend-neutral RenderAST contract and FFmpeg implementation."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Protocol

from .models import RenderAST


class Backend(Protocol):
    def render(self, ast: RenderAST, output: str | Path) -> Path: ...


class FFmpegBackend:
    def __init__(self, prefer_nvenc: bool = True):
        self.prefer_nvenc = prefer_nvenc

    def render(self, ast: RenderAST, output: str | Path) -> Path:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg was not found on PATH")
        target = Path(output).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite: {target}")
        clip_paths = list(dict.fromkeys(str(Path(s.clip_path).resolve()) for s in ast.shots))
        missing = [p for p in clip_paths if not Path(p).is_file()]
        if missing: raise FileNotFoundError(missing[0])
        if not Path(ast.audio_path).is_file(): raise FileNotFoundError(ast.audio_path)
        cmd = [ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", ast.audio_path]
        for path in clip_paths: cmd.extend(["-i", path])
        filters, labels = [], []
        for i, shot in enumerate(ast.shots):
            source = clip_paths.index(str(Path(shot.clip_path).resolve())) + 1
            label = f"v{i}"
            duration = shot.duration
            # Clone-frame padding handles source clips shorter than the requested shot.
            filters.append(
                f"[{source}:v]trim=start={shot.source_in:.6f}:duration={duration:.6f},"
                f"setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={duration:.6f},"
                f"trim=duration={duration:.6f},scale={ast.width}:{ast.height}:"
                f"force_original_aspect_ratio=increase,crop={ast.width}:{ast.height},"
                f"fps={ast.fps},format=yuv420p[{label}]"
            )
            labels.append(f"[{label}]")
        filters.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[outv]")
        encoders = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True,
                                  text=True, check=False).stdout
        use_nvenc = self.prefer_nvenc and "h264_nvenc" in encoders
        cmd += ["-filter_complex", ";".join(filters), "-map", "[outv]", "-map", "0:a:0?",
                "-t", f"{ast.duration:.6f}", "-map_metadata", "-1", "-map_chapters", "-1",
                "-sn", "-dn", "-c:v", "h264_nvenc" if use_nvenc else "libx264"]
        cmd += ["-preset", "p4", "-cq", "19"] if use_nvenc else ["-preset", "medium", "-crf", "20"]
        cmd += ["-c:a", "aac", "-b:a", "320k", "-r", str(ast.fps), str(target)]
        subprocess.run(cmd, check=True)
        return target
