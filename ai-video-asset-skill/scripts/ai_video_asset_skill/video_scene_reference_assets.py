"""Collect one de-watermarked representative frame per TransNetV2 scene."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .file_manager import artifact_id, ensure_dir, write_json
from .video_reference_assets import (
    _build_contact_sheet,
    _frame_metrics,
    _manifest_path,
    _persist_selected_frames,
    _probe_video,
    _rebuild_aggregate_manifest,
    _require_cv2,
    _resolve_asset_root,
    _resolve_video_source,
    _resolve_watermark_region,
    _source_id,
    _title_from_url_or_path,
    _write_jsonl,
)


def collect_scene_reference_frames(
    source_url: str,
    project_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    title: str | None = None,
    threshold: float = 0.5,
    min_scene_duration: float = 2.0,
    max_scene_duration: float = 0.0,
    max_scenes: int = 0,
    watermark_preset: str | None = "\u5149\u5382",
    watermark_rect: str | Sequence[int] | Dict[str, Any] | None = None,
    watermark_backend: str = "auto",
    keep_raw_frames: bool = False,
    overwrite: bool = False,
    ffmpeg_path: str | Path | None = None,
    remwm_root: str | Path | None = None,
    transnet_root: str | Path | None = None,
    transnet_python: str | Path | None = None,
    transnet_weights: str | Path | None = None,
    rebuild_aggregate: bool = True,
    watermark_device: str = "cpu",
) -> Dict[str, Any]:
    """Resolve a video, split it with TransNetV2, and save one frame per scene."""

    if not source_url:
        raise ValueError("source_url is required")
    if watermark_backend not in {"auto", "remwm", "opencv", "none"}:
        raise ValueError("watermark_backend must be auto, remwm, opencv, or none")

    resolved_project = Path(project_dir) if project_dir else None
    asset_root = _resolve_asset_root(resolved_project, output_dir)
    ensure_dir(asset_root)

    source_title = title or _title_from_url_or_path(source_url)
    source_id = _source_id(source_url, f"{source_title}_单场景代表帧")
    source_dir = asset_root / "来源" / source_id
    source_manifest = source_dir / "来源信息.json"
    if source_manifest.exists() and not overwrite:
        aggregate = _rebuild_aggregate_manifest(asset_root, resolved_project) if rebuild_aggregate else {}
        frame_count = (
            int(aggregate.get("source_frame_counts", {}).get(source_id, 0))
            if aggregate
            else _count_jsonl_rows(source_dir / "索引" / "参考帧索引.jsonl")
        )
        return {
            "system_output_success": True,
            "system_output_reused_existing": True,
            "system_output_source_id": source_id,
            "system_output_source_dir": str(source_dir),
            "system_output_manifest": str(source_manifest),
            "system_output_aggregate_manifest": str(aggregate.get("manifest_path", "")),
            "system_output_frame_count": frame_count,
            "system_output_message": "已复用现有场景参考帧目录。传入 --overwrite 可重建。",
        }

    if source_dir.exists() and overwrite:
        shutil.rmtree(source_dir)

    raw_dir = ensure_dir(source_dir / "原视频")
    ensure_dir(source_dir / "镜头")
    ensure_dir(source_dir / "索引")

    resolved = _resolve_video_source(source_url, raw_dir, source_title, ffmpeg_path)
    video_path = Path(resolved["video_path"])
    video_info = _probe_video(video_path)

    scenes = _detect_transnet_scenes(
        video_path,
        threshold=threshold,
        min_scene_duration=min_scene_duration,
        max_scene_duration=max_scene_duration,
        transnet_python=transnet_python,
        transnet_root=transnet_root,
        transnet_weights=transnet_weights,
    )
    if max_scenes > 0:
        scenes = scenes[:max_scenes]
    selections = _select_scene_midpoint_frames(video_path, scenes)
    watermark_region = _resolve_watermark_region(watermark_preset, watermark_rect)
    frame_records, shot_records = _persist_selected_frames(
        selections,
        source_dir,
        source_id,
        resolved_project,
        watermark_region,
        watermark_backend,
        keep_raw_frames,
        remwm_root,
        watermark_device,
    )
    _attach_scene_bounds(frame_records, shot_records, scenes, source_dir)

    frames_index = _write_jsonl(source_dir / "索引" / "参考帧索引.jsonl", frame_records)
    shots_index = _write_jsonl(source_dir / "索引" / "镜头索引.jsonl", shot_records)
    contact_sheet = _build_contact_sheet(
        [Path(record["resolved_thumb_path"]) for record in frame_records],
        source_dir / "总览拼图.jpg",
    )
    transnet_scenes_path = write_json(
        source_dir / "场景切分.json",
        {
            "schema_version": "transnet-scenes/v1",
            "threshold": threshold,
            "min_scene_duration": min_scene_duration,
            "max_scene_duration": max_scene_duration or None,
            "scene_count": len(scenes),
            "scenes": scenes,
        },
    )

    manifest = {
        "schema_version": "video-reference-source/v1",
        "source_id": source_id,
        "title": source_title,
        "input_url": source_url,
        "resolved_video_url": resolved.get("video_url", ""),
        "source_type": resolved.get("source_type", ""),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_dir": _manifest_path(source_dir, resolved_project),
        "video_path": _manifest_path(video_path, resolved_project),
        "video_info": video_info,
        "options": {
            "frame_mode": "transnet-scene-one",
            "scene_detector": "TransNetV2",
            "threshold": threshold,
            "min_scene_duration": min_scene_duration,
            "max_scene_duration": max_scene_duration or 0.0,
            "max_scenes": max_scenes,
            "watermark_preset": watermark_preset or "",
            "watermark_rect": watermark_region or {},
            "watermark_backend": watermark_backend,
            "watermark_device": watermark_device,
            "keep_raw_frames": keep_raw_frames,
        },
        "summary": {
            "shot_count": len(shot_records),
            "frame_count": len(frame_records),
            "scene_count": len(scenes),
            "watermark_removed_count": sum(1 for item in frame_records if item.get("watermark_removed")),
            "watermark_backend_used": sorted(
                {str(item.get("watermark_backend_used")) for item in frame_records if item.get("watermark_backend_used")}
            ),
        },
        "indexes": {
            "frames_jsonl": _manifest_path(frames_index, resolved_project),
            "shots_jsonl": _manifest_path(shots_index, resolved_project),
            "transnet_scenes_json": _manifest_path(transnet_scenes_path, resolved_project),
            "contact_sheet": _manifest_path(contact_sheet, resolved_project) if contact_sheet else "",
        },
        "usage_policy": [
            "Use only as research reference for shot language, composition, color, and lighting.",
            "Use source frames as similar visual references only; keep final generated images below 90% similarity and remove logos, watermarks, people, and copyrighted elements.",
        ],
        "shots": shot_records,
    }
    write_json(source_manifest, manifest)
    aggregate = _rebuild_aggregate_manifest(asset_root, resolved_project) if rebuild_aggregate else {}

    return {
        "system_output_success": True,
        "system_output_reused_existing": False,
        "system_output_source_id": source_id,
        "system_output_source_dir": str(source_dir),
        "system_output_video_path": str(video_path),
        "system_output_manifest": str(source_manifest),
        "system_output_frames_index": str(frames_index),
        "system_output_shots_index": str(shots_index),
        "system_output_transnet_scenes": str(transnet_scenes_path),
        "system_output_contact_sheet": str(contact_sheet) if contact_sheet else "",
        "system_output_aggregate_manifest": str(aggregate.get("manifest_path", "")),
        "system_output_gallery": str(aggregate.get("gallery_path", "")),
        "system_output_frame_count": len(frame_records),
        "system_output_shot_count": len(shot_records),
        "system_output_scene_count": len(scenes),
        "system_output_message": "已完成 TransNetV2 场景参考帧采集：每个场景保留一张代表图。",
    }


def _detect_transnet_scenes(
    video_path: Path,
    threshold: float,
    min_scene_duration: float,
    max_scene_duration: float,
    transnet_python: str | Path | None,
    transnet_root: str | Path | None,
    transnet_weights: str | Path | None,
) -> List[Dict[str, Any]]:
    runtime = _resolve_transnet_runtime(transnet_python, transnet_root, transnet_weights)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        ascii_video = temp_path / f"input{video_path.suffix or '.mp4'}"
        scene_json = temp_path / "scenes.json"
        shutil.copy2(video_path, ascii_video)
        code = r"""
import json
import sys
from pathlib import Path

video_path = Path(sys.argv[1])
transnet_root = Path(sys.argv[2])
weights = Path(sys.argv[3])
threshold = float(sys.argv[4])
min_scene_duration = float(sys.argv[5])
max_scene_duration = float(sys.argv[6])
output_path = Path(sys.argv[7])

sys.path.insert(0, str(transnet_root))
from video_scene_splitter import VideoSceneSplitter

splitter = VideoSceneSplitter(
    threshold=threshold,
    min_scene_duration=min_scene_duration,
    max_scene_duration=max_scene_duration if max_scene_duration > 0 else None,
    model_dir=str(weights),
)
scenes = splitter.detect_scene_changes(str(video_path))
payload = []
for index, (start, end) in enumerate(scenes, start=1):
    payload.append({
        "scene_id": f"scene_{index:04d}",
        "start_seconds": round(float(start), 3),
        "end_seconds": round(float(end), 3),
        "midpoint_seconds": round((float(start) + float(end)) / 2.0, 3),
    })
output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
"""
        result = subprocess.run(
            [
                str(runtime["python"]),
                "-c",
                code,
                str(ascii_video),
                str(runtime["root"]),
                str(runtime["weights"]),
                str(threshold),
                str(min_scene_duration),
                str(max_scene_duration or 0.0),
                str(scene_json),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=1800,
        )
        if result.returncode != 0 or not scene_json.exists():
            message = result.stderr.strip() or result.stdout.strip() or "TransNetV2 scene detection failed"
            raise RuntimeError(message)
        scenes = json.loads(scene_json.read_text(encoding="utf-8-sig"))
    if not scenes:
        raise RuntimeError("TransNetV2 did not return any valid scenes")
    return scenes


def _resolve_transnet_runtime(
    transnet_python: str | Path | None,
    transnet_root: str | Path | None,
    transnet_weights: str | Path | None,
) -> Dict[str, Path]:
    default_root = _first_existing(_picvideos_roots()) or _picvideos_roots()[0]
    root = Path(transnet_root or os.environ.get("AI_VIDEO_TRANSNET_ROOT") or default_root)
    python_path = Path(
        transnet_python
        or os.environ.get("AI_VIDEO_TRANSNET_PYTHON")
        or root / ".venv" / "Scripts" / "python.exe"
    )
    weights = Path(transnet_weights or os.environ.get("AI_VIDEO_TRANSNET_WEIGHTS") or root / "transnetv2-weights")
    if not root.exists():
        raise RuntimeError(f"TransNetV2 root not found: {root}")
    if not python_path.exists():
        raise RuntimeError(f"TransNetV2 Python not found: {python_path}")
    if not weights.exists():
        raise RuntimeError(f"TransNetV2 weights not found: {weights}")
    return {"root": root, "python": python_path, "weights": weights}


def _picvideos_roots() -> List[Path]:
    skill_root = Path(__file__).resolve().parents[2]
    roots = [
        skill_root.parent / "picVideos",
        skill_root.parent.parent / "picVideos",
    ]
    output: List[Path] = []
    seen = set()
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            output.append(root)
    return output


def _first_existing(candidates: List[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _select_scene_midpoint_frames(video_path: Path, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cv2 = _require_cv2()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    selections: List[Dict[str, Any]] = []
    try:
        for scene in scenes:
            timestamp = float(scene["midpoint_seconds"])
            frame_index = max(0, min(max(frame_count - 1, 0), int(round(timestamp * fps))))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            metrics = _frame_metrics(frame)
            selections.append(
                {
                    "shot_id": scene["scene_id"],
                    "frame": frame,
                    "timestamp": timestamp,
                    "frame_index": frame_index,
                    "quality_score": metrics["quality_score"],
                    "brightness": metrics["brightness"],
                    "sharpness": metrics["sharpness"],
                    "scene_diff": 0.0,
                }
            )
    finally:
        cap.release()
    if not selections:
        raise RuntimeError("No scene midpoint frames could be decoded")
    return selections


def _attach_scene_bounds(
    frame_records: List[Dict[str, Any]],
    shot_records: List[Dict[str, Any]],
    scenes: List[Dict[str, Any]],
    source_dir: Path,
) -> None:
    scenes_by_id = {item["scene_id"]: item for item in scenes}
    for record in frame_records:
        scene = scenes_by_id.get(record["shot_id"])
        if scene:
            record["scene_start_seconds"] = scene["start_seconds"]
            record["scene_end_seconds"] = scene["end_seconds"]
            record["scene_midpoint_seconds"] = scene["midpoint_seconds"]
    for record in shot_records:
        scene = scenes_by_id.get(record["shot_id"])
        if scene:
            record["scene_id"] = scene["scene_id"]
            record["start_seconds"] = scene["start_seconds"]
            record["end_seconds"] = scene["end_seconds"]
            record["duration_seconds"] = round(float(scene["end_seconds"]) - float(scene["start_seconds"]), 3)
            record["scene_midpoint_seconds"] = scene["midpoint_seconds"]
            write_json(source_dir / "镜头" / artifact_id(record["shot_id"]) / "镜头信息.json", record)


def _count_jsonl_rows(path: Path) -> int:
    try:
        return sum(1 for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip())
    except OSError:
        return 0
