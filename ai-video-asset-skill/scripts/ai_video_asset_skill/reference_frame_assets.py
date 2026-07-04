"""Selected video-reference frame workflow for storyboard/image generation."""

from __future__ import annotations

import json
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from .file_manager import (
    MARKET_MINING_DIR_NAME,
    RESEARCH_DIR_NAME,
    SELECTED_REFERENCE_DIR_NAME,
    STORYBOARD_DIR_NAME,
    VIDEO_REFERENCE_DIR_NAME,
    ensure_dir,
    read_json,
    relative_path,
    shot_json_file,
    write_json,
)
from .video_reference_assets import _build_contact_sheet, _rebuild_aggregate_manifest
from .video_scene_reference_assets import collect_scene_reference_frames


MARKET_MINING_DIR = Path(RESEARCH_DIR_NAME) / MARKET_MINING_DIR_NAME
VIDEO_REFERENCE_DIR = Path(RESEARCH_DIR_NAME) / VIDEO_REFERENCE_DIR_NAME
SELECTED_REFERENCE_DIR = Path(RESEARCH_DIR_NAME) / SELECTED_REFERENCE_DIR_NAME
TEMPLATE_EXCLUSION_TERMS = [
    "模板",
    "模版",
    "AE模板",
    "AE模版",
    "PR模板",
    "PR模版",
    "工程文件",
    "片头模板",
    "片头模版",
    "开场模板",
    "开场模版",
    "展示模板",
    "展示模版",
    "字幕条",
    "LOGO演绎",
    "MOGRT",
]
NON_VIDEO_SRC_FILE_TYPES = {"TEMPLATE", "PACKAGE", "PPT"}
REFERENCE_FRAME_ANALYSIS_SYSTEM_PROMPT = (
    "你是一个专业的参考帧视觉解析与商业 AI 生图提示词工程智能体。必须逐张观察分析拼图中的图片，"
    "必要时打开单张精选帧复核；禁止只根据 frame_id、文件名、作品标题、历史分析文本或 JSON 元数据判断。"
    "按 frame_ids 顺序写回 JSON frames 数组，每个元素必须包含 frame_id、sheet_label、ai_prompt_analysis，"
    "并新增结构化字段 visual_summary、subject_type、scene_type、shot_role_tags、composition_tags、"
    "motion_potential、commercial_use_cases、topic_fit_score、image2_usage_weight、reference_use_policy、"
    "risk_flags、prompt_ready_brief、negative_prompt_notes。"
    "ai_prompt_analysis 保留中文可读分析，格式为：主体：；背景：；构图：；视角/镜头：；光线：；色彩：；"
    "风格：；材质与细节：；情绪氛围：；空一行后输出【中文生图提示词】，再空一行后输出【负面提示词】。"
    "subject_type 用简短中文描述主体类型，例如人物、产品、建筑、自然景观、工业设备、医疗场景、教育场景、"
    "食物、节日道具、抽象氛围。scene_type 描述空间或环境类型。shot_role_tags 必须从这些英文标签中选择："
    "establishing、main_subject、process_action、detail_closeup、people_usage、transition_mood、"
    "outcome_emotion、end_copy_space，可多选。composition_tags 可包含 wide、medium、closeup、macro、"
    "top_view、low_angle、silhouette、copy_space、symmetry、depth、reflection。motion_potential 用中文写"
    "适合生视频的动作潜力。commercial_use_cases 写这张图适合素材包中的用途，例如片头、产品展示、签约动作、"
    "转场、结尾留白。topic_fit_score 为 0-100，image2_usage_weight 为 0-1；reference_use_policy 只能是 "
    "image2_reference、composition_only、style_only、evidence_only、exclude。risk_flags 标注文字、Logo、"
    "水印、品牌、人物身份、过暗、模糊、多宫格、低相关等风险。prompt_ready_brief 是可直接进入生图提示词的"
    "中文视觉 brief，不能添加图中不存在的主体；negative_prompt_notes 只写负面提示词要点。"
)


def prepare_high_value_video_frame_queue(
    project_dir: str | Path,
    max_works: int = 10,
    strict_video_material: bool = True,
) -> Dict[str, Any]:
    project_path = Path(project_dir)
    details = _read_jsonl(project_path / MARKET_MINING_DIR / "光厂第二轮作品详情.jsonl")
    directions = _read_directions(project_path / MARKET_MINING_DIR / "商业AI方向.json")
    direction_by_work = _direction_by_work_id(directions)
    topic_terms = _read_project_topic_terms(project_path)
    selected, rejected = _select_high_value_video_works_with_rejections(
        details,
        direction_by_work,
        max_works=max_works,
        strict_video_material=strict_video_material,
        topic_terms=topic_terms,
    )
    queue_dir = ensure_dir(project_path / VIDEO_REFERENCE_DIR)
    queue_path = write_json(
        queue_dir / "高价值视频拆帧队列.json",
        {
            "schema_version": "high-value-video-frame-queue/v1",
            "project_dir": str(project_path),
            "generated_at": _now(),
            "max_works": max_works,
            "strict_video_material": strict_video_material,
            "topic_terms": topic_terms,
            "selection_policy": "second-pass works sorted by material_income, purchase_count, click_count, market_signal_score; only VJShi 视频素材 works with a public sample/preview video URL are queued; template/project-file works are rejected.",
            "works": selected,
            "rejected_count": len(rejected),
            "rejected_works": rejected,
        },
    )
    return {
        "system_output_success": True,
        "system_output_queue": str(queue_path),
        "system_output_work_count": len(selected),
        "system_output_rejected_count": len(rejected),
        "works": selected,
    }


def select_high_value_video_works(
    details: Sequence[Dict[str, Any]],
    direction_by_work_id: Dict[str, str] | None = None,
    max_works: int = 10,
    strict_video_material: bool = True,
    topic_terms: Sequence[str] | None = None,
) -> List[Dict[str, Any]]:
    selected, _ = _select_high_value_video_works_with_rejections(
        details,
        direction_by_work_id,
        max_works=max_works,
        strict_video_material=strict_video_material,
        topic_terms=topic_terms,
    )
    return selected


def _select_high_value_video_works_with_rejections(
    details: Sequence[Dict[str, Any]],
    direction_by_work_id: Dict[str, str] | None = None,
    max_works: int = 10,
    strict_video_material: bool = True,
    topic_terms: Sequence[str] | None = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    direction_by_work_id = direction_by_work_id or {}
    candidates = []
    rejected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for work in details:
        work_id = str(work.get("work_id") or _work_id_from_url(work.get("work_url") or ""))
        source_url = str(work.get("sample_video_url") or work.get("preview_video_url") or "")
        if not source_url or not work_id or work_id in seen:
            if work_id and work_id not in seen:
                rejected.append(_rejected_work_record(work, ["missing_public_sample_or_preview_video_url"]))
            continue
        if not (work.get("sample_video_url") or work.get("preview_video_url")):
            rejected.append(_rejected_work_record(work, ["missing_public_sample_or_preview_video_url"]))
            continue
        rejection_reasons = _video_work_rejection_reasons(
            work,
            strict_video_material=strict_video_material,
            topic_terms=topic_terms,
        )
        if rejection_reasons:
            rejected.append(_rejected_work_record(work, rejection_reasons))
            continue
        seen.add(work_id)
        score = _market_score(work)
        candidates.append(
            (
                score,
                {
                    "work_id": work_id,
                    "title": work.get("title", ""),
                    "work_url": work.get("work_url", ""),
                    "source_url": source_url,
                    "sample_video_url": work.get("sample_video_url", ""),
                    "preview_video_url": work.get("preview_video_url", ""),
                    "preview_video_source": work.get("preview_video_source", ""),
                    "search_keyword": work.get("search_keyword", ""),
                    "source_rank": work.get("rank"),
                    "source_market_signal": score,
                    "commercial_direction": direction_by_work_id.get(work_id, ""),
                    "material_type": work.get("material_type", ""),
                    "src_file_type": work.get("src_file_type", ""),
                    "declared_duration": work.get("duration", ""),
                    "declared_duration_seconds": _duration_to_seconds(work.get("duration")),
                    "material_income": _float(work.get("material_income")),
                    "purchase_count": _int(work.get("purchase_count")),
                    "click_count": _int(work.get("click_count")),
                    "market_signal_score": _int(work.get("market_signal_score")),
                },
            )
        )
    candidates.sort(
        key=lambda item: (
            -float(item[1]["material_income"]),
            -int(item[1]["purchase_count"]),
            -int(item[1]["click_count"]),
            -int(item[1]["market_signal_score"]),
            str(item[1]["work_id"]),
        )
    )
    return [item for _, item in candidates[: max(0, max_works)]], rejected


def collect_high_value_video_frames(
    project_dir: str | Path,
    max_works: int = 30,
    initial_works: int = 10,
    min_total_frames: int = 300,
    max_frames_per_source: int = 0,
    scene_threshold: float = 0.28,
    min_scene_duration: float = 0.6,
    max_scene_duration: float = 0.0,
    strict_video_material: bool = True,
    watermark_preset: str | None = "光厂",
    watermark_rect: str | Sequence[int] | Dict[str, Any] | None = None,
    watermark_backend: str = "auto",
    overwrite: bool = False,
    workers: int = 6,
    watermark_device: str = "cpu",
) -> Dict[str, Any]:
    project_path = Path(project_dir)
    queue_result = prepare_high_value_video_frame_queue(
        project_path,
        max_works=max_works,
        strict_video_material=strict_video_material,
    )
    works = list(queue_result["works"])
    worker_count = max(1, min(int(workers or 1), max(1, len(works))))
    collected_by_rank: List[Dict[str, Any] | None] = [None] * len(works)
    errors_by_rank: List[Dict[str, Any] | None] = [None] * len(works)
    completed_work_count = 0
    aggregate = _rebuild_aggregate_manifest(project_path / VIDEO_REFERENCE_DIR, project_path)
    total_frame_count = _aggregate_frame_count(aggregate, project_path)

    def collect_one(rank: int, work: Dict[str, Any]) -> tuple[int, Dict[str, Any] | None, Dict[str, Any] | None]:
        try:
            result = collect_scene_reference_frames(
                work["source_url"],
                project_dir=project_path,
                title=f"排行{rank + 1:02d}_{work.get('work_id', '')}_{work.get('title', '')}",
                threshold=scene_threshold,
                min_scene_duration=min_scene_duration,
                max_scene_duration=max_scene_duration,
                max_scenes=max_frames_per_source,
                watermark_preset=watermark_preset,
                watermark_rect=watermark_rect,
                watermark_backend=watermark_backend,
                overwrite=overwrite,
                rebuild_aggregate=False,
                watermark_device=watermark_device,
            )
            return rank, {**work, "collection_result": result, "sample_integrity": _sample_integrity_report(work, result, project_path)}, None
        except Exception as error:  # keep batch collection resilient
            return rank, None, {**work, "error": str(error)}

    batch_size = max(1, int(initial_works or 10))
    next_rank = 0
    while works and next_rank < len(works):
        if next_rank > 0 and min_total_frames > 0 and total_frame_count >= min_total_frames:
            break
        batch_end = min(len(works), next_rank + batch_size)
        batch = list(enumerate(works[next_rank:batch_end], start=next_rank))
        with ThreadPoolExecutor(max_workers=min(worker_count, len(batch))) as executor:
            futures = [executor.submit(collect_one, rank, work) for rank, work in batch]
            for future in as_completed(futures):
                rank, collected, error = future.result()
                if collected is not None:
                    collected_by_rank[rank] = collected
                if error is not None:
                    errors_by_rank[rank] = error
        completed_work_count = batch_end
        aggregate = _rebuild_aggregate_manifest(project_path / VIDEO_REFERENCE_DIR, project_path)
        total_frame_count = _aggregate_frame_count(aggregate, project_path)
        next_rank = batch_end

    collected = [item for item in collected_by_rank if item is not None]
    errors = [item for item in errors_by_rank if item is not None]
    aggregate = _rebuild_aggregate_manifest(project_path / VIDEO_REFERENCE_DIR, project_path)
    total_frame_count = _aggregate_frame_count(aggregate, project_path)
    if not works:
        stop_reason = "no_queued_works"
    elif min_total_frames > 0 and total_frame_count >= min_total_frames:
        stop_reason = "reached_min_total_frames"
    elif completed_work_count >= len(works):
        stop_reason = "reached_max_works"
    else:
        stop_reason = "stopped"
    output_path = write_json(
        project_path / VIDEO_REFERENCE_DIR / "高价值视频拆帧记录.json",
        {
            "schema_version": "high-value-video-frame-collection/v1",
            "generated_at": _now(),
            "initial_works": initial_works,
            "max_works": max_works,
            "min_total_frames": min_total_frames,
            "max_frames_per_source": max_frames_per_source,
            "scene_threshold": scene_threshold,
            "min_scene_duration": min_scene_duration,
            "max_scene_duration": max_scene_duration,
            "strict_video_material": strict_video_material,
            "workers": worker_count,
            "watermark_device": watermark_device,
            "final_work_count": completed_work_count,
            "supplemental_work_count": max(0, completed_work_count - min(initial_works, completed_work_count)),
            "total_frame_count": total_frame_count,
            "stop_reason": stop_reason,
            "frame_limit_policy": "0 means no per-source frame limit; keep one representative frame per detected high-sensitivity scene; if total frames stay below min_total_frames, add more video-material works instead of every-frame sampling.",
            "collected": collected,
            "errors": errors,
        },
    )
    return {
        "system_output_success": True,
        "system_output_collection": str(output_path),
        "system_output_collected_count": len(collected),
        "system_output_error_count": len(errors),
        "system_output_initial_works": initial_works,
        "system_output_final_work_count": completed_work_count,
        "system_output_supplemental_work_count": max(0, completed_work_count - min(initial_works, completed_work_count)),
        "system_output_total_frame_count": total_frame_count,
        "system_output_stop_reason": stop_reason,
        "system_output_workers": worker_count,
        "system_output_aggregate_manifest": str(aggregate["manifest_path"]),
        "system_output_gallery": str(aggregate["gallery_path"]),
    }


def build_selected_reference_frames(
    project_dir: str | Path,
    max_sheet_items: int = 12,
) -> Dict[str, Any]:
    project_path = Path(project_dir)
    review = _read_operator_review(project_path)
    selected_ids = _selected_frame_ids(review)
    frame_rows = _read_video_reference_frames(project_path)
    selected_dir = ensure_dir(project_path / SELECTED_REFERENCE_DIR)
    frame_dir = ensure_dir(selected_dir / "帧图片")
    selected = []

    selected_index = 0
    for frame in frame_rows:
        frame_id = str(frame.get("frame_id") or "")
        if frame_id not in selected_ids:
            continue
        source_path = _resolve_project_path(project_path, frame.get("path") or frame.get("resolved_path") or "")
        if not source_path.exists():
            continue
        extension = source_path.suffix or ".jpg"
        selected_index += 1
        target = frame_dir / f"精选帧_{selected_index:04d}{extension}"
        shutil.copy2(source_path, target)
        record = {
            "schema_version": "selected-reference-frame/v1",
            "frame_id": frame_id,
            "source_work_id": _work_id_from_frame(frame),
            "source_work_url": frame.get("source_work_url", ""),
            "source_rank": frame.get("source_rank"),
            "source_market_signal": frame.get("source_market_signal"),
            "original_frame_path": str(source_path.resolve()),
            "selected_frame_path": str(target.resolve()),
            "selected_frame_relative_path": relative_path(target, project_path),
            "commercial_direction": frame.get("commercial_direction", ""),
            "selected_by_operator": True,
            "operator_label": selected_ids[frame_id],
            "allowed_usage": [
                "subject_reference",
                "composition_reference",
                "camera_language_reference",
                "lighting_reference",
                "commercial_texture_reference",
            ],
            "similarity_policy": "Allowed as visual reference, but final generated image should stay below 90% similarity to the source frame.",
            "source_frame": frame,
        }
        selected.append(record)

    selected_path = write_json(
        selected_dir / "精选参考帧清单.json",
        {
            "schema_version": "selected-reference-frames/v1",
            "generated_at": _now(),
            "project_dir": str(project_path),
            "selected_count": len(selected),
            "frames": selected,
        },
    )
    sheet_result = build_reference_frame_analysis_tasks(project_path, selected, max_sheet_items=max_sheet_items)
    return {
        "system_output_success": True,
        "system_output_selected_reference_frames": str(selected_path),
        "system_output_selected_count": len(selected),
        **sheet_result,
    }


def build_reference_frame_analysis_tasks(
    project_dir: str | Path,
    selected_frames: Sequence[Dict[str, Any]] | None = None,
    max_sheet_items: int = 12,
) -> Dict[str, Any]:
    project_path = Path(project_dir)
    selected_dir = ensure_dir(project_path / SELECTED_REFERENCE_DIR)
    if selected_frames is None:
        payload = read_json(selected_dir / "精选参考帧清单.json")
        selected_frames = payload.get("frames", [])
    sheets_dir = ensure_dir(selected_dir / "分析拼图")
    tasks = []
    for index, batch in enumerate(_chunks(list(selected_frames), max(1, max_sheet_items)), start=1):
        image_paths = [Path(item["selected_frame_path"]) for item in batch if Path(item.get("selected_frame_path", "")).exists()]
        if not image_paths:
            continue
        sheet_path = _build_contact_sheet(image_paths, sheets_dir / f"拼图_{index:03d}.jpg")
        task = {
            "task_id": f"reference_frame_sheet_{index:03d}",
            "sheet_path": str(sheet_path.resolve()) if sheet_path else "",
            "sheet_relative_path": relative_path(sheet_path, project_path) if sheet_path else "",
            "frame_ids": [item["frame_id"] for item in batch],
            "analysis_instruction": (
                "Read analysis_system_prompt first. Inspect this contact sheet and, if needed, open single "
                "selected frames for visual verification. Write one structured JSON frame object for every "
                "frame_id in order, including the required visual summary, role tags, composition tags, "
                "topic fit, image2 weight, reference policy, prompt-ready brief, and negative notes."
            ),
        }
        tasks.append(task)
    tasks_path = write_json(
        selected_dir / "参考帧分析任务.json",
        {
            "schema_version": "reference-frame-analysis-tasks/v1",
            "generated_at": _now(),
            "batch_size": max_sheet_items,
            "analysis_system_prompt": REFERENCE_FRAME_ANALYSIS_SYSTEM_PROMPT,
            "tasks": tasks,
        },
    )
    analysis_path = selected_dir / "参考帧分析.json"
    if not analysis_path.exists():
        write_json(
            analysis_path,
            {
                "schema_version": "reference-frame-analysis/v1",
                "generated_at": "",
                "analysis_source": "pending_codex_visual_analysis",
                "expected_structured_fields": [
                    "visual_summary",
                    "subject_type",
                    "scene_type",
                    "shot_role_tags",
                    "composition_tags",
                    "motion_potential",
                    "commercial_use_cases",
                    "topic_fit_score",
                    "image2_usage_weight",
                    "reference_use_policy",
                    "risk_flags",
                    "prompt_ready_brief",
                    "negative_prompt_notes",
                ],
                "frames": [],
            },
        )
    return {
        "system_output_analysis_tasks": str(tasks_path),
        "system_output_reference_frame_analysis": str(analysis_path),
        "system_output_contact_sheet_count": len(tasks),
    }


def build_reference_frame_binding_plan(
    project_dir: str | Path,
    min_frames_per_shot: int = 1,
    max_reuse_per_frame: int = 3,
) -> Dict[str, Any]:
    project_path = Path(project_dir)
    storyboard = _read_storyboard(project_path)
    selected_payload = _read_json_default(project_path / SELECTED_REFERENCE_DIR / "精选参考帧清单.json", {"frames": []})
    analysis_payload = _read_json_default(project_path / SELECTED_REFERENCE_DIR / "参考帧分析.json", {"frames": []})
    selected_frames = selected_payload.get("frames", [])
    analysis_by_id = {str(item.get("frame_id")): item for item in analysis_payload.get("frames", []) if item.get("frame_id")}
    if not selected_frames:
        plan = {"schema_version": "reference-frame-binding-plan/v1", "generated_at": _now(), "items": []}
        path = write_json(project_path / RESEARCH_DIR_NAME / "参考帧绑定计划.json", plan)
        return {"system_output_success": True, "system_output_binding_plan": str(path), "system_output_bound_shot_count": 0}

    reuse: Dict[str, int] = {}
    items = []
    for shot in storyboard:
        matches = _match_reference_frames_for_shot(shot, selected_frames, analysis_by_id, reuse, max_reuse_per_frame)
        if matches:
            matches = matches[: max(1, min_frames_per_shot)]
        frame_ids = [item["frame_id"] for item in matches]
        for frame_id in frame_ids:
            reuse[frame_id] = reuse.get(frame_id, 0) + 1
        source_paths = [item["selected_frame_path"] for item in matches]
        notes = _reference_usage_notes(matches, analysis_by_id)
        shot["reference_frame_ids"] = frame_ids
        shot["reference_frame_paths"] = source_paths
        shot["reference_frame_usage_notes"] = notes
        shot.setdefault("reference_dependency", {})
        shot["reference_dependency"]["role"] = "standalone"
        shot["reference_dependency"]["anchor_shot_id"] = None
        shot["reference_dependency"]["reference_frame_ids"] = frame_ids
        shot["reference_dependency"]["reference_frame_paths"] = source_paths
        shot["reference_dependency"]["reference_frame_usage"] = notes
        shot["reference_dependency"]["reference_usage_role"] = _binding_usage_role(matches, analysis_by_id)
        items.append(
            {
                "shot_id": shot.get("shot_id"),
                "reference_role": "standalone",
                "reference_shot_id": None,
                "reference_frame_ids": frame_ids,
                "source_image_paths": source_paths,
                "reference_usage_notes": notes,
                "reference_usage_role": _binding_usage_role(matches, analysis_by_id),
            }
        )

    plan = {
        "schema_version": "reference-frame-binding-plan/v1",
        "generated_at": _now(),
        "selection_policy": "Match storyboard text to Codex frame analysis and selected frame metadata; reference frames are optional, standalone, and dynamically reused 0-3 times by visual value.",
        "reuse_counts": reuse,
        "items": items,
    }
    binding_path = write_json(project_path / RESEARCH_DIR_NAME / "参考帧绑定计划.json", plan)
    write_json(project_path / STORYBOARD_DIR_NAME / "分镜总表.json", storyboard)
    for shot in storyboard:
        if shot.get("shot_id"):
            write_json(project_path / STORYBOARD_DIR_NAME / shot_json_file(shot["shot_id"]), shot)
    return {
        "system_output_success": True,
        "system_output_binding_plan": str(binding_path),
        "system_output_bound_shot_count": len(items),
    }


def _match_reference_frames_for_shot(
    shot: Dict[str, Any],
    frames: Sequence[Dict[str, Any]],
    analysis_by_id: Dict[str, Dict[str, Any]],
    reuse: Dict[str, int],
    max_reuse_per_frame: int,
) -> List[Dict[str, Any]]:
    shot_text = _search_text(shot)
    scored = []
    for frame in frames:
        frame_id = str(frame.get("frame_id") or "")
        analysis = analysis_by_id.get(frame_id, {})
        reuse_budget = min(max_reuse_per_frame, _binding_reuse_budget(frame, analysis))
        if reuse_budget <= 0 or reuse.get(frame_id, 0) >= reuse_budget:
            continue
        frame_text = _search_text(frame) + " " + _search_text(analysis)
        score = sum(1 for token in _tokens(frame_text) if token and token in shot_text)
        if frame.get("commercial_direction") and frame.get("commercial_direction") in shot_text:
            score += 4
        if score <= 0:
            continue
        score += float(analysis.get("reference_strength") or 0) * 0.1
        score += float(analysis.get("image2_usage_weight") or 0) * 2
        scored.append((score, frame_id, frame))
    scored.sort(key=lambda item: (-item[0], reuse.get(item[1], 0), item[1]))
    return [item[2] for item in scored if item[0] > 0]


def _binding_reuse_budget(frame: Dict[str, Any], analysis: Dict[str, Any]) -> int:
    policy = str(analysis.get("reference_use_policy") or frame.get("reference_use_policy") or "image2_reference")
    risk_text = _search_text([analysis.get("risk_flags", []), frame.get("risk_flags", [])])
    if policy in {"exclude", "evidence_only"}:
        return 0
    if any(keyword in risk_text for keyword in ["水印", "Logo", "logo", "文字", "多宫格", "低相关", "版权"]):
        return 0
    weight = _safe_float(analysis.get("image2_usage_weight", frame.get("image2_usage_weight", 0.6)), 0.6)
    if weight <= 0:
        return 0
    if policy in {"composition_only", "style_only"}:
        return 1
    tags = set(str(item) for item in analysis.get("shot_role_tags", []) if item)
    tags.update(str(item) for item in analysis.get("composition_tags", []) if item)
    text = _search_text([frame, analysis])
    if _binding_is_detail_reference(text, tags):
        return 1
    topic_fit = _safe_float(analysis.get("topic_fit_score", 70), 70)
    budget = 1
    if weight >= 0.72 and topic_fit >= 70:
        budget += 1
    if weight >= 0.86 and topic_fit >= 82 and (
        tags & {"establishing", "process_action", "people_usage", "wide", "depth", "outcome_emotion"}
        or any(keyword in text for keyword in ["握手", "会议", "团队", "城市", "空间", "合作", "成功"])
    ):
        budget += 1
    return max(0, min(3, budget))


def _binding_usage_role(frames: Sequence[Dict[str, Any]], analysis_by_id: Dict[str, Dict[str, Any]]) -> str:
    if not frames:
        return "original_planning"
    frame = frames[0]
    analysis = analysis_by_id.get(str(frame.get("frame_id") or ""), {})
    tags = set(str(item) for item in analysis.get("shot_role_tags", []) if item)
    tags.update(str(item) for item in analysis.get("composition_tags", []) if item)
    text = _search_text([frame, analysis])
    if _binding_is_detail_reference(text, tags):
        return "material_detail"
    if tags & {"process_action"}:
        return "action_pose"
    if tags & {"establishing", "wide"}:
        return "composition_light"
    if tags & {"people_usage"}:
        return "scene_relation"
    if tags & {"transition_mood", "reflection", "copy_space"}:
        return "light_mood"
    return "visual_reference"


def _binding_is_detail_reference(text: str, tags: set[str]) -> bool:
    if not tags & {"detail_closeup", "closeup", "macro"}:
        return False
    detail_keywords = ["微距", "极近", "局部", "手部", "笔尖", "钢笔", "指尖", "纸面", "袖口", "特写", "只截取", "裁切", "浅景深"]
    scene_keywords = ["宽幅", "远景", "中远景", "大厅", "团队", "多人围坐", "长桌两侧", "城市", "楼宇", "玻璃幕墙", "走廊", "高层会议室长桌"]
    if tags & {"wide", "establishing", "silhouette"}:
        return False
    return any(keyword in text for keyword in detail_keywords) and not any(keyword in text for keyword in scene_keywords)


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _reference_usage_notes(frames: Sequence[Dict[str, Any]], analysis_by_id: Dict[str, Dict[str, Any]]) -> str:
    parts = []
    for frame in frames:
        frame_id = frame.get("frame_id", "")
        analysis = analysis_by_id.get(str(frame_id), {})
        usage = analysis.get("suggested_prompt_usage") or analysis.get("suitable_shot_types") or frame.get("allowed_usage", [])
        parts.append(f"{frame_id}: reference subject, composition, camera language, lighting, and commercial texture; keep final similarity below 90%; usage={usage}")
    return " | ".join(parts)


def _read_video_reference_frames(project_path: Path) -> List[Dict[str, Any]]:
    manifest_path = project_path / VIDEO_REFERENCE_DIR / "视频参考帧清单.json"
    manifest = _read_json_default(manifest_path, {"assets": []})
    frames = list(manifest.get("assets", []))
    queue_by_source = _queue_by_source(project_path)
    for frame in frames:
        source_info = queue_by_source.get(str(frame.get("source_id") or ""), {})
        frame.setdefault("source_work_id", source_info.get("work_id", ""))
        frame.setdefault("source_work_url", source_info.get("work_url", ""))
        frame.setdefault("source_rank", source_info.get("source_rank"))
        frame.setdefault("source_market_signal", source_info.get("source_market_signal"))
        frame.setdefault("commercial_direction", source_info.get("commercial_direction", ""))
    return frames


def _queue_by_source(project_path: Path) -> Dict[str, Dict[str, Any]]:
    collection = _read_json_default(project_path / VIDEO_REFERENCE_DIR / "高价值视频拆帧记录.json", {"collected": []})
    output: Dict[str, Dict[str, Any]] = {}
    for item in collection.get("collected", []):
        result = item.get("collection_result", {})
        source_id = str(result.get("system_output_source_id") or "")
        if source_id:
            output[source_id] = item
    return output


def _selected_frame_ids(review: Dict[str, Any]) -> Dict[str, str]:
    output = {}
    labels = {"image2_reference", "high_value"}
    for frame_id, item in (review.get("frame_reviews") or {}).items():
        label = item.get("label") if isinstance(item, dict) else ""
        if label in labels:
            output[str(frame_id)] = str(label)
    return output


def _read_operator_review(project_path: Path) -> Dict[str, Any]:
    return _read_json_default(project_path / MARKET_MINING_DIR / "人工审核.json", {})


def _read_storyboard(project_path: Path) -> List[Dict[str, Any]]:
    return _read_json_default(project_path / STORYBOARD_DIR_NAME / "分镜总表.json", [])


def _read_directions(path: Path) -> List[Dict[str, Any]]:
    payload = _read_json_default(path, {"directions": []})
    if isinstance(payload, list):
        return payload
    return payload.get("directions", [])


def _direction_by_work_id(directions: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    output = {}
    for direction in directions:
        name = str(direction.get("direction_name") or "")
        for work_id in direction.get("evidence_work_ids", []) + direction.get("second_pass_evidence_work_ids", []):
            output[str(work_id)] = name
    return output


def _market_score(work: Dict[str, Any]) -> float:
    return (
        _float(work.get("material_income")) * 1000
        + _int(work.get("purchase_count")) * 100
        + _int(work.get("click_count")) * 5
        + _int(work.get("market_signal_score")) * 10
    )


def _video_work_rejection_reasons(
    work: Dict[str, Any],
    strict_video_material: bool = True,
    topic_terms: Sequence[str] | None = None,
) -> List[str]:
    reasons: List[str] = []
    src_file_type = str(work.get("src_file_type") or work.get("srcFileType") or "").upper()
    if src_file_type in NON_VIDEO_SRC_FILE_TYPES:
        reasons.append(f"src_file_type_{src_file_type.lower()}")
    if _has_template_marker(work):
        reasons.append("template_or_project_file_keyword")
    if strict_video_material and not _is_video_material_work(work):
        reasons.append("not_confirmed_vjshi_video_material")
    if topic_terms and not _has_topic_marker(work, topic_terms):
        reasons.append("off_topic_for_project_terms")
    return reasons


def _has_template_marker(work: Dict[str, Any]) -> bool:
    haystack = _search_text(
        [
            work.get("title"),
            work.get("material_type"),
            work.get("src_file_type"),
            work.get("category"),
            work.get("detail_keywords"),
        ]
    ).upper()
    return any(term.upper() in haystack for term in TEMPLATE_EXCLUSION_TERMS)


def _is_video_material_work(work: Dict[str, Any]) -> bool:
    src_file_type = str(work.get("src_file_type") or work.get("srcFileType") or "").upper()
    material_type = str(work.get("material_type") or "")
    if bool(work.get("video_material_filter")):
        return True
    if src_file_type == "VIDEO":
        return True
    if "视频素材" in material_type or (material_type == "视频"):
        return True
    urls = [work.get("source_search_url")] + list(work.get("source_search_urls") or [])
    return any("categoryIdForSoftware=230" in str(url) and "st=y" in str(url) for url in urls)


def _has_topic_marker(work: Dict[str, Any], topic_terms: Sequence[str]) -> bool:
    haystack = _search_text(
        [
            work.get("title"),
            work.get("detail_keywords"),
        ]
    )
    return any(term and term in haystack for term in topic_terms)


def _read_project_topic_terms(project_path: Path) -> List[str]:
    seed_payload = _read_json_default(project_path / MARKET_MINING_DIR / "种子关键词.json", {})
    summary_payload = _read_json_default(project_path / MARKET_MINING_DIR / "市场反挖摘要.json", {})
    terms: List[str] = []
    terms.extend(_split_topic_terms(seed_payload.get("topic")))
    for seed in seed_payload.get("seed_keywords", []):
        terms.extend(_split_topic_terms(seed))
    for prompt in summary_payload.get("buyer_search_prompts", [])[:12]:
        terms.extend(_split_topic_terms(prompt.get("prompt")))
    if any(term in terms for term in ["新能源汽车", "新能源", "汽车", "智能驾驶", "自动驾驶"]):
        terms.extend(
            [
                "新能源汽车",
                "新能源",
                "智能驾驶",
                "自动驾驶",
                "智驾",
                "无人驾驶",
                "智能座舱",
                "HUD",
                "充电桩",
                "充电站",
                "换电站",
                "动力电池",
                "固态电池",
                "锂电池",
                "汽车电池",
                "氢能源",
                "氢燃料",
                "电动汽车",
                "电车",
                "车联网",
                "车路协同",
                "智慧交通",
                "智慧出行",
                "绿色出行",
                "低碳",
                "零排放",
                "碳中和",
                "绿色能源",
                "汽车制造",
                "汽车工厂",
                "碳化硅",
                "永磁电机",
            ]
        )
    stop_terms = {"AI", "ai", "视频", "素材", "适配", "素材包", "科技", "合集", "绿色", "出行", "汽车", "驾驶", "智能", "充电", "电池"}
    cleaned = [term.strip() for term in terms if term and term.strip() not in stop_terms and len(term.strip()) >= 2]
    return _unique_preserve_order(cleaned)[:80]


def _split_topic_terms(value: Any) -> List[str]:
    text = str(value or "")
    parts = re.split(r"[,，;；、\s/|_]+", text)
    output = [part.strip() for part in parts if len(part.strip()) >= 2]
    for match in re.findall(r"[\u4e00-\u9fff]{2,10}", text):
        output.append(match)
    return output


def _unique_preserve_order(values: Sequence[str]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _rejected_work_record(work: Dict[str, Any], reasons: Sequence[str]) -> Dict[str, Any]:
    return {
        "work_id": str(work.get("work_id") or _work_id_from_url(work.get("work_url") or "")),
        "title": work.get("title", ""),
        "work_url": work.get("work_url", ""),
        "preview_video_url": work.get("preview_video_url", ""),
        "sample_video_url": work.get("sample_video_url", ""),
        "material_type": work.get("material_type", ""),
        "src_file_type": work.get("src_file_type", ""),
        "rejection_reasons": list(reasons),
    }


def _aggregate_frame_count(aggregate: Dict[str, Any], project_path: Path) -> int:
    direct_count = int(_float(aggregate.get("frame_count")) or 0)
    if direct_count > 0:
        return direct_count
    manifest_path = _resolve_manifest_path(project_path, aggregate.get("manifest_path"))
    if not manifest_path:
        return 0
    manifest = _read_json_default(manifest_path, {})
    return int(_float(manifest.get("frame_count")) or 0)


def _sample_integrity_report(work: Dict[str, Any], collection_result: Dict[str, Any], project_path: Path) -> Dict[str, Any]:
    declared_seconds = _float(work.get("declared_duration_seconds")) or _duration_to_seconds(work.get("declared_duration"))
    manifest_path = _resolve_manifest_path(project_path, collection_result.get("system_output_manifest"))
    actual_seconds = 0.0
    source_type = ""
    resolved_video_url = ""
    if manifest_path and manifest_path.exists():
        manifest = _read_json_default(manifest_path, {})
        video_info = manifest.get("video_info") or {}
        actual_seconds = _float(video_info.get("duration_seconds")) or _float(video_info.get("duration"))
        source_type = str(manifest.get("source_type") or "")
        resolved_video_url = str(manifest.get("resolved_video_url") or "")
    ratio = actual_seconds / declared_seconds if declared_seconds > 0 and actual_seconds > 0 else 0.0
    status = "not_checked"
    if declared_seconds > 0 and actual_seconds > 0:
        status = "ok" if ratio >= 0.8 else "shorter_than_declared_duration"
    elif actual_seconds > 0:
        status = "downloaded_without_declared_duration"
    return {
        "declared_duration_seconds": round(declared_seconds, 3) if declared_seconds else 0,
        "actual_downloaded_duration_seconds": round(actual_seconds, 3) if actual_seconds else 0,
        "duration_ratio": round(ratio, 3) if ratio else 0,
        "status": status,
        "source_type": source_type,
        "resolved_video_url": resolved_video_url,
        "note": "Use a public sample URL when available; contentUrl fallback may be a short preview and is flagged by duration_ratio.",
    }


def _resolve_manifest_path(project_path: Path, value: Any) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    project_candidate = project_path / path
    if project_candidate.exists():
        return project_candidate
    cwd_candidate = Path.cwd() / path
    if cwd_candidate.exists():
        return cwd_candidate
    return project_candidate


def _duration_to_seconds(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    match = re.fullmatch(r"(?:(\d+)')?(\d{1,2})", text)
    if match:
        return int(match.group(1) or 0) * 60 + int(match.group(2))
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*秒", text)
    if match:
        return float(match.group(1))
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*分钟", text)
    if match:
        return float(match.group(1)) * 60
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", text)
    if match:
        if match.group(3):
            return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3))
        return int(match.group(1)) * 60 + int(match.group(2))
    return 0.0


def _resolve_project_path(project_path: Path, value: Any) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path
    return project_path / path


def _work_id_from_frame(frame: Dict[str, Any]) -> str:
    if frame.get("source_work_id"):
        return str(frame["source_work_id"])
    return _work_id_from_url(frame.get("source_work_url") or frame.get("input_url") or "")


def _work_id_from_url(url: Any) -> str:
    text = str(url or "")
    marker = "/watch/"
    if marker in text:
        return text.split(marker, 1)[1].split(".", 1)[0].split("?", 1)[0]
    return ""


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError):
        return []


def _read_json_default(path: Path, default: Any) -> Any:
    try:
        return read_json(path)
    except Exception:
        return default


def _chunks(values: Sequence[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for index in range(0, len(values), size):
        yield list(values[index : index + size])


def _search_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_search_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_search_text(item) for item in value)
    return str(value or "")


def _tokens(text: str) -> List[str]:
    return [item for item in str(text).replace(",", " ").replace("，", " ").split() if len(item) >= 2]


def _int(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
