# Runtime Setup

This repository contains the skill source code, workflow scripts, Electron viewer source, tests, and PRD documents. It intentionally does not contain generated project outputs, downloaded preview videos, extracted frames, local caches, `node_modules`, or third-party binary/model bundles.

## Included

- `ai-video-asset-skill/SKILL.md`
- `ai-video-asset-skill/agents/openai.yaml`
- `ai-video-asset-skill/scripts/`
- `ai-video-asset-skill/references/`
- `ai-video-asset-skill/electron-viewer/`
- `ai-video-asset-skill/tests/`
- `docs/`

## Not Included

- `ai-video-asset-skill/output/`
- `ai-video-asset-skill/perf_tests/`
- `ai-video-asset-skill/scripts/projects/`
- `ai-video-asset-skill/scripts/video_reference_assets*/`
- `ai-video-asset-skill/scripts/_tmp*/`
- `ai-video-asset-skill/electron-viewer/node_modules/`
- local `ffmpeg`, `remwm`, TransNetV2 virtualenvs, and model weights

These files are either generated, bulky, machine-specific, or third-party artifacts that should be installed or configured outside the Git repository.

## Base Python Setup

From the repository root:

```powershell
cd .\ai-video-asset-skill
python -m pip install -r .\requirements.txt
python .\scripts\check_runtime.py
python -m pytest .\tests -q
```

The basic storyboard and mock-placeholder workflows can run without the optional video tools:

```powershell
cd .\ai-video-asset-skill\scripts
python .\run_mvp.py run --total-shots 20 --provider mock_placeholder
```

## Optional Electron Viewer

```powershell
cd .\ai-video-asset-skill\electron-viewer
npm install
npm start
```

## Optional Video Tooling

Video reference-frame collection uses additional local tools.

### ffmpeg

Required for downloading or remuxing `m3u8` preview videos.

Configure either:

```powershell
$env:AI_VIDEO_FFMPEG="D:\tools\ffmpeg\bin\ffmpeg.exe"
```

or make `ffmpeg` available on `PATH`.

### remwm

Optional. Used for higher-quality watermark removal. If it is absent, the scripts can fall back to OpenCV inpainting or `--watermark-backend none`.

Expected layout:

```text
remwm-win/
  bin/remwm-bin/remwm.exe
  models/big-lama.pt
```

Configure:

```powershell
$env:AI_VIDEO_REMWM_ROOT="D:\tools\remwm-win"
```

### TransNetV2

Required for `collect-scene-frames` and high-value scene splitting.

Configure:

```powershell
$env:AI_VIDEO_TRANSNET_ROOT="D:\tools\picVideos"
$env:AI_VIDEO_TRANSNET_PYTHON="D:\tools\picVideos\.venv\Scripts\python.exe"
$env:AI_VIDEO_TRANSNET_WEIGHTS="D:\tools\picVideos\transnetv2-weights"
```

The scripts also keep a backward-compatible local fallback: if a nearby `picVideos/` directory exists next to the skill folder or next to the skill folder's parent and contains `ffmpeg`, `remwm-win`, `.venv`, and `transnetv2-weights`, it can be used automatically. Public users should prefer the environment variables above.

Check the full video runtime:

```powershell
python .\ai-video-asset-skill\scripts\check_runtime.py --strict-video
```

## Cost and Storage Notes

- Use `mock_placeholder` for offline checks; it does not call image generation APIs.
- Use `codex_image2` only when ready to spend generation quota.
- `collect-video-frames` defaults to keyframes to avoid unnecessary storage growth.
- Use `--mode every-frame --max-frames 0` only when dense frame extraction is genuinely needed.
- Do not commit generated outputs, extracted frames, secrets, cookies, paid source media, or private customer project files.
