"""Collect public preview video frames as structured research reference assets."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from .file_manager import (
    RESEARCH_DIR_NAME,
    VIDEO_REFERENCE_DIR_NAME,
    artifact_id,
    ensure_dir,
    relative_path,
    slug_text,
    write_json,
    write_text,
)
from .market_mining import fetch_vjshi_work_detail


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".flv", ".wmv", ".m3u8"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

DEFAULT_WATERMARK_PRESETS: Dict[str, Dict[str, int]] = {
    "光厂": {
        "x": 109,
        "y": 248,
        "width": 256,
        "height": 50,
        "base_width": 960,
        "base_height": 540,
    }
}


def collect_video_reference_frames(
    source_url: str,
    project_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    title: str | None = None,
    frame_mode: str = "keyframes",
    sample_every_seconds: float = 1.5,
    scan_every_seconds: float = 0.75,
    max_frames: int = 48,
    max_frames_per_shot: int = 3,
    scene_threshold: float = 18.0,
    min_brightness: float = 8.0,
    watermark_preset: str | None = "光厂",
    watermark_rect: str | Sequence[int] | Dict[str, Any] | None = None,
    watermark_backend: str = "auto",
    keep_raw_frames: bool = False,
    overwrite: bool = False,
    ffmpeg_path: str | Path | None = None,
    remwm_root: str | Path | None = None,
    watermark_device: str = "cpu",
) -> Dict[str, Any]:
    """Download/resolve a public preview video and save de-watermarked reference frames.

    The default mode stores key reference frames, not every decoded video frame.
    Use ``frame_mode="every-frame"`` deliberately when a dense frame dump is required.
    """

    if not source_url:
        raise ValueError("source_url is required")
    if frame_mode not in {"keyframes", "sample", "every-frame"}:
        raise ValueError("frame_mode must be keyframes, sample, or every-frame")
    if watermark_backend not in {"auto", "remwm", "opencv", "none"}:
        raise ValueError("watermark_backend must be auto, remwm, opencv, or none")

    resolved_project = Path(project_dir) if project_dir else None
    asset_root = _resolve_asset_root(resolved_project, output_dir)
    ensure_dir(asset_root)

    source_title = title or _title_from_url_or_path(source_url)
    source_id = _source_id(source_url, source_title)
    source_dir = asset_root / "来源" / source_id
    source_manifest = source_dir / "来源信息.json"
    if source_manifest.exists() and not overwrite:
        aggregate = _rebuild_aggregate_manifest(asset_root, resolved_project)
        return {
            "system_output_success": True,
            "system_output_reused_existing": True,
            "system_output_source_id": source_id,
            "system_output_source_dir": str(source_dir),
            "system_output_manifest": str(source_manifest),
            "system_output_aggregate_manifest": str(aggregate.get("manifest_path", "")),
            "system_output_frame_count": int(aggregate.get("source_frame_counts", {}).get(source_id, 0)),
            "system_output_message": "已存在相同链接的参考帧目录；未重复下载。传入 --overwrite 可重建。",
        }

    if source_dir.exists() and overwrite:
        shutil.rmtree(source_dir)

    raw_dir = ensure_dir(source_dir / "原视频")
    ensure_dir(source_dir / "镜头")
    ensure_dir(source_dir / "索引")

    resolved = _resolve_video_source(source_url, raw_dir, source_title, ffmpeg_path)
    video_path = Path(resolved["video_path"])
    video_info = _probe_video(video_path)

    watermark_region = _resolve_watermark_region(watermark_preset, watermark_rect)
    extraction_options = {
        "frame_mode": frame_mode,
        "sample_every_seconds": sample_every_seconds,
        "scan_every_seconds": scan_every_seconds,
        "max_frames": max_frames,
        "max_frames_per_shot": max_frames_per_shot,
        "scene_threshold": scene_threshold,
        "min_brightness": min_brightness,
        "watermark_preset": watermark_preset or "",
        "watermark_rect": watermark_region or {},
        "watermark_backend": watermark_backend,
        "watermark_device": watermark_device,
        "keep_raw_frames": keep_raw_frames,
    }

    selections = _select_reference_frames(
        video_path,
        frame_mode=frame_mode,
        sample_every_seconds=sample_every_seconds,
        scan_every_seconds=scan_every_seconds,
        max_frames=max_frames,
        max_frames_per_shot=max_frames_per_shot,
        scene_threshold=scene_threshold,
        min_brightness=min_brightness,
    )
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

    frames_index = _write_jsonl(source_dir / "索引" / "参考帧索引.jsonl", frame_records)
    shots_index = _write_jsonl(source_dir / "索引" / "镜头索引.jsonl", shot_records)
    contact_sheet = _build_contact_sheet(
        [Path(record["resolved_thumb_path"]) for record in frame_records],
        source_dir / "总览拼图.jpg",
    )

    manifest = {
        "schema_version": "video-reference-source/v1",
        "source_id": source_id,
        "title": source_title,
        "input_url": source_url,
        "resolved_video_url": resolved.get("video_url", ""),
        "source_type": resolved.get("source_type", ""),
        "generated_at": _now(),
        "source_dir": _manifest_path(source_dir, resolved_project),
        "video_path": _manifest_path(video_path, resolved_project),
        "video_info": video_info,
        "options": extraction_options,
        "summary": {
            "shot_count": len(shot_records),
            "frame_count": len(frame_records),
            "watermark_removed_count": sum(1 for item in frame_records if item.get("watermark_removed")),
            "watermark_backend_used": _unique_nonempty(item.get("watermark_backend_used") for item in frame_records),
        },
        "indexes": {
            "frames_jsonl": _manifest_path(frames_index, resolved_project),
            "shots_jsonl": _manifest_path(shots_index, resolved_project),
            "contact_sheet": _manifest_path(contact_sheet, resolved_project) if contact_sheet else "",
        },
        "usage_policy": [
            "仅用于市场调研、镜头语言拆解、构图/色彩/光线方向参考，不作为最终交付素材。",
            "正式生图可相似参考镜头语言和商业质感，但与来源帧相似度目标不得超过 90%，且不得保留人物、品牌、Logo、水印、包装或可识别版权元素。",
            "默认抽取关键帧以节省本地存储和后续检索成本；确需密集拆帧时才使用 every-frame 模式。",
        ],
        "shots": shot_records,
    }
    write_json(source_manifest, manifest)
    aggregate = _rebuild_aggregate_manifest(asset_root, resolved_project)

    return {
        "system_output_success": True,
        "system_output_reused_existing": False,
        "system_output_source_id": source_id,
        "system_output_source_dir": str(source_dir),
        "system_output_video_path": str(video_path),
        "system_output_manifest": str(source_manifest),
        "system_output_frames_index": str(frames_index),
        "system_output_shots_index": str(shots_index),
        "system_output_contact_sheet": str(contact_sheet) if contact_sheet else "",
        "system_output_aggregate_manifest": str(aggregate["manifest_path"]),
        "system_output_gallery": str(aggregate["gallery_path"]),
        "system_output_frame_count": len(frame_records),
        "system_output_shot_count": len(shot_records),
        "system_output_message": "公开预览视频参考帧已采集并写入索引。",
    }


def _resolve_asset_root(project_dir: Path | None, output_dir: str | Path | None) -> Path:
    if output_dir:
        return Path(output_dir)
    if project_dir:
        return project_dir / RESEARCH_DIR_NAME / VIDEO_REFERENCE_DIR_NAME
    return Path.cwd() / VIDEO_REFERENCE_DIR_NAME


def _source_id(source_url: str, title: str) -> str:
    date_part = datetime.now().strftime("%Y-%m-%d")
    slug = slug_text(title, max_length=36)
    url_hash = hashlib.sha256(str(source_url).encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"来源_{date_part}_{slug}_{url_hash}"


def _resolve_video_source(
    source_url: str,
    raw_dir: Path,
    title: str,
    ffmpeg_path: str | Path | None,
) -> Dict[str, str]:
    local_path = Path(source_url)
    if local_path.exists() and local_path.is_file():
        suffix = local_path.suffix.lower() if local_path.suffix.lower() in VIDEO_EXTENSIONS else ".mp4"
        target = raw_dir / f"原视频{suffix}"
        shutil.copy2(local_path, target)
        return {
            "source_type": "local_file",
            "video_url": "",
            "video_path": str(target),
        }

    if _looks_like_video_url(source_url):
        video_url = source_url
        target = _download_video_url(video_url, raw_dir, title, referer=None, ffmpeg_path=ffmpeg_path)
        return {
            "source_type": "direct_video_url",
            "video_url": video_url,
            "video_path": str(target),
        }

    video_url = ""
    source_type = "web_page"
    if "vjshi.com" in urllib.parse.urlparse(source_url).netloc.lower():
        try:
            detail = fetch_vjshi_work_detail(source_url)
            video_url = str(detail.get("sample_video_url") or detail.get("preview_video_url") or "")
            source_type = "vjshi_public_sample" if detail.get("sample_video_url") else "vjshi_public_preview"
        except Exception:
            video_url = ""
    if not video_url:
        html = _fetch_text(source_url)
        video_url = _extract_first_video_url(html, source_url)
    if not video_url:
        raise RuntimeError(f"未能从链接中解析公开预览视频地址: {source_url}")

    target = _download_video_url(video_url, raw_dir, title, referer=source_url, ffmpeg_path=ffmpeg_path)
    return {
        "source_type": source_type,
        "video_url": video_url,
        "video_path": str(target),
    }


def _looks_like_video_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return True
    lowered = url.lower()
    return any(token in lowered for token in [".mp4?", ".m3u8?", ".webm?"])


def _download_video_url(
    video_url: str,
    raw_dir: Path,
    title: str,
    referer: str | None,
    ffmpeg_path: str | Path | None,
) -> Path:
    parsed = urllib.parse.urlparse(video_url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix == ".m3u8" or ".m3u8" in video_url.lower():
        output_path = raw_dir / f"{slug_text(title, max_length=40) or '原视频'}.mp4"
        _download_stream_with_ffmpeg(video_url, output_path, referer, ffmpeg_path)
        return output_path

    ext = suffix if suffix in VIDEO_EXTENSIONS and suffix != ".m3u8" else ".mp4"
    output_path = raw_dir / f"{slug_text(title, max_length=40) or '原视频'}{ext}"
    request = urllib.request.Request(
        video_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "video/mp4,video/webm,application/octet-stream,*/*;q=0.8",
            "Referer": referer or "https://www.vjshi.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response, output_path.open("wb") as file:
        shutil.copyfileobj(response, file)
    if output_path.stat().st_size <= 0:
        raise RuntimeError(f"视频下载后为空: {video_url}")
    return output_path


def _download_stream_with_ffmpeg(
    video_url: str,
    output_path: Path,
    referer: str | None,
    ffmpeg_path: str | Path | None,
) -> None:
    ffmpeg = _resolve_ffmpeg(ffmpeg_path)
    headers = f"User-Agent: {USER_AGENT}\r\n"
    if referer:
        headers += f"Referer: {referer}\r\n"
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-headers",
        headers,
        "-i",
        video_url,
        "-c",
        "copy",
        "-y",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=600)
    if result.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"ffmpeg 下载流媒体失败: {result.stderr.strip() or result.stdout.strip()}")


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=35) as response:
        body = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    if body.startswith(b"\x1f\x8b"):
        import gzip

        body = gzip.decompress(body)
    try:
        return body.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return body.decode(charset, errors="replace")


def _extract_first_video_url(html: str, page_url: str) -> str:
    source = html.replace("\\/", "/").replace("\\u002F", "/")
    patterns = [
        r"https?://[^\"'<>\\\s]+?\.(?:mp4|m3u8|webm)(?:\?[^\"'<>\\\s]*)?",
        r"(?:src|contentUrl|videoUrl|preview_video_url)[\"']?\s*[:=]\s*[\"']([^\"']+\.(?:mp4|m3u8|webm)[^\"']*)[\"']",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, source, flags=re.I):
            candidate = match if isinstance(match, str) else match[0]
            if candidate.startswith("//"):
                candidate = "https:" + candidate
            return urllib.parse.urljoin(page_url, candidate)
    return ""


def _probe_video(video_path: Path) -> Dict[str, Any]:
    cv2 = _require_cv2()
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = frame_count / fps if fps > 0 and frame_count > 0 else 0.0
    capture.release()
    return {
        "width": width,
        "height": height,
        "fps": round(fps, 4),
        "frame_count": frame_count,
        "duration_seconds": round(duration, 3),
    }


def _select_reference_frames(
    video_path: Path,
    frame_mode: str,
    sample_every_seconds: float,
    scan_every_seconds: float,
    max_frames: int,
    max_frames_per_shot: int,
    scene_threshold: float,
    min_brightness: float,
) -> List[Dict[str, Any]]:
    cv2 = _require_cv2()
    np = _require_numpy()
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0) or 25.0
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if frame_count > 0 else 0.0

    if frame_mode == "every-frame":
        selections = _select_every_frame(capture, fps, max_frames, min_brightness)
        capture.release()
        return selections

    step_seconds = sample_every_seconds if frame_mode == "sample" else scan_every_seconds
    step_seconds = max(0.05, float(step_seconds or 1.0))
    groups: List[List[Dict[str, Any]]] = []
    current_group: List[Dict[str, Any]] = []
    previous_signature = None
    timestamp = 0.0
    scanned = 0
    scan_limit = 0 if max_frames <= 0 else max(max_frames * 8, max_frames + 24)

    while True:
        if duration > 0 and timestamp > duration:
            break
        if scan_limit and scanned >= scan_limit:
            break
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, frame = capture.read()
        if not ok:
            break
        frame_index = int(round(timestamp * fps))
        metrics = _frame_metrics(frame)
        if metrics["brightness"] >= min_brightness:
            signature = metrics["signature"]
            diff = (
                float(np.mean(np.abs(signature.astype("float32") - previous_signature.astype("float32"))))
                if previous_signature is not None
                else 0.0
            )
            if frame_mode == "keyframes" and current_group and diff >= scene_threshold:
                groups.append(current_group)
                current_group = []
            current_group.append(
                {
                    "timestamp": timestamp,
                    "frame_index": frame_index,
                    "frame": frame,
                    "quality_score": metrics["quality_score"],
                    "brightness": metrics["brightness"],
                    "sharpness": metrics["sharpness"],
                    "scene_diff": diff,
                }
            )
            previous_signature = signature
        timestamp += step_seconds
        scanned += 1

    capture.release()
    if current_group:
        groups.append(current_group)
    if not groups:
        raise RuntimeError("没有抽取到可用画面，可能视频为空、过暗或无法解码。")

    if frame_mode == "sample":
        flattened = [frame for group in groups for frame in group]
        selected = flattened if max_frames <= 0 else flattened[:max_frames]
        return [_with_shot_id(item, 1) for item in selected]

    selections: List[Dict[str, Any]] = []
    max_per_shot = max(1, int(max_frames_per_shot or 1))
    for shot_index, group in enumerate(groups, start=1):
        ranked = sorted(group, key=lambda item: (-item["quality_score"], item["timestamp"]))
        keep_timestamps = {id(item) for item in ranked[:max_per_shot]}
        chosen = [_with_shot_id(item, shot_index) for item in group if id(item) in keep_timestamps]
        selections.extend(chosen)

    selections.sort(key=lambda item: item["timestamp"])
    if max_frames > 0 and len(selections) > max_frames:
        ranked = sorted(selections, key=lambda item: (-item["quality_score"], item["timestamp"]))[:max_frames]
        keep = {id(item) for item in ranked}
        selections = [item for item in selections if id(item) in keep]
    return selections


def _select_every_frame(capture: Any, fps: float, max_frames: int, min_brightness: float) -> List[Dict[str, Any]]:
    selections: List[Dict[str, Any]] = []
    frame_index = 0
    while True:
        if max_frames > 0 and len(selections) >= max_frames:
            break
        ok, frame = capture.read()
        if not ok:
            break
        metrics = _frame_metrics(frame)
        if metrics["brightness"] >= min_brightness:
            selections.append(
                {
                    "timestamp": frame_index / fps if fps else 0,
                    "frame_index": frame_index,
                    "frame": frame,
                    "shot_id": "shot_0001",
                    "quality_score": metrics["quality_score"],
                    "brightness": metrics["brightness"],
                    "sharpness": metrics["sharpness"],
                    "scene_diff": 0.0,
                }
            )
        frame_index += 1
    if not selections:
        raise RuntimeError("没有抽取到可用画面，可能视频为空、过暗或无法解码。")
    return selections


def _with_shot_id(frame_item: Dict[str, Any], shot_index: int) -> Dict[str, Any]:
    copied = dict(frame_item)
    copied["shot_id"] = f"shot_{shot_index:04d}"
    return copied


def _frame_metrics(frame: Any) -> Dict[str, Any]:
    cv2 = _require_cv2()
    np = _require_numpy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    signature = cv2.resize(gray, (32, 18), interpolation=cv2.INTER_AREA)
    brightness_score = max(0.0, min(1.0, 1.0 - abs(brightness - 128.0) / 128.0))
    sharpness_score = max(0.0, min(1.0, sharpness / 450.0))
    quality_score = round((brightness_score * 0.35 + sharpness_score * 0.65) * 100, 2)
    return {
        "brightness": round(brightness, 2),
        "sharpness": round(sharpness, 2),
        "quality_score": quality_score,
        "signature": signature,
    }


def _persist_selected_frames(
    selections: List[Dict[str, Any]],
    source_dir: Path,
    source_id: str,
    project_dir: Path | None,
    watermark_region: Dict[str, Any] | None,
    watermark_backend: str,
    keep_raw_frames: bool,
    remwm_root: str | Path | None,
    watermark_device: str = "cpu",
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    cv2 = _require_cv2()
    frame_records: List[Dict[str, Any]] = []
    shots: Dict[str, List[Dict[str, Any]]] = {}

    for global_index, item in enumerate(selections, start=1):
        shot_id = item["shot_id"]
        shot_dir = ensure_dir(source_dir / "镜头" / artifact_id(shot_id))
        frames_dir = ensure_dir(shot_dir / "帧图片")
        thumbs_dir = ensure_dir(shot_dir / "缩略图")
        raw_frames_dir = ensure_dir(shot_dir / "原始帧") if keep_raw_frames else None
        frame_name = f"帧_{global_index:04d}.jpg"
        output_path = frames_dir / frame_name
        thumb_path = thumbs_dir / frame_name.replace(".jpg", ".webp")
        raw_frame_path = raw_frames_dir / frame_name if raw_frames_dir else None

        frame = item["frame"]
        if raw_frame_path:
            _imwrite(raw_frame_path, frame)
        backend_used = "none"
        watermark_removed = False
        if watermark_region and watermark_backend != "none":
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_input = Path(temp_dir) / "input.jpg"
                _imwrite(temp_input, frame)
                removed = _remove_watermark(
                    temp_input,
                    output_path,
                    frame,
                    watermark_region,
                    watermark_backend,
                    remwm_root,
                    watermark_device,
                )
                backend_used = removed["backend_used"]
                watermark_removed = removed["success"]
                if not removed["success"] and not output_path.exists():
                    _imwrite(output_path, frame)
        else:
            _imwrite(output_path, frame)

        _create_thumbnail(output_path, thumb_path)
        digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
        height, width = frame.shape[:2]
        record = {
            "schema_version": "video-reference-frame/v1",
            "frame_id": f"{source_id}_{artifact_id(shot_id)}_帧_{global_index:04d}",
            "source_id": source_id,
            "shot_id": shot_id,
            "path": _manifest_path(output_path, project_dir),
            "thumb_path": _manifest_path(thumb_path, project_dir),
            "raw_frame_path": _manifest_path(raw_frame_path, project_dir) if raw_frame_path else "",
            "resolved_path": str(output_path.resolve()),
            "resolved_thumb_path": str(thumb_path.resolve()),
            "timestamp_seconds": round(float(item["timestamp"]), 3),
            "frame_index": int(item["frame_index"]),
            "width": int(width),
            "height": int(height),
            "quality_score": item["quality_score"],
            "brightness": item["brightness"],
            "sharpness": item["sharpness"],
            "scene_diff": round(float(item.get("scene_diff", 0.0)), 3),
            "sha256": digest,
            "watermark_removed": watermark_removed,
            "watermark_backend_used": backend_used,
            "usage_notes": [
                "仅作视觉参考和 prompt/分镜分析，不作为最终交付素材。",
                "使用时提炼镜头语言、构图、光线和色彩；允许相似参考，但最终生成图与来源帧相似度目标不得超过 90%。",
            ],
        }
        frame_records.append(record)
        shots.setdefault(shot_id, []).append(record)

    shot_records = []
    for shot_id, records in sorted(shots.items()):
        start = min(item["timestamp_seconds"] for item in records)
        end = max(item["timestamp_seconds"] for item in records)
        average_quality = sum(float(item["quality_score"]) for item in records) / max(1, len(records))
        representative = sorted(records, key=lambda item: (-float(item["quality_score"]), item["timestamp_seconds"]))[0]
        shot_record = {
            "schema_version": "video-reference-shot/v1",
            "shot_id": shot_id,
            "source_id": source_id,
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "frame_count": len(records),
            "average_quality_score": round(average_quality, 2),
            "representative_frame_id": representative["frame_id"],
            "representative_frame_path": representative["path"],
            "frame_ids": [item["frame_id"] for item in records],
            "frame_paths": [item["path"] for item in records],
        }
        shot_records.append(shot_record)
        write_json(source_dir / "镜头" / artifact_id(shot_id) / "镜头信息.json", shot_record)

    return frame_records, shot_records


def _remove_watermark(
    image_path: Path,
    output_path: Path,
    frame: Any,
    watermark_region: Dict[str, Any],
    backend: str,
    remwm_root: str | Path | None,
    watermark_device: str,
) -> Dict[str, Any]:
    selected = backend
    if backend in {"auto", "remwm"}:
        try:
            _remove_watermark_with_remwm(
                image_path,
                output_path,
                frame,
                watermark_region,
                remwm_root,
                watermark_device,
            )
            return {"success": True, "backend_used": "remwm"}
        except Exception:
            if backend == "remwm":
                return {"success": False, "backend_used": "remwm"}
            selected = "opencv"
    if selected in {"auto", "opencv"}:
        try:
            _remove_watermark_with_opencv(output_path, frame, watermark_region)
            return {"success": True, "backend_used": "opencv"}
        except Exception:
            return {"success": False, "backend_used": "opencv"}
    return {"success": False, "backend_used": selected}


def _remove_watermark_with_remwm(
    image_path: Path,
    output_path: Path,
    frame: Any,
    watermark_region: Dict[str, Any],
    remwm_root: str | Path | None,
    watermark_device: str,
) -> None:
    cv2 = _require_cv2()
    np = _require_numpy()
    remwm_exe, model_path = _resolve_remwm(remwm_root)
    height, width = frame.shape[:2]
    x, y, w, h = _scaled_rect(watermark_region, width, height)
    if w <= 0 or h <= 0:
        raise RuntimeError("watermark region is outside the frame")

    with tempfile.TemporaryDirectory() as temp_dir:
        mask_path = Path(temp_dir) / "mask.png"
        temp_output = Path(temp_dir) / "output.jpg"
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[y : y + h, x : x + w] = 255
        cv2.imwrite(str(mask_path), mask)
        cmd = [
            str(remwm_exe),
            "--image",
            str(image_path),
            "--mask",
            str(mask_path),
            "--output",
            str(temp_output),
            "--model-path",
            str(model_path),
            "--device",
            str(watermark_device or "cpu"),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=180)
        if result.returncode != 0 or not temp_output.exists():
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "remwm failed")
        ensure_dir(output_path.parent)
        shutil.copy2(temp_output, output_path)


def _remove_watermark_with_opencv(output_path: Path, frame: Any, watermark_region: Dict[str, Any]) -> None:
    cv2 = _require_cv2()
    np = _require_numpy()
    height, width = frame.shape[:2]
    x, y, w, h = _scaled_rect(watermark_region, width, height)
    if w <= 0 or h <= 0:
        raise RuntimeError("watermark region is outside the frame")
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[y : y + h, x : x + w] = 255
    result = cv2.inpaint(frame, mask, 3, cv2.INPAINT_TELEA)
    _imwrite(output_path, result)


def _resolve_watermark_region(
    preset_name: str | None,
    watermark_rect: str | Sequence[int] | Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    if watermark_rect:
        if isinstance(watermark_rect, dict):
            return dict(watermark_rect)
        if isinstance(watermark_rect, str):
            parts = [int(float(item.strip())) for item in re.split(r"[,xX\s]+", watermark_rect) if item.strip()]
        else:
            parts = [int(item) for item in watermark_rect]
        if len(parts) not in {4, 6}:
            raise ValueError("watermark_rect must be x,y,width,height or x,y,width,height,base_width,base_height")
        data = {"x": parts[0], "y": parts[1], "width": parts[2], "height": parts[3]}
        if len(parts) == 6:
            data["base_width"] = parts[4]
            data["base_height"] = parts[5]
        return data
    if not preset_name:
        return None
    presets = _load_watermark_presets()
    preset = presets.get(preset_name)
    if not preset:
        raise ValueError(f"未知水印预设: {preset_name}")
    return dict(preset)


def _load_watermark_presets() -> Dict[str, Dict[str, Any]]:
    presets = dict(DEFAULT_WATERMARK_PRESETS)
    preset_path = Path(__file__).with_name("watermark_presets.json")
    if preset_path.exists():
        try:
            data = json.loads(preset_path.read_text(encoding="utf-8-sig"))
            for name, value in data.items():
                if isinstance(value, dict):
                    presets[name] = value
        except json.JSONDecodeError:
            pass
    return presets


def _scaled_rect(region: Dict[str, Any], frame_width: int, frame_height: int) -> tuple[int, int, int, int]:
    base_width = int(region.get("base_width") or frame_width)
    base_height = int(region.get("base_height") or frame_height)
    scale_x = frame_width / base_width if base_width else 1.0
    scale_y = frame_height / base_height if base_height else 1.0
    x = int(round(float(region.get("x", 0)) * scale_x))
    y = int(round(float(region.get("y", 0)) * scale_y))
    width = int(round(float(region.get("width", 0)) * scale_x))
    height = int(round(float(region.get("height", 0)) * scale_y))
    x = max(0, min(x, max(0, frame_width - 1)))
    y = max(0, min(y, max(0, frame_height - 1)))
    width = max(0, min(width, frame_width - x))
    height = max(0, min(height, frame_height - y))
    return x, y, width, height


def _resolve_ffmpeg(ffmpeg_path: str | Path | None) -> Path:
    candidates = []
    if ffmpeg_path:
        candidates.append(Path(ffmpeg_path))
    env_path = os.environ.get("AI_VIDEO_FFMPEG")
    if env_path:
        candidates.append(Path(env_path))
    skill_file = Path(__file__).resolve()
    candidates.extend(
        [
            skill_file.parents[4] / "picVideos" / "ffmpeg" / "bin" / "ffmpeg.exe",
            Path("ffmpeg"),
        ]
    )
    for candidate in candidates:
        if str(candidate) == "ffmpeg":
            return candidate
        if candidate.exists():
            return candidate
    return Path("ffmpeg")


def _resolve_remwm(remwm_root: str | Path | None) -> tuple[Path, Path]:
    candidates = []
    if remwm_root:
        root = Path(remwm_root)
        candidates.append(root)
    env_path = os.environ.get("AI_VIDEO_REMWM_ROOT")
    if env_path:
        candidates.append(Path(env_path))
    skill_file = Path(__file__).resolve()
    candidates.append(skill_file.parents[4] / "picVideos" / "remwm-win")
    for root in candidates:
        remwm_exe = root / "bin" / "remwm-bin" / "remwm.exe"
        model_path = root / "models" / "big-lama.pt"
        if remwm_exe.exists() and model_path.exists():
            return remwm_exe, model_path
    raise RuntimeError("remwm.exe 或 big-lama.pt 不存在")


def _imwrite(path: Path, image: Any) -> None:
    cv2 = _require_cv2()
    ensure_dir(path.parent)
    suffix = path.suffix or ".jpg"
    ok, encoded = cv2.imencode(suffix, image)
    if not ok:
        raise RuntimeError(f"无法编码图片: {path}")
    path.write_bytes(encoded.tobytes())


def _create_thumbnail(source_path: Path, thumb_path: Path) -> None:
    try:
        from PIL import Image
    except Exception:
        ensure_dir(thumb_path.parent)
        shutil.copy2(source_path, thumb_path)
        return
    ensure_dir(thumb_path.parent)
    with Image.open(source_path) as image:
        image = image.convert("RGB")
        image.thumbnail((360, 220))
        image.save(thumb_path, "WEBP", quality=78)


def _build_contact_sheet(image_paths: Sequence[Path], output_path: Path) -> Path | None:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    thumbs = []
    for path in image_paths[:60]:
        if not path.exists():
            continue
        try:
            image = Image.open(path).convert("RGB")
        except Exception:
            continue
        image.thumbnail((320, 190))
        canvas = Image.new("RGB", (320, 230), "white")
        canvas.paste(image, ((320 - image.width) // 2, 0))
        draw = ImageDraw.Draw(canvas)
        label_digits = "".join(char for char in path.stem if char.isdigit())
        label = f"#{label_digits[-4:]}" if label_digits else f"#{len(thumbs) + 1:04d}"
        draw.text((8, 202), label, fill=(20, 20, 20))
        thumbs.append(canvas)
    if not thumbs:
        return None
    cols = 3 if len(thumbs) >= 3 else len(thumbs)
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * 320, rows * 230), (245, 245, 245))
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((index % cols) * 320, (index // cols) * 230))
    ensure_dir(output_path.parent)
    sheet.save(output_path, quality=90)
    return output_path


def _rebuild_aggregate_manifest(asset_root: Path, project_dir: Path | None) -> Dict[str, Any]:
    sources = []
    frames: List[Dict[str, Any]] = []
    shots: List[Dict[str, Any]] = []
    source_frame_counts: Dict[str, int] = {}

    for source_manifest_path in sorted((asset_root / "来源").glob("*/来源信息.json")):
        try:
            manifest = json.loads(source_manifest_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        source_id = manifest.get("source_id", source_manifest_path.parent.name)
        source_frames = _read_jsonl(source_manifest_path.parent / "索引" / "参考帧索引.jsonl")
        source_shots = _read_jsonl(source_manifest_path.parent / "索引" / "镜头索引.jsonl")
        source_frame_counts[source_id] = len(source_frames)
        sources.append(
            {
                "source_id": source_id,
                "title": manifest.get("title", ""),
                "input_url": manifest.get("input_url", ""),
                "source_type": manifest.get("source_type", ""),
                "source_dir": manifest.get("source_dir", ""),
                "manifest_path": _manifest_path(source_manifest_path, project_dir),
                "frame_count": len(source_frames),
                "shot_count": len(source_shots),
                "contact_sheet": manifest.get("indexes", {}).get("contact_sheet", ""),
            }
        )
        frames.extend(source_frames)
        shots.extend(source_shots)

    frames_index = _write_jsonl(asset_root / "视频参考帧索引.jsonl", frames)
    shots_index = _write_jsonl(asset_root / "视频镜头索引.jsonl", shots)
    contact_sheet = _build_contact_sheet([Path(item["resolved_thumb_path"]) for item in frames], asset_root / "视频参考帧总览.jpg")
    aggregate = {
        "schema_version": "video-reference-assets/v1",
        "generated_at": _now(),
        "asset_root": _manifest_path(asset_root, project_dir),
        "source_count": len(sources),
        "shot_count": len(shots),
        "frame_count": len(frames),
        "frames_index": _manifest_path(frames_index, project_dir),
        "shots_index": _manifest_path(shots_index, project_dir),
        "contact_sheet": _manifest_path(contact_sheet, project_dir) if contact_sheet else "",
        "sources": sources,
        "assets": frames,
        "usage_policy": [
            "这些帧仅用于调研、镜头语言拆解、构图/光线/色彩参考和生图 prompt 规划。",
            "后续生成素材可相似参考镜头语言和商业质感，但与来源帧相似度目标不得超过 90%，且不得保留品牌、Logo、水印、人物或可识别版权元素。",
        ],
    }
    manifest_path = write_json(asset_root / "视频参考帧清单.json", aggregate)
    gallery_path = write_text(asset_root / "视频参考帧说明.md", _build_gallery_markdown(aggregate))
    return {
        "manifest_path": manifest_path,
        "gallery_path": gallery_path,
        "source_frame_counts": source_frame_counts,
    }


def _build_gallery_markdown(manifest: Dict[str, Any]) -> str:
    lines = [
        "# 视频小样参考帧索引",
        "",
        "> 这些画面只用于调研和提示词规划。使用时提炼镜头语言、构图、光线和色彩；允许相似参考，但最终生成图与来源帧相似度目标不得超过 90%。",
        "",
    ]
    if manifest.get("contact_sheet"):
        lines.extend(["## 总览", "", f"![视频参考帧总览]({manifest['contact_sheet']})", ""])
    for source in manifest.get("sources", []):
        lines.extend(
            [
                f"## {source.get('source_id', '')} {source.get('title', '')}",
                "",
                f"- 来源：{source.get('input_url', '')}",
                f"- 画面数：{source.get('frame_count', 0)}",
                f"- 镜头组：{source.get('shot_count', 0)}",
                f"- manifest：`{source.get('manifest_path', '')}`",
                "",
            ]
        )
    for asset in manifest.get("assets", [])[:80]:
        lines.extend(
            [
                f"### {asset.get('frame_id', '')}",
                "",
                f"- 时间：{asset.get('timestamp_seconds', '')}s",
                f"- 质量分：{asset.get('quality_score', '')}",
                f"- 文件：`{asset.get('path', '')}`",
                "",
                f"![{asset.get('frame_id', '')}]({asset.get('thumb_path') or asset.get('path', '')})",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> Path:
    ensure_dir(path.parent)
    content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text((content + "\n") if content else "", encoding="utf-8")
    return path


def _manifest_path(path: str | Path | None, project_dir: Path | None) -> str:
    if path is None:
        return ""
    return relative_path(Path(path), project_dir) if project_dir else str(path)


def _title_from_url_or_path(value: str) -> str:
    path = Path(value)
    if path.exists():
        return path.stem
    parsed = urllib.parse.urlparse(value)
    name = Path(parsed.path).stem
    if name:
        return urllib.parse.unquote(name)
    return parsed.netloc.removeprefix("www.") or "video_reference"


def _unique_nonempty(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _require_cv2() -> Any:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("需要安装 opencv-python 后才能抽帧。") from exc
    return cv2


def _require_numpy() -> Any:
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("需要安装 numpy 后才能处理画面。") from exc
    return np
