"""Check local runtime dependencies for ai-video-asset-skill."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


def _module_status(import_name: str, package_name: str | None = None) -> dict[str, Any]:
    found = importlib.util.find_spec(import_name) is not None
    return {
        "name": package_name or import_name,
        "import": import_name,
        "ok": found,
        "install": f"python -m pip install {package_name or import_name}",
    }


def _first_existing(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_picvideos_roots() -> list[Path]:
    skill_root = _skill_root()
    roots = [
        skill_root.parent / "picVideos",
        skill_root.parent.parent / "picVideos",
    ]
    output = []
    seen = set()
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            output.append(root)
    return output


def _ffmpeg_status() -> dict[str, Any]:
    env_path = os.environ.get("AI_VIDEO_FFMPEG")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend(root / "ffmpeg" / "bin" / "ffmpeg.exe" for root in _default_picvideos_roots())
    which_path = shutil.which("ffmpeg")
    if which_path:
        candidates.append(Path(which_path))
    resolved = _first_existing(candidates)
    return {
        "name": "ffmpeg",
        "ok": resolved is not None,
        "path": str(resolved) if resolved else "",
        "env": "AI_VIDEO_FFMPEG",
        "used_for": "m3u8/public preview video download",
    }


def _remwm_status() -> dict[str, Any]:
    env_path = os.environ.get("AI_VIDEO_REMWM_ROOT")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend(root / "remwm-win" for root in _default_picvideos_roots())
    root = None
    exe = None
    model = None
    for candidate in candidates:
        candidate_exe = candidate / "bin" / "remwm-bin" / "remwm.exe"
        candidate_model = candidate / "models" / "big-lama.pt"
        if candidate_exe.exists() and candidate_model.exists():
            root = candidate
            exe = candidate_exe
            model = candidate_model
            break
    return {
        "name": "remwm",
        "ok": root is not None,
        "root": str(root) if root else "",
        "exe": str(exe) if exe else "",
        "model": str(model) if model else "",
        "env": "AI_VIDEO_REMWM_ROOT",
        "used_for": "optional high-quality watermark removal; opencv fallback is available",
    }


def _transnet_status() -> dict[str, Any]:
    default_root = _first_existing(_default_picvideos_roots()) or _default_picvideos_roots()[0]
    root = Path(os.environ.get("AI_VIDEO_TRANSNET_ROOT") or default_root)
    python_path = Path(
        os.environ.get("AI_VIDEO_TRANSNET_PYTHON")
        or root / ".venv" / "Scripts" / "python.exe"
    )
    weights = Path(os.environ.get("AI_VIDEO_TRANSNET_WEIGHTS") or root / "transnetv2-weights")
    ok = root.exists() and python_path.exists() and weights.exists()
    return {
        "name": "TransNetV2",
        "ok": ok,
        "root": str(root),
        "python": str(python_path),
        "weights": str(weights),
        "env": [
            "AI_VIDEO_TRANSNET_ROOT",
            "AI_VIDEO_TRANSNET_PYTHON",
            "AI_VIDEO_TRANSNET_WEIGHTS",
        ],
        "used_for": "collect-scene-frames and high-value scene splitting",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict-video",
        action="store_true",
        help="Fail if optional video-processing tools are missing.",
    )
    args = parser.parse_args()

    python_packages = [
        _module_status("numpy"),
        _module_status("cv2", "opencv-python"),
        _module_status("PIL", "Pillow"),
    ]
    external_tools = [_ffmpeg_status(), _remwm_status(), _transnet_status()]
    required_ok = all(item["ok"] for item in python_packages)
    video_ok = all(item["ok"] for item in external_tools)
    payload = {
        "python": sys.version.split()[0],
        "required_python_packages": python_packages,
        "optional_video_tools": external_tools,
        "ok": required_ok and (video_ok if args.strict_video else True),
        "strict_video": args.strict_video,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
