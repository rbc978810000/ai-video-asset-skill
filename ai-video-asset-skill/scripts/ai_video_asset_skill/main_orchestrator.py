"""AI 视频素材 MVP 的总控入口。"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .config import DEFAULT_OUTPUT_ROOT, build_style_bible, merge_input
from .file_manager import (
    CURRENT_IMAGE_FILE,
    EXPORT_DIR_NAME,
    IMAGE_DIR_NAME,
    INPUT_DIR_NAME,
    MARKET_MINING_DIR_NAME,
    PROJECT_MANIFEST_FILE,
    PROMPT_DIR_NAME,
    RESEARCH_DIR_NAME,
    REFERENCE_ASSETS_DIR_NAME,
    REVIEW_DIR_NAME,
    REVIEW_FILE,
    SELECTED_REFERENCE_DIR_NAME,
    STORYBOARD_DIR_NAME,
    STYLE_BIBLE_FILE,
    TOPIC_BRIEF_FILE,
    VIDEO_REFERENCE_DIR_NAME,
    append_json_list,
    artifact_id,
    copy_file,
    create_project_dirs,
    ensure_dir,
    find_existing_project_dir,
    prompt_json_file,
    init_review_files,
    next_image_version_path,
    read_json,
    relative_path,
    shot_json_file,
    slug_text,
    write_csv,
    write_json,
    write_text,
)
from .image_generator_adapter import generate_image
from .image_prompt_builder import build_image_prompt, build_regeneration_prompt
from .image_review_engine import review_image, summarize_reviews
from .jiaozi_storyboard_export import audit_jiaozi_storyboard_script, export_jiaozi_storyboard_script
from .market_reference_assets import collect_market_reference_assets
from .market_mining import fetch_vjshi_work_detail, fetch_vjshi_work_details_batch, mine_market
from .production_text import clean_visual_phrase, clean_visual_terms
from .video_reference_assets import collect_video_reference_frames
from .video_scene_reference_assets import collect_scene_reference_frames
from .reference_image_planner import (
    attach_market_reference_assets,
    build_reference_image_plan,
    reference_plan_for_shot,
)
from .reference_frame_assets import (
    build_reference_frame_binding_plan,
    build_selected_reference_frames,
    collect_high_value_video_frames,
    prepare_high_value_video_frame_queue,
)
from .research_planner import (
    build_research_brief_markdown,
    build_research_plan,
    normalize_source_notes,
)
from .storyboard_planner import (
    build_storyboard_planner_prompt,
    generate_mock_storyboard,
    storyboard_csv_fields,
    storyboard_csv_rows,
)
from .vjshi_search import fetch_vjshi_search_results
from .variation_expander import expand_variations
from .visual_taxonomy_builder import build_visual_research_outputs

def run_skill(user_input: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """创建完整的分镜、提示词和生图任务项目。"""

    settings = merge_input(user_input)
    created_at = datetime.now()
    dirs = create_project_dirs(settings, created_at=created_at)
    project_dir = dirs["project_dir"]
    init_review_files(dirs["review_dir"])
    archived_inputs = _archive_project_inputs(settings, dirs)

    market_mining_summary_path = settings.get("user_input_market_mining_summary_path")
    source_notes = _load_research_notes(settings.get("user_input_research_notes_path"))
    source_notes.extend(_load_market_mining_notes(market_mining_summary_path))
    if market_mining_summary_path and not settings.get("user_input_shot_group_plan"):
        mined_shot_group_plan = _load_market_mining_shot_group_plan(market_mining_summary_path)
        if mined_shot_group_plan:
            settings["user_input_shot_group_plan"] = mined_shot_group_plan
    research_plan = build_research_plan(settings)
    research_outputs = build_visual_research_outputs(settings, source_notes)
    write_json(dirs["research_dir"] / "搜索词.json", research_plan["search_queries"])
    write_text(dirs["research_dir"] / "调研说明.md", build_research_brief_markdown(research_plan))
    write_json(dirs["research_dir"] / "来源笔记.json", research_outputs["source_notes"])
    write_json(dirs["research_dir"] / "代表画面.json", research_outputs["representative_visuals"])
    write_json(dirs["research_dir"] / "视觉分类.json", research_outputs["visual_taxonomy"])
    write_json(dirs["research_dir"] / "市场信号映射.json", research_outputs["market_signal_map"])
    write_json(dirs["research_dir"] / "视觉需求矩阵.json", research_outputs["visual_demand_matrix"])
    write_json(dirs["research_dir"] / "创意角度.json", research_outputs["creative_angles"])
    write_json(dirs["research_dir"] / "镜头组规划.json", research_outputs["shot_group_plan"])

    style_bible = build_style_bible(settings)
    write_json(project_dir / STYLE_BIBLE_FILE, style_bible)
    script_brief_path = write_json(
        dirs["input_dir"] / "脚本创作简报.json",
        _build_script_brief(settings, style_bible, research_outputs, market_mining_summary_path),
    )
    write_text(project_dir / TOPIC_BRIEF_FILE, _topic_brief(settings, created_at))
    write_text(
        dirs["storyboard_dir"] / "分镜规划提示词.md",
        build_storyboard_planner_prompt(settings, research_outputs["shot_group_plan"]),
    )

    storyboard = generate_mock_storyboard(settings, style_bible, research_outputs["shot_group_plan"])
    reference_plan = build_reference_image_plan(storyboard, project_dir)
    reference_plan = attach_market_reference_assets(
        reference_plan,
        storyboard,
        project_dir,
        settings.get("user_input_market_reference_assets_path"),
    )
    _attach_reference_dependencies_to_storyboard(storyboard, reference_plan)
    write_json(dirs["research_dir"] / "参考图规划.json", reference_plan)
    prompt_paths: List[str] = []
    generated_paths: List[str] = []
    reviews: List[Dict[str, Any]] = []

    for shot in storyboard:
        shot_id = shot["shot_id"]
        shot_path = dirs["storyboard_dir"] / shot_json_file(shot_id)
        prompt_data = build_image_prompt(shot, style_bible, settings["user_input_aspect_ratio"])
        shot_reference_plan = reference_plan_for_shot(reference_plan, shot_id) or {}
        shot_reference_dependency = shot.get("reference_dependency") or _reference_dependency_from_plan(shot_reference_plan)
        prompt_path = dirs["prompt_dir"] / prompt_json_file(shot_id)
        write_json(prompt_path, prompt_data)
        prompt_paths.append(str(prompt_path))
        shot["generate_status"] = "prompt_created"

        if settings.get("user_input_generate_images", True):
            shot["generate_status"] = "generating"
            shot_image_dir = dirs["image_dir"] / artifact_id(shot_id)
            image_path = shot_image_dir / "版本1.png"
            generation = generate_image(
                prompt_data["prompt"],
                image_path,
                {
                    "provider": settings.get("user_input_image_provider", "codex_image2"),
                    "overwrite": True,
                    "negative_prompt": prompt_data.get("negative_prompt", ""),
                    "aspect_ratio": prompt_data.get("aspect_ratio", settings["user_input_aspect_ratio"]),
                    "reference_image_plan": shot_reference_plan,
                    "reference_dependency": shot_reference_dependency,
                    "reference_frame_ids": shot.get("reference_frame_ids", []),
                    "reference_frame_paths": shot.get("reference_frame_paths", []),
                    "reference_frame_usage_notes": shot.get("reference_frame_usage_notes", ""),
                    "reference_image_path": shot_reference_plan.get("reference_image_path", ""),
                    "market_reference_asset_paths": shot_reference_plan.get("market_reference_asset_paths", []),
                    "market_reference_asset_ids": shot_reference_plan.get("market_reference_asset_ids", []),
                    "market_reference_scores": shot_reference_plan.get("market_reference_scores", []),
                    "market_reference_categories": shot_reference_plan.get("market_reference_categories", []),
                    "market_reference_decisions": shot_reference_plan.get("market_reference_decisions", []),
                    "market_reference_usage": shot_reference_plan.get("market_reference_usage", ""),
                },
            )
            if generation["success"]:
                current_path = copy_file(image_path, shot_image_dir / CURRENT_IMAGE_FILE)
                generated_paths.append(str(current_path))
                shot["generate_status"] = "reviewing"
                review = review_image(shot, current_path, CURRENT_IMAGE_FILE, style_bible)
                write_json(shot_image_dir / REVIEW_FILE, review)
                reviews.append(review)
                if review["review_status"] == "approved":
                    shot["generate_status"] = "approved"
                    shot["approved_version"] = CURRENT_IMAGE_FILE
                else:
                    shot["generate_status"] = "needs_regeneration"
            elif generation.get("adapter_status") == "requires_codex_image2_tool":
                shot["generate_status"] = "manual_review"
                review = _image2_waiting_review(shot, generation)
                write_json(shot_image_dir / REVIEW_FILE, review)
                reviews.append(review)
            else:
                shot["generate_status"] = "failed"
                review = review_image(shot, image_path, "版本1.png", style_bible)
                review["failure_reasons"].append(generation["message"])
                write_json(shot_image_dir / REVIEW_FILE, review)
                reviews.append(review)

        write_json(shot_path, shot)

    write_json(dirs["storyboard_dir"] / "分镜总表.json", storyboard)
    write_csv(dirs["storyboard_dir"] / "分镜总表.csv", storyboard_csv_rows(storyboard), storyboard_csv_fields())
    detailed_script_json_path = write_json(dirs["storyboard_dir"] / "详细脚本.json", _detailed_script_items(storyboard))
    detailed_script_md_path = write_text(dirs["storyboard_dir"] / "详细脚本.md", _detailed_script_markdown(storyboard))

    review_summary = summarize_reviews(reviews)
    approved_list = [review for review in reviews if review["review_status"] == "approved"]
    failed_queue = [review for review in reviews if review["review_status"] not in {"approved", "manual_review"}]
    write_json(dirs["review_dir"] / "通过清单.json", approved_list)
    write_json(dirs["review_dir"] / "失败队列.json", failed_queue)
    approved_manifest_path = write_json(dirs["export_dir"] / "通过清单汇总.json", approved_list)
    delivery_index_path = _write_delivery_index(project_dir, storyboard)

    manifest = _build_manifest(settings, created_at, project_dir, review_summary, len(generated_paths), archived_inputs)
    write_json(project_dir / PROJECT_MANIFEST_FILE, manifest)
    package_result = export_project_package(project_dir)

    return {
        "system_output_success": True,
        "system_output_project_dir": str(project_dir),
        "system_output_input_dir": str(dirs["input_dir"]),
        "system_output_script_brief": str(script_brief_path),
        "system_output_storyboard_json": str(dirs["storyboard_dir"] / "分镜总表.json"),
        "system_output_storyboard_csv": str(dirs["storyboard_dir"] / "分镜总表.csv"),
        "system_output_detailed_script_json": str(detailed_script_json_path),
        "system_output_detailed_script_md": str(detailed_script_md_path),
        "system_output_research_dir": str(dirs["research_dir"]),
        "system_output_market_signal_map": str(dirs["research_dir"] / "市场信号映射.json"),
        "system_output_visual_demand_matrix": str(dirs["research_dir"] / "视觉需求矩阵.json"),
        "system_output_shot_group_plan": str(dirs["research_dir"] / "镜头组规划.json"),
        "system_output_reference_image_plan": str(dirs["research_dir"] / "参考图规划.json"),
        "system_output_generated_image_count": len(generated_paths),
        "system_output_approved_image_count": review_summary["approved_count"],
        "system_output_failed_image_count": review_summary["failed_count"],
        "system_output_failed_queue": str(dirs["review_dir"] / "失败队列.json"),
        "system_output_approved_manifest": str(approved_manifest_path),
        "system_output_delivery_index": str(delivery_index_path),
        "system_output_storyboard_script_json": package_result["system_output_storyboard_script_json"],
        "system_output_prompt_count": len(prompt_paths),
        "system_output_manual_review_count": review_summary["manual_review_count"],
        "system_output_message": _run_message(settings, review_summary),
    }


def create_market_mining_project_dir(topic: str, created_at: datetime | None = None) -> Path:
    timestamp = created_at or datetime.now()
    output_root = ensure_dir(DEFAULT_OUTPUT_ROOT)
    topic_slug = slug_text(topic, max_length=48)
    existing = find_existing_project_dir(output_root, topic, created_at=timestamp)
    if existing:
        ensure_dir(existing / INPUT_DIR_NAME)
        ensure_dir(existing / RESEARCH_DIR_NAME)
        return existing

    base_name = f"{timestamp.strftime('%Y-%m-%d')}_素材调研_{topic_slug}"
    project_dir = output_root / base_name
    suffix = 2
    while project_dir.exists():
        project_dir = output_root / f"{base_name}_{suffix:02d}"
        suffix += 1
    ensure_dir(project_dir / INPUT_DIR_NAME)
    ensure_dir(project_dir / RESEARCH_DIR_NAME)
    write_json(
        project_dir / PROJECT_MANIFEST_FILE,
        {
            "schema_version": "ai-video-asset-project/v1",
            "project_type": "market_mining",
            "topic": topic,
            "created_at": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "output_root": str(output_root),
        },
    )
    return project_dir


def regenerate_shot(
    project_dir: str | Path,
    shot_id: str,
    failure_reasons: List[str] | None = None,
    provider: str = "codex_image2",
) -> Dict[str, Any]:
    project_path = Path(project_dir)
    shot_path = project_path / STORYBOARD_DIR_NAME / shot_json_file(shot_id)
    prompt_path = project_path / PROMPT_DIR_NAME / prompt_json_file(shot_id)
    if not shot_path.exists() or not prompt_path.exists():
        return {
            "system_output_success": False,
            "system_output_message": f"未找到 {shot_id} 的分镜或提示词文件。",
        }

    shot = read_json(shot_path)
    prompt_data = read_json(prompt_path)
    reasons = failure_reasons or ["人工要求重新生成"]
    regen_prompt = build_regeneration_prompt(shot, prompt_data, reasons)
    shot_image_dir = project_path / IMAGE_DIR_NAME / artifact_id(shot_id)
    new_version_path = next_image_version_path(shot_image_dir)
    generation = generate_image(
        regen_prompt["prompt"],
        new_version_path,
        {
            "provider": provider,
            "overwrite": True,
            "negative_prompt": regen_prompt.get("negative_prompt", ""),
        },
    )
    if generation.get("adapter_status") == "requires_codex_image2_tool":
        shot["generate_status"] = "manual_review"
        write_json(shot_path, shot)
        review = _image2_waiting_review(shot, generation)
        write_json(shot_image_dir / REVIEW_FILE, review)
        return {
            "system_output_success": True,
            "system_output_shot_id": shot_id,
            "system_output_status": "waiting_for_codex_image2",
            "system_output_image2_request": generation.get("request_path"),
            "system_output_message": "已创建重生 image2 请求，请调用 Codex image2 后用 register-image 登记结果。",
        }
    if not generation["success"]:
        return {
            "system_output_success": False,
            "system_output_message": generation.get("message", "生图失败"),
            "system_output_generation": generation,
        }

    old_current = shot.get("approved_version") or CURRENT_IMAGE_FILE
    copy_file(new_version_path, shot_image_dir / CURRENT_IMAGE_FILE)
    review = review_image(shot, shot_image_dir / CURRENT_IMAGE_FILE, CURRENT_IMAGE_FILE)
    write_json(shot_image_dir / REVIEW_FILE, review)

    shot["retry_count"] = int(shot.get("retry_count", 0)) + 1
    shot["generate_status"] = "approved" if review["review_status"] == "approved" else "needs_regeneration"
    shot["approved_version"] = CURRENT_IMAGE_FILE if review["review_status"] == "approved" else shot.get("approved_version")
    write_json(shot_path, shot)

    replace_record = {
        "shot_id": shot_id,
        "old_version": old_current,
        "new_version": new_version_path.name,
        "replace_reason": reasons,
        "replaced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current_version": CURRENT_IMAGE_FILE,
    }
    append_json_list(project_path / REVIEW_DIR_NAME / "替换记录.json", replace_record)
    append_json_list(
        project_path / REVIEW_DIR_NAME / "重试记录.json",
        {
            "shot_id": shot_id,
            "new_version": new_version_path.name,
            "retry_count": shot["retry_count"],
            "review_status": review["review_status"],
            "created_at": replace_record["replaced_at"],
        },
    )
    export_approved_manifest(project_path)
    _write_delivery_index(project_path, _load_storyboard(project_path))
    return {
        "system_output_success": True,
        "system_output_shot_id": shot_id,
        "system_output_new_version": str(new_version_path),
        "system_output_review": review,
    }


def replace_current_image(
    project_dir: str | Path,
    shot_id: str,
    image_version: str,
    reason: str | None = None,
) -> Dict[str, Any]:
    project_path = Path(project_dir)
    shot_image_dir = project_path / IMAGE_DIR_NAME / artifact_id(shot_id)
    source = shot_image_dir / image_version
    if not source.exists():
        return {
            "system_output_success": False,
            "system_output_message": f"Image version not found: {source}",
        }
    current = copy_file(source, shot_image_dir / CURRENT_IMAGE_FILE)
    append_json_list(
        project_path / REVIEW_DIR_NAME / "替换记录.json",
        {
            "shot_id": shot_id,
            "old_version": CURRENT_IMAGE_FILE,
            "new_version": image_version,
            "replace_reason": [reason or "人工替换当前图"],
            "replaced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_version": CURRENT_IMAGE_FILE,
        },
    )
    return {
        "system_output_success": True,
        "system_output_current_image": str(current),
    }


def prepare_image2_requests(
    project_dir: str | Path,
    only_ready: bool = True,
    provider: str = "codex_image2",
) -> Dict[str, Any]:
    """为已有项目生成 image2 请求队列，不重建分镜和 prompt。"""

    project_path = Path(project_dir)
    storyboard = _load_storyboard(project_path)
    reference_plan_path = project_path / RESEARCH_DIR_NAME / "参考图规划.json"
    reference_plan = read_json(reference_plan_path) if reference_plan_path.exists() else {"items": []}
    prepared = []
    blocked = []

    for shot in storyboard:
        shot_id = shot["shot_id"]
        prompt_path = project_path / PROMPT_DIR_NAME / prompt_json_file(shot_id)
        if not prompt_path.exists():
            blocked.append(
                {
                    "shot_id": shot_id,
                    "reason": "缺少生图提示词",
                    "prompt_path": relative_path(prompt_path, project_path),
                }
            )
            continue

        shot_reference_plan = reference_plan_for_shot(reference_plan, shot_id) or shot.get("reference_image_plan", {})
        shot_reference_dependency = shot.get("reference_dependency") or _reference_dependency_from_plan(shot_reference_plan)
        shot["reference_dependency"] = shot_reference_dependency
        reference_path = shot_reference_plan.get("reference_image_path") or ""
        reference_exists = not reference_path or (project_path / reference_path).exists() or Path(reference_path).exists()
        if only_ready and not reference_exists:
            blocked.append(
                {
                    "shot_id": shot_id,
                    "reason": "等待参考图文件可用",
                    "reference_shot_id": shot_reference_plan.get("reference_shot_id"),
                    "reference_image_path": reference_path,
                }
            )
            continue

        prompt_data = read_json(prompt_path)
        shot_image_dir = project_path / IMAGE_DIR_NAME / artifact_id(shot_id)
        image_path = shot_image_dir / "版本1.png"
        generation = generate_image(
            prompt_data["prompt"],
            image_path,
            {
                "provider": provider,
                "overwrite": True,
                "negative_prompt": prompt_data.get("negative_prompt", ""),
                "aspect_ratio": prompt_data.get("aspect_ratio", "16:9"),
                "reference_image_plan": shot_reference_plan,
                "reference_dependency": shot_reference_dependency,
                "reference_frame_ids": shot.get("reference_frame_ids", []),
                "reference_frame_paths": shot.get("reference_frame_paths", []),
                "reference_frame_usage_notes": shot.get("reference_frame_usage_notes", ""),
                "reference_image_path": reference_path,
                "market_reference_asset_paths": shot_reference_plan.get("market_reference_asset_paths", []),
                "market_reference_asset_ids": shot_reference_plan.get("market_reference_asset_ids", []),
                "market_reference_scores": shot_reference_plan.get("market_reference_scores", []),
                "market_reference_categories": shot_reference_plan.get("market_reference_categories", []),
                "market_reference_decisions": shot_reference_plan.get("market_reference_decisions", []),
                "market_reference_usage": shot_reference_plan.get("market_reference_usage", ""),
                "reference_usage_role": shot_reference_plan.get("reference_usage_role", ""),
                "reference_reuse_group": shot_reference_plan.get("reference_reuse_group", ""),
                "reference_reuse_budget": shot_reference_plan.get("reference_reuse_budget", 0),
            },
        )
        shot["generate_status"] = "manual_review"
        write_json(project_path / STORYBOARD_DIR_NAME / shot_json_file(shot_id), shot)
        review = _image2_waiting_review(shot, generation)
        write_json(shot_image_dir / REVIEW_FILE, review)
        prepared.append(
            {
                "shot_id": shot_id,
                "scene_group": shot.get("scene_group", ""),
                "reference_role": shot_reference_plan.get("reference_role", "standalone"),
                "reference_shot_id": shot_reference_plan.get("reference_shot_id"),
                "image2_request_path": relative_path(generation.get("request_path", ""), project_path),
                "target_current_path": relative_path(shot_image_dir / CURRENT_IMAGE_FILE, project_path),
                "prompt_path": relative_path(prompt_path, project_path),
            }
        )

    write_json(project_path / REVIEW_DIR_NAME / "生图队列.json", {"prepared": prepared, "blocked": blocked})
    for shot in storyboard:
        if any(item["shot_id"] == shot.get("shot_id") for item in prepared):
            shot["generate_status"] = "manual_review"
    write_json(project_path / STORYBOARD_DIR_NAME / "分镜总表.json", storyboard)
    write_csv(
        project_path / STORYBOARD_DIR_NAME / "分镜总表.csv",
        storyboard_csv_rows(storyboard),
        storyboard_csv_fields(),
    )
    _refresh_review_exports(project_path)

    return {
        "system_output_success": True,
        "system_output_project_dir": str(project_path),
        "system_output_generation_queue": str(project_path / REVIEW_DIR_NAME / "生图队列.json"),
        "system_output_prepared_count": len(prepared),
        "system_output_blocked_count": len(blocked),
        "system_output_message": "已生成当前可执行的 image2 请求队列；派生镜头会等锚点 当前图.png 登记后再准备。",
    }


def register_image_result(
    project_dir: str | Path,
    shot_id: str,
    source_image_path: str | Path,
    reason: str | None = None,
) -> Dict[str, Any]:
    """登记 Codex image2 生成后的本地图片。"""

    project_path = Path(project_dir)
    source = Path(source_image_path)
    shot_path = project_path / STORYBOARD_DIR_NAME / shot_json_file(shot_id)
    if not shot_path.exists():
        return {
            "system_output_success": False,
            "system_output_message": f"未找到分镜文件：{shot_path}",
        }
    if not source.exists():
        return {
            "system_output_success": False,
            "system_output_message": f"未找到 image2 输出图片：{source}",
        }

    shot = read_json(shot_path)
    shot_image_dir = project_path / IMAGE_DIR_NAME / artifact_id(shot_id)
    version_path = next_image_version_path(shot_image_dir)
    copy_file(source, version_path)
    current_path = copy_file(version_path, shot_image_dir / CURRENT_IMAGE_FILE)
    review = review_image(shot, current_path, CURRENT_IMAGE_FILE)
    write_json(shot_image_dir / REVIEW_FILE, review)

    shot["generate_status"] = "approved" if review["review_status"] == "approved" else "needs_regeneration"
    shot["approved_version"] = CURRENT_IMAGE_FILE if review["review_status"] == "approved" else shot.get("approved_version")
    write_json(shot_path, shot)
    _replace_shot_in_master(project_path, shot)

    append_json_list(
        project_path / REVIEW_DIR_NAME / "替换记录.json",
        {
            "shot_id": shot_id,
            "old_version": "image2_request",
            "new_version": version_path.name,
            "replace_reason": [reason or "登记 Codex image2 生成图片"],
            "replaced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_version": CURRENT_IMAGE_FILE,
        },
    )
    _refresh_review_exports(project_path)
    return {
        "system_output_success": True,
        "system_output_shot_id": shot_id,
        "system_output_image_version": version_path.name,
        "system_output_current_image": str(current_path),
        "system_output_review": review,
    }


def get_failed_queue(project_dir: str | Path) -> Dict[str, Any]:
    path = Path(project_dir) / REVIEW_DIR_NAME / "失败队列.json"
    queue = read_json(path) if path.exists() else []
    return {
        "system_output_success": True,
        "system_output_failed_count": len(queue),
        "system_output_failed_queue": queue,
    }


def export_approved_manifest(project_dir: str | Path) -> Dict[str, Any]:
    project_path = Path(project_dir)
    storyboard = _load_storyboard(project_path)
    approved_items = []
    for shot in storyboard:
        current = project_path / IMAGE_DIR_NAME / artifact_id(shot["shot_id"]) / CURRENT_IMAGE_FILE
        if shot.get("generate_status") == "approved" and current.exists():
            approved_items.append(
                {
                    "shot_id": shot["shot_id"],
                    "shot_title": shot["shot_title"],
                    "current_image": relative_path(current, project_path),
                    "prompt_path": relative_path(project_path / PROMPT_DIR_NAME / prompt_json_file(shot["shot_id"]), project_path),
                }
            )
    output_path = write_json(project_path / EXPORT_DIR_NAME / "通过清单汇总.json", approved_items)
    return {
        "system_output_success": True,
        "system_output_approved_count": len(approved_items),
        "system_output_approved_manifest": str(output_path),
    }


def export_project_package(project_dir: str | Path, output_json: str | Path | None = None) -> Dict[str, Any]:
    """Create a lightweight JSON script for Jiaozi import tests."""

    project_path = Path(project_dir)
    if not project_path.exists():
        return {
            "system_output_success": False,
            "system_output_project_dir": str(project_path),
            "system_output_storyboard_script_json": "",
            "system_output_packaged_file_count": 0,
            "system_output_message": "项目目录不存在，无法生成轻量分镜脚本包。",
        }

    export_dir = project_path / EXPORT_DIR_NAME
    export_dir.mkdir(parents=True, exist_ok=True)
    script_path = Path(output_json) if output_json else export_dir / "JiaoZistudio专用脚本.json"
    if script_path.suffix.lower() != ".json":
        script_path = script_path.with_suffix(".json")
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_payload = _build_storyboard_script_payload(project_path)
    write_json(script_path, script_payload)
    legacy_files = list(export_dir.glob("*_skill_package.zip")) + [
        export_dir / "storyboard_script.json",
        export_dir / "JiaoZistudio专用脚本.js",
    ]
    for legacy_file in legacy_files:
        try:
            legacy_file.unlink(missing_ok=True)
        except PermissionError:
            pass

    return {
        "system_output_success": True,
        "system_output_project_dir": str(project_path),
        "system_output_storyboard_script_json": str(script_path),
        "system_output_packaged_file_count": 1,
        "system_output_message": "JiaoZistudio 专用脚本已生成；请直接上传 .json 文件，不再生成压缩包。",
    }


def _read_json_or_default(path: Path, default: Any) -> Any:
    return read_json(path) if path.exists() else default


def _build_storyboard_script_payload(project_path: Path) -> Dict[str, Any]:
    prompt_dir = project_path / PROMPT_DIR_NAME
    prompts = []
    if prompt_dir.exists():
        for path in sorted(prompt_dir.glob("*_生图提示词.json")):
            prompt = _read_json_or_default(path, {})
            if isinstance(prompt, dict):
                prompt["__filename"] = path.name
                prompts.append(prompt)

    payload = {
        "format": "ai_video_asset_storyboard_script_v1",
        "project_manifest": _read_json_or_default(project_path / PROJECT_MANIFEST_FILE, {}),
        "style_bible": _read_json_or_default(project_path / STYLE_BIBLE_FILE, {}),
        "reference_image_plan": _read_json_or_default(project_path / RESEARCH_DIR_NAME / "参考图规划.json", {"items": []}),
        "storyboard_master": _read_json_or_default(project_path / STORYBOARD_DIR_NAME / "分镜总表.json", []),
        "detailed_script": _read_json_or_default(project_path / STORYBOARD_DIR_NAME / "详细脚本.json", []),
        "prompts": prompts,
    }
    return _sanitize_storyboard_script_payload(payload)


_LOCAL_REFERENCE_PATH_KEYS = {
    "project_dir",
    "reference_image_path",
    "planned_current_image_path",
    "target_current_path",
    "current_image_path",
}


_PROMPT_TEXT_KEYS = {
    "detailed_script",
    "prompt",
    "image_prompt",
    "final_prompt",
}


def _looks_like_local_path(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:[\\/]", value))


def _contains_local_path(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]:[\\/]", value))


def _strip_local_reference_text(value: str) -> str:
    text = value
    text = re.sub(
        r"本镜头需要参考\s+([A-Za-z0-9_-]+)\s+的\s+current\.png[:：]\s*[A-Za-z]:[^\n。]*current\.png。?",
        r"本镜头需要参考锚点镜头 \1 的画面一致性。",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"本镜头必须参考锚点\s+([A-Za-z0-9_-]+)\s+的\s+current\.png[:：]\s*[A-Za-z]:[^\n，。]*current\.png[，。]?",
        r"本镜头必须参考锚点 \1 的画面一致性，",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"参考锚点\s+([A-Za-z0-9_-]+)[:：]\s*[A-Za-z]:[^\n。]*current\.png。?",
        r"参考锚点 \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"[A-Za-z]:[\\/][^\n。]*current\.png", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[A-Za-z]:[\\/][^\n，。]*", "", text)
    text = re.sub(r"\s+。", "。", text)
    text = re.sub(r"[：:]\s*。", "。", text)
    text = re.sub(r"，\s*，", "，", text)
    return text.strip()


def _sanitize_storyboard_script_payload(value: Any) -> Any:
    if isinstance(value, dict):
        clean: Dict[str, Any] = {}
        for key, item in value.items():
            if key in _LOCAL_REFERENCE_PATH_KEYS and isinstance(item, str) and _looks_like_local_path(item):
                clean[key] = None
            elif key in _PROMPT_TEXT_KEYS and isinstance(item, str):
                clean[key] = _strip_local_reference_text(item)
            elif isinstance(item, str) and _contains_local_path(item):
                clean[key] = _strip_local_reference_text(item)
            else:
                clean[key] = _sanitize_storyboard_script_payload(item)
        return clean
    if isinstance(value, list):
        return [_sanitize_storyboard_script_payload(item) for item in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="AI 视频素材 MVP")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="创建新项目")
    run_parser.add_argument("--input-json", help="输入 JSON 配置路径")
    run_parser.add_argument("--output-root", help="输出根目录")
    run_parser.add_argument("--total-shots", type=int, help="覆盖分镜数量")
    run_parser.add_argument("--duration-seconds", type=int, help="可选：未指定分镜数量时按时长估算镜头数")
    run_parser.add_argument("--provider", choices=["codex_image2", "mock_placeholder"], help="生图 provider")
    run_parser.add_argument("--research-json", help="外部联网调研笔记 JSON 路径")
    run_parser.add_argument("--market-reference-assets", help="市场参考图 manifest 路径")
    run_parser.add_argument("--market-mining-summary", help="市场反挖摘要.json 路径")
    run_parser.add_argument("--no-images", action="store_true", help="只生成分镜和提示词，不创建生图任务")

    regen_parser = subparsers.add_parser("regenerate", help="重生一个镜头")
    regen_parser.add_argument("--project-dir", required=True)
    regen_parser.add_argument("--shot-id", required=True)
    regen_parser.add_argument("--reason", action="append", default=[])
    regen_parser.add_argument("--provider", choices=["codex_image2", "mock_placeholder"], default="codex_image2")

    register_parser = subparsers.add_parser("register-image", help="登记 Codex image2 输出图片")
    register_parser.add_argument("--project-dir", required=True)
    register_parser.add_argument("--shot-id", required=True)
    register_parser.add_argument("--source-image", required=True)
    register_parser.add_argument("--reason")

    prepare_parser = subparsers.add_parser("prepare-image2", help="为已有项目生成 image2 请求队列")
    prepare_parser.add_argument("--project-dir", required=True)
    prepare_parser.add_argument("--all", action="store_true", help="包含暂未满足锚点参考依赖的派生镜头")
    prepare_parser.add_argument("--provider", choices=["codex_image2", "mock_placeholder"], default="codex_image2")

    expand_parser = subparsers.add_parser("expand", help="扩展锚点图角度")
    expand_parser.add_argument("--project-dir", required=True)
    expand_parser.add_argument("--shot-id", required=True)
    expand_parser.add_argument("--count", type=int, default=6)
    expand_parser.add_argument("--provider", choices=["codex_image2", "mock_placeholder"], default="codex_image2")

    failed_parser = subparsers.add_parser("failed-queue", help="查看失败队列")
    failed_parser.add_argument("--project-dir", required=True)

    export_parser = subparsers.add_parser("export-approved", help="导出已通过素材清单")
    export_parser.add_argument("--project-dir", required=True)

    package_parser = subparsers.add_parser("export-package", help="生成 JiaoziStudio 专用 JSON 脚本")
    package_parser.add_argument("--project-dir", required=True)
    package_parser.add_argument("--output-json")

    jiaozi_storyboard_parser = subparsers.add_parser("export-jiaozi-storyboard", help="根据精选参考帧生成 JiaoziStudio 80 镜头分镜脚本")
    jiaozi_storyboard_parser.add_argument("--project-dir", required=True)
    jiaozi_storyboard_parser.add_argument("--shot-count", type=int, default=80)
    jiaozi_storyboard_parser.add_argument("--duration-per-shot", type=int, default=4)
    jiaozi_storyboard_parser.add_argument("--output-json")

    audit_jiaozi_parser = subparsers.add_parser("audit-jiaozi-storyboard", help="逐镜头审校 JiaoziStudio 分镜脚本的参考图、图片提示词和视频提示词")
    audit_jiaozi_parser.add_argument("--project-dir", required=True)
    audit_jiaozi_parser.add_argument("--script-json", help="可选：指定要审校的 JiaoziStudio 脚本 JSON")
    audit_jiaozi_parser.add_argument("--auto-fix", action="store_true", help="自动解绑明显冲突参考图并重写相关提示词")

    market_assets_parser = subparsers.add_parser("collect-market-assets", help="采集公开市场参考封面图")
    market_assets_parser.add_argument("--source-json", required=True, help="浏览器/调研导出的参考图 JSON")
    market_assets_parser.add_argument("--project-dir", help="项目目录，默认写入项目 00_调研/参考图")
    market_assets_parser.add_argument("--output-dir", help="自定义参考图输出目录")
    market_assets_parser.add_argument("--max-images", type=int, default=24)
    market_assets_parser.add_argument("--delay-seconds", type=float, default=0.35)

    video_assets_parser = subparsers.add_parser("collect-video-frames", help="采集公开预览视频参考帧并去水印")
    video_assets_parser.add_argument("--url", required=True, help="公开视频小样链接、光厂作品链接或本地视频路径")
    video_assets_parser.add_argument("--project-dir", help="项目目录，默认写入项目 00_调研/视频参考帧")
    video_assets_parser.add_argument("--output-dir", help="自定义视频参考帧输出目录")
    video_assets_parser.add_argument("--title", help="参考视频标题，用于目录命名")
    video_assets_parser.add_argument("--mode", choices=["keyframes", "sample", "every-frame"], default="keyframes")
    video_assets_parser.add_argument("--sample-every-seconds", type=float, default=1.5)
    video_assets_parser.add_argument("--scan-every-seconds", type=float, default=0.75)
    video_assets_parser.add_argument("--max-frames", type=int, default=48)
    video_assets_parser.add_argument("--max-frames-per-shot", type=int, default=3)
    video_assets_parser.add_argument("--scene-threshold", type=float, default=18.0)
    video_assets_parser.add_argument("--min-brightness", type=float, default=8.0)
    video_assets_parser.add_argument("--watermark-preset", default="光厂")
    video_assets_parser.add_argument("--watermark-rect", help="水印区域：x,y,width,height 或 x,y,width,height,base_width,base_height")
    video_assets_parser.add_argument("--watermark-backend", choices=["auto", "remwm", "opencv", "none"], default="auto")
    video_assets_parser.add_argument("--watermark-device", default="cpu", help="remwm device: cpu, cuda, etc.")
    video_assets_parser.add_argument("--keep-raw-frames", action="store_true")
    video_assets_parser.add_argument("--overwrite", action="store_true")
    video_assets_parser.add_argument("--ffmpeg-path")
    video_assets_parser.add_argument("--remwm-root")

    scene_assets_parser = subparsers.add_parser(
        "collect-scene-frames",
        help="TransNetV2 场景切分：每个场景取一张参考图并去水印",
    )
    scene_assets_parser.add_argument("--url", required=True, help="公开视频小样链接、光厂作品链接或本地视频路径")
    scene_assets_parser.add_argument("--project-dir", help="项目目录，默认写入项目 00_调研/视频参考帧")
    scene_assets_parser.add_argument("--output-dir", help="自定义视频参考帧输出目录")
    scene_assets_parser.add_argument("--title", help="参考视频标题，用于目录命名")
    scene_assets_parser.add_argument("--threshold", type=float, default=0.5, help="TransNetV2 检测阈值")
    scene_assets_parser.add_argument("--min-scene-duration", type=float, default=2.0, help="最小场景时长，秒")
    scene_assets_parser.add_argument("--max-scene-duration", type=float, default=0.0, help="最大场景时长，0 表示不限制")
    scene_assets_parser.add_argument("--max-scenes", type=int, default=0, help="每个视频最多保留的代表场景帧，0 表示不限制")
    scene_assets_parser.add_argument("--watermark-preset", default="光厂")
    scene_assets_parser.add_argument("--watermark-rect", help="水印区域：x,y,width,height 或 x,y,width,height,base_width,base_height")
    scene_assets_parser.add_argument("--watermark-backend", choices=["auto", "remwm", "opencv", "none"], default="auto")
    scene_assets_parser.add_argument("--watermark-device", default="cpu", help="remwm device: cpu, cuda, etc.")
    scene_assets_parser.add_argument("--keep-raw-frames", action="store_true")
    scene_assets_parser.add_argument("--overwrite", action="store_true")
    scene_assets_parser.add_argument("--ffmpeg-path")
    scene_assets_parser.add_argument("--remwm-root")
    scene_assets_parser.add_argument("--transnet-root", help="TransNetV2 根目录；也可用 AI_VIDEO_TRANSNET_ROOT")
    scene_assets_parser.add_argument("--transnet-python", help="含 TensorFlow 的 Python；也可用 AI_VIDEO_TRANSNET_PYTHON")
    scene_assets_parser.add_argument("--transnet-weights", help="TransNetV2 权重目录")

    high_value_frames_parser = subparsers.add_parser("prepare-high-value-video-frame-queue", help="按第二轮市场信号选择前 10 个可拆帧视频")
    high_value_frames_parser.add_argument("--project-dir", required=True)
    high_value_frames_parser.add_argument("--max-works", type=int, default=10)
    high_value_frames_parser.add_argument("--allow-unconfirmed-video-material", action="store_true", help="允许未确认属于光厂视频素材分类的作品进入队列")

    collect_high_value_frames_parser = subparsers.add_parser("collect-high-value-video-frames", help="采集高价值视频的场景参考帧，不足阈值时补采作品")
    collect_high_value_frames_parser.add_argument("--project-dir", required=True)
    collect_high_value_frames_parser.add_argument("--initial-works", type=int, default=10, help="先采集前 N 个高价值作品，默认 10")
    collect_high_value_frames_parser.add_argument("--min-total-frames", type=int, default=300, help="参考帧少于该数量时继续补采作品，默认 300")
    collect_high_value_frames_parser.add_argument("--max-works", type=int, default=30, help="最多采集作品数，默认 30")
    collect_high_value_frames_parser.add_argument("--workers", type=int, default=6, help="parallel video workers, default 6")
    collect_high_value_frames_parser.add_argument("--max-frames-per-source", type=int, default=0, help="每个源视频最多保留的代表帧，0 表示不限制")
    collect_high_value_frames_parser.add_argument("--scene-threshold", type=float, default=0.28, help="TransNetV2 高敏场景阈值，默认 0.28")
    collect_high_value_frames_parser.add_argument("--min-scene-duration", type=float, default=0.6, help="最小场景时长，秒，默认 0.6")
    collect_high_value_frames_parser.add_argument("--max-scene-duration", type=float, default=0.0, help="最大场景时长，0 表示不限制")
    collect_high_value_frames_parser.add_argument("--allow-unconfirmed-video-material", action="store_true", help="允许未确认属于光厂视频素材分类的作品进入队列")
    collect_high_value_frames_parser.add_argument("--watermark-preset", default="光厂")
    collect_high_value_frames_parser.add_argument("--watermark-rect")
    collect_high_value_frames_parser.add_argument("--watermark-backend", choices=["auto", "remwm", "opencv", "none"], default="auto")
    collect_high_value_frames_parser.add_argument("--watermark-device", default="cpu", help="remwm device: cpu, cuda, etc.")
    collect_high_value_frames_parser.add_argument("--overwrite", action="store_true")

    selected_frames_parser = subparsers.add_parser("build-selected-reference-frames", help="根据 Electron 勾选复制精选参考帧并生成 Codex 打标任务")
    selected_frames_parser.add_argument("--project-dir", required=True)
    selected_frames_parser.add_argument("--max-sheet-items", type=int, default=12)

    bind_frames_parser = subparsers.add_parser("bind-reference-frames", help="把精选参考帧绑定到每条分镜")
    bind_frames_parser.add_argument("--project-dir", required=True)
    bind_frames_parser.add_argument("--min-frames-per-shot", type=int, default=1)
    bind_frames_parser.add_argument("--max-reuse-per-frame", type=int, default=4)

    market_mining_parser = subparsers.add_parser("mine-market", help="光厂两轮关键词反挖和商业方向分析")
    market_mining_parser.add_argument("--project-dir", help="写入市场反挖数据的项目目录；不传则复用同日同主题目录，找不到才创建")
    market_mining_parser.add_argument("--topic", required=True, help="调研主题，例如：端午节 AI 视频素材")
    market_mining_parser.add_argument("--seed-keywords", help="3-5 个种子词，逗号或换行分隔；不填则自动生成")
    market_mining_parser.add_argument("--per-keyword", type=int, default=20, help="第一轮每个种子词最多抓取作品数")
    market_mining_parser.add_argument("--detail-top", type=int, default=10, help="第一轮每个种子词打开详情页的作品上限")
    market_mining_parser.add_argument("--second-pass-top", type=int, default=10, help="第二轮每个买家提示词取前 N 个作品")
    market_mining_parser.add_argument("--delay-seconds", type=float, default=0.35)
    market_mining_parser.add_argument("--no-live-fetch", action="store_true", help="不访问网络，仅用导入 JSON 或空数据验证流程")
    market_mining_parser.add_argument("--all-media", action="store_true", help="允许采集非视频素材；默认只采集光厂视频素材分类")
    market_mining_parser.add_argument("--first-pass-source-json", help="可选：浏览器导出的第一轮搜索/详情 JSON")
    market_mining_parser.add_argument("--second-pass-source-json", help="可选：浏览器导出的第二轮搜索/详情 JSON")

    fetch_work_parser = subparsers.add_parser("fetch-vjshi-work", help="Fetch one VJShi work detail page")
    fetch_work_parser.add_argument("--url", required=True)
    fetch_work_parser.add_argument("--output-json")
    fetch_work_parser.add_argument("--referer")
    fetch_work_parser.add_argument("--search-keyword", default="")

    fetch_works_parser = subparsers.add_parser("fetch-vjshi-works", help="Fetch multiple VJShi work detail pages")
    fetch_works_parser.add_argument("--urls", help="Comma or newline separated VJShi work URLs")
    fetch_works_parser.add_argument("--url-file", help="TXT, JSON, or JSONL file containing work URLs")
    fetch_works_parser.add_argument("--output-jsonl")
    fetch_works_parser.add_argument("--output-json")
    fetch_works_parser.add_argument("--referer")
    fetch_works_parser.add_argument("--search-keyword", default="")
    fetch_works_parser.add_argument("--delay-seconds", type=float, default=0.35)

    fetch_search_parser = subparsers.add_parser("fetch-vjshi-search-results", help="Fetch VJShi keyword/search result work URLs")
    fetch_search_parser.add_argument("--keyword", default="")
    fetch_search_parser.add_argument("--url", default="")
    fetch_search_parser.add_argument("--limit", type=int, default=80)
    fetch_search_parser.add_argument("--output-jsonl")
    fetch_search_parser.add_argument("--output-json")
    fetch_search_parser.add_argument("--all-media", action="store_true", help="Do not force video-material filter when building keyword URL")

    args = parser.parse_args()
    command = args.command or "run"

    if command == "run":
        user_input = _load_input_file(args.input_json) if args.input_json else {}
        if args.output_root:
            user_input["user_input_output_root_dir"] = args.output_root
        if args.total_shots:
            user_input["user_input_total_shots"] = args.total_shots
        if args.duration_seconds:
            user_input["user_input_duration_seconds"] = args.duration_seconds
        if args.provider:
            user_input["user_input_image_provider"] = args.provider
        if args.research_json:
            user_input["user_input_research_notes_path"] = args.research_json
        if args.market_reference_assets:
            user_input["user_input_market_reference_assets_path"] = args.market_reference_assets
        if args.market_mining_summary:
            user_input["user_input_market_mining_summary_path"] = args.market_mining_summary
        if args.no_images:
            user_input["user_input_generate_images"] = False
        if args.input_json:
            user_input["user_input_source_config_path"] = args.input_json
        result = run_skill(user_input)
    elif command == "regenerate":
        result = regenerate_shot(args.project_dir, args.shot_id, args.reason, provider=args.provider)
    elif command == "register-image":
        result = register_image_result(args.project_dir, args.shot_id, args.source_image, args.reason)
    elif command == "prepare-image2":
        result = prepare_image2_requests(args.project_dir, only_ready=not args.all, provider=args.provider)
    elif command == "expand":
        result = expand_variations(args.project_dir, args.shot_id, expand_count=args.count, provider=args.provider)
    elif command == "failed-queue":
        result = get_failed_queue(args.project_dir)
    elif command == "export-approved":
        result = export_approved_manifest(args.project_dir)
    elif command == "export-package":
        result = export_project_package(args.project_dir, args.output_json)
    elif command == "export-jiaozi-storyboard":
        result = export_jiaozi_storyboard_script(
            args.project_dir,
            shot_count=args.shot_count,
            output_json=args.output_json,
            duration_per_shot=args.duration_per_shot,
        )
    elif command == "audit-jiaozi-storyboard":
        result = audit_jiaozi_storyboard_script(
            args.project_dir,
            script_json=args.script_json,
            auto_fix=args.auto_fix,
        )
    elif command == "collect-market-assets":
        result = collect_market_reference_assets(
            args.source_json,
            project_dir=args.project_dir,
            output_dir=args.output_dir,
            max_images=args.max_images,
            delay_seconds=args.delay_seconds,
        )
    elif command == "collect-video-frames":
        result = collect_video_reference_frames(
            args.url,
            project_dir=args.project_dir,
            output_dir=args.output_dir,
            title=args.title,
            frame_mode=args.mode,
            sample_every_seconds=args.sample_every_seconds,
            scan_every_seconds=args.scan_every_seconds,
            max_frames=args.max_frames,
            max_frames_per_shot=args.max_frames_per_shot,
            scene_threshold=args.scene_threshold,
            min_brightness=args.min_brightness,
            watermark_preset=args.watermark_preset,
            watermark_rect=args.watermark_rect,
            watermark_backend=args.watermark_backend,
            keep_raw_frames=args.keep_raw_frames,
            overwrite=args.overwrite,
            ffmpeg_path=args.ffmpeg_path,
            remwm_root=args.remwm_root,
            watermark_device=args.watermark_device,
        )
    elif command == "collect-scene-frames":
        result = collect_scene_reference_frames(
            args.url,
            project_dir=args.project_dir,
            output_dir=args.output_dir,
            title=args.title,
            threshold=args.threshold,
            min_scene_duration=args.min_scene_duration,
            max_scene_duration=args.max_scene_duration,
            max_scenes=args.max_scenes,
            watermark_preset=args.watermark_preset,
            watermark_rect=args.watermark_rect,
            watermark_backend=args.watermark_backend,
            keep_raw_frames=args.keep_raw_frames,
            overwrite=args.overwrite,
            ffmpeg_path=args.ffmpeg_path,
            remwm_root=args.remwm_root,
            transnet_root=args.transnet_root,
            transnet_python=args.transnet_python,
            transnet_weights=args.transnet_weights,
            watermark_device=args.watermark_device,
        )
    elif command == "prepare-high-value-video-frame-queue":
        result = prepare_high_value_video_frame_queue(
            args.project_dir,
            max_works=args.max_works,
            strict_video_material=not args.allow_unconfirmed_video_material,
        )
    elif command == "collect-high-value-video-frames":
        result = collect_high_value_video_frames(
            args.project_dir,
            max_works=args.max_works,
            initial_works=args.initial_works,
            min_total_frames=args.min_total_frames,
            max_frames_per_source=args.max_frames_per_source,
            scene_threshold=args.scene_threshold,
            min_scene_duration=args.min_scene_duration,
            max_scene_duration=args.max_scene_duration,
            strict_video_material=not args.allow_unconfirmed_video_material,
            watermark_preset=args.watermark_preset,
            watermark_rect=args.watermark_rect,
            watermark_backend=args.watermark_backend,
            overwrite=args.overwrite,
            workers=args.workers,
            watermark_device=args.watermark_device,
        )
    elif command == "build-selected-reference-frames":
        result = build_selected_reference_frames(args.project_dir, max_sheet_items=args.max_sheet_items)
    elif command == "bind-reference-frames":
        result = build_reference_frame_binding_plan(
            args.project_dir,
            min_frames_per_shot=args.min_frames_per_shot,
            max_reuse_per_frame=args.max_reuse_per_frame,
        )
        result.update(_refresh_storyboard_outputs_after_reference_binding(args.project_dir))
    elif command == "mine-market":
        project_dir = args.project_dir or str(create_market_mining_project_dir(args.topic))
        result = mine_market(
            project_dir,
            args.topic,
            seed_keywords=args.seed_keywords,
            per_keyword=args.per_keyword,
            detail_top=args.detail_top,
            second_pass_top=args.second_pass_top,
            delay_seconds=args.delay_seconds,
            fetch_live=not args.no_live_fetch,
            first_pass_source_json=args.first_pass_source_json,
            second_pass_source_json=args.second_pass_source_json,
            video_material_only=not args.all_media,
        )
    elif command == "fetch-vjshi-work":
        result = fetch_vjshi_work_detail(
            args.url,
            output_json=args.output_json,
            referer=args.referer,
            search_keyword=args.search_keyword,
        )
    elif command == "fetch-vjshi-works":
        result = fetch_vjshi_work_details_batch(
            urls=args.urls,
            url_file=args.url_file,
            output_jsonl=args.output_jsonl,
            output_json=args.output_json,
            referer=args.referer,
            search_keyword=args.search_keyword,
            delay_seconds=args.delay_seconds,
        )
    elif command == "fetch-vjshi-search-results":
        result = fetch_vjshi_search_results(
            keyword=args.keyword,
            search_url=args.url,
            limit=args.limit,
            output_jsonl=args.output_jsonl,
            output_json=args.output_json,
            video_material_only=not args.all_media,
        )
    else:
        parser.error(f"未知命令：{command}")
        return

    print(json.dumps(result, ensure_ascii=True, indent=2))


def _load_input_file(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _load_research_notes(path: str | None) -> List[Dict[str, Any]]:
    if not path:
        return []
    research_path = Path(path)
    if not research_path.exists():
        return []
    return normalize_source_notes(json.loads(research_path.read_text(encoding="utf-8-sig")))


def _load_market_mining_notes(path: str | None) -> List[Dict[str, Any]]:
    if not path:
        return []
    mining_path = Path(path)
    if not mining_path.exists():
        return []
    data = json.loads(mining_path.read_text(encoding="utf-8-sig"))
    notes = data.get("source_notes", []) if isinstance(data, dict) else []
    normalized = []
    for index, note in enumerate(notes, start=1):
        if not isinstance(note, dict):
            continue
        normalized.append(
            {
                "source_id": note.get("source_id") or f"market_mining_{index:02d}",
                "source_type": note.get("source_type") or "vjshi_keyword_reverse_mining",
                "title": note.get("title") or "光厂关键词反挖方向",
                "url": note.get("url") or "https://www.vjshi.com/",
                "summary": note.get("summary") or "",
                "keywords": note.get("keywords", []),
                "related_keywords": note.get("related_keywords", []),
                "representative_visuals": note.get("representative_visuals", []),
                "high_purchase_examples": note.get("high_purchase_examples", []),
                "avoid_notes": note.get("avoid_notes", []),
                "purchase_count": note.get("purchase_count"),
            }
        )
    return normalized


def _load_market_mining_shot_group_plan(path: str | None) -> List[Dict[str, Any]]:
    if not path:
        return []
    mining_path = Path(path)
    if not mining_path.exists():
        return []
    data = json.loads(mining_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        return []
    plan = data.get("shot_group_plan_seed") or data.get("visual_demand_matrix_inputs") or []
    normalized = []
    for item in plan:
        if not isinstance(item, dict):
            continue
        group_name = clean_visual_phrase(item.get("group_name") or item.get("direction_name"))
        if not group_name:
            continue
        buyer_use_cases = clean_visual_terms(item.get("buyer_use_cases") or item.get("buyer_search_prompts", []))
        representative_scenes = clean_visual_terms(
            item.get("representative_scenes") or item.get("buyer_search_prompts", [])
        )
        core_elements = clean_visual_terms(item.get("core_elements") or item.get("keyword_basis", []))
        creative_angles = clean_visual_terms(item.get("creative_angles") or item.get("buyer_search_prompts", []))
        evidence_keywords = clean_visual_terms(item.get("evidence_keywords") or item.get("keyword_basis", []))
        normalized.append(
            {
                "group_name": group_name,
                "shot_count": max(1, int(item.get("shot_count") or item.get("recommended_shot_count") or 1)),
                "reason": item.get("reason") or item.get("prompt_guidance_for_image_generation") or "",
                "market_demand_score": item.get("market_demand_score") or item.get("market_signal_score"),
                "ai_generation_feasibility": item.get("ai_generation_feasibility"),
                "video_motion_potential": item.get("video_motion_potential"),
                "commercial_reuse_value": item.get("commercial_reuse_value"),
                "risk_score": item.get("risk_score"),
                "recommended_anchor_strategy": item.get("recommended_anchor_strategy", ""),
                "market_basis": item.get("market_basis", ""),
                "buyer_use_cases": buyer_use_cases,
                "representative_scenes": representative_scenes or [group_name],
                "core_elements": core_elements,
                "creative_angles": creative_angles,
                "avoid_patterns": item.get("avoid_patterns") or item.get("risk_notes", []),
                "evidence_keywords": evidence_keywords,
            }
        )
    return normalized


def _archive_project_inputs(settings: Dict[str, Any], dirs: Dict[str, Path]) -> Dict[str, str]:
    input_dir = dirs["input_dir"]
    archived: Dict[str, str] = {}
    effective_path = write_json(input_dir / "生效输入.json", settings)
    archived["effective_input_path"] = relative_path(effective_path, dirs["project_dir"])

    source_config_path = settings.get("user_input_source_config_path")
    if source_config_path:
        source_path = Path(source_config_path)
        if source_path.exists():
            archived_path = copy_file(source_path, input_dir / "原始输入.json")
            archived["source_input_path"] = relative_path(archived_path, dirs["project_dir"])

    research_notes_path = settings.get("user_input_research_notes_path")
    if research_notes_path:
        source_path = Path(research_notes_path)
        if source_path.exists():
            archived_path = copy_file(source_path, input_dir / "原始调研笔记.json")
            archived["source_research_notes_path"] = relative_path(archived_path, dirs["project_dir"])

    research_report_path = settings.get("user_input_research_report_path")
    if research_report_path:
        source_path = Path(research_report_path)
        if source_path.exists():
            archived_path = copy_file(source_path, input_dir / "原始调研报告.md")
            archived["source_research_report_path"] = relative_path(archived_path, dirs["project_dir"])

    market_reference_path = settings.get("user_input_market_reference_assets_path")
    if market_reference_path:
        source_path = Path(market_reference_path)
        if source_path.exists():
            archived_path = copy_file(source_path, input_dir / "原始市场参考图清单.json")
            archived["source_market_reference_assets_path"] = relative_path(archived_path, dirs["project_dir"])

    market_mining_path = settings.get("user_input_market_mining_summary_path")
    if market_mining_path:
        source_path = Path(market_mining_path)
        if source_path.exists():
            archived_path = copy_file(source_path, input_dir / "原始市场反挖摘要.json")
            archived["source_market_mining_summary_path"] = relative_path(archived_path, dirs["project_dir"])

    return archived


def _image2_waiting_review(shot: Dict[str, Any], generation: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "shot_id": shot["shot_id"],
        "image_version": "",
        "review_status": "manual_review",
        "stock_readiness_score": 0,
        "checks": {
            "file_exists": False,
            "waiting_for_codex_image2": True,
            "subject_match": False,
            "style_consistency": False,
            "copy_space_ok": False,
            "no_logo": False,
            "no_text": False,
            "no_watermark": False,
            "composition_ok": False,
            "lighting_ok": False,
            "machinery_ok": False,
            "people_anatomy_ok": False,
            "commercial_quality_ok": False,
        },
        "failure_reasons": [],
        "suggested_fix_prompt": "请读取 生图请求.json，调用 Codex 内置 image2 生图能力，再用 register-image 登记生成图片。",
        "image2_request_path": generation.get("request_path"),
    }


def _run_message(settings: Dict[str, Any], review_summary: Dict[str, Any]) -> str:
    provider = settings.get("user_input_image_provider", "codex_image2")
    if provider == "codex_image2":
        return "项目、中文分镜和 image2 生图请求已生成；请调用 Codex image2 并用 register-image 登记结果。"
    if provider == "mock_placeholder":
        return "项目已用 mock_placeholder 离线生成，占位图不代表真实素材质量。"
    return f"项目已生成，当前还有 {review_summary['manual_review_count']} 条需要人工处理。"


def _build_script_brief(
    settings: Dict[str, Any],
    style_bible: Dict[str, Any],
    research_outputs: Dict[str, Any],
    market_mining_summary_path: str | None,
) -> Dict[str, Any]:
    directions = _top_research_names(research_outputs.get("visual_demand_matrix", []), "direction_name")
    if not directions:
        directions = _top_research_names(research_outputs.get("shot_group_plan", []), "group_name")
    buyer_groups = _top_research_names(research_outputs.get("market_signal_map", []), "buyer_use_case")
    if not buyer_groups:
        buyer_groups = list(settings.get("user_input_target_usage", []))
    return {
        "schema_version": "script-brief/v1",
        "topic": settings["user_input_topic_title"],
        "aspect_ratio": settings.get("user_input_aspect_ratio", "16:9") or "16:9",
        "needs_voiceover": bool(settings.get("user_input_needs_voiceover", False)),
        "needs_subtitles": bool(settings.get("user_input_needs_subtitles", False)),
        "style_source": "derive_from_topic_and_market_research",
        "visual_style": settings.get("user_input_visual_style", ""),
        "style_bible_path": "../风格设定.json",
        "target_usage": list(settings.get("user_input_target_usage", [])),
        "target_buyer_groups": buyer_groups[:8],
        "commercial_direction_basis": directions[:10],
        "duration_seconds": int(settings.get("user_input_duration_seconds") or 0),
        "shot_count": int(settings["user_input_total_shots"]),
        "shot_count_policy": "user_total_shots wins; otherwise duration_seconds estimates one sellable shot about every 2.5 seconds; if neither is provided use project default.",
        "market_research_policy": "Use mined keyword and direction data to decide saleable themes, buyer intent, shot mix, style, and risk controls; do not ask the user to fill these manually.",
        "script_output_type": "silent stock-video storyboard; no voiceover, no subtitles, no readable copy by default",
        "creative_constraints": {
            "no_logo": bool(style_bible.get("commercial_rules", {}).get("no_logo", True)),
            "no_text": bool(style_bible.get("commercial_rules", {}).get("no_text", True)),
            "no_watermark": bool(style_bible.get("commercial_rules", {}).get("no_watermark", True)),
            "no_brand_name": bool(style_bible.get("commercial_rules", {}).get("no_brand_name", True)),
            "copy_space_required": bool(style_bible.get("commercial_rules", {}).get("copy_space_required", False)),
        },
        "research_inputs": {
            "market_mining_summary_path": str(market_mining_summary_path or ""),
            "visual_demand_matrix_path": "../00_调研/视觉需求矩阵.json",
            "shot_group_plan_path": "../00_调研/镜头组规划.json",
            "market_signal_map_path": "../00_调研/市场信号映射.json",
        },
    }


def _top_research_names(rows: Any, key: str) -> List[str]:
    output: List[str] = []
    if not isinstance(rows, list):
        return output
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get(key) or row.get("name") or row.get("title")
        if isinstance(value, list):
            output.extend(str(item) for item in value if item)
        elif value:
            output.append(str(value))
    seen: set[str] = set()
    unique = []
    for item in output:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _topic_brief(settings: Dict[str, Any], created_at: datetime) -> str:
    return f"""# {settings['user_input_topic_title']}

- 行业：{settings['user_input_industry_name']}
- 目标用途：{', '.join(settings['user_input_target_usage'])}
- 分镜数量：{settings['user_input_total_shots']}
- 画幅：{settings['user_input_aspect_ratio']}
- 视觉风格：{settings['user_input_visual_style']}
- 创建时间：{created_at.strftime('%Y-%m-%d %H:%M:%S')}
- 生图模式：{settings.get('user_input_image_provider', 'codex_image2')}
"""


def _build_manifest(
    settings: Dict[str, Any],
    created_at: datetime,
    project_dir: Path,
    review_summary: Dict[str, Any],
    generated_image_count: int,
    archived_inputs: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    project_id = f"asset_project_{created_at.strftime('%Y%m%d_%H%M%S')}"
    return {
        "project_id": project_id,
        "project_title": settings["user_input_topic_title"],
        "industry_name": settings["user_input_industry_name"],
        "total_shots": int(settings["user_input_total_shots"]),
        "aspect_ratio": settings["user_input_aspect_ratio"],
        "target_usage": settings["user_input_target_usage"],
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "completed" if review_summary["manual_review_count"] == 0 else "waiting_for_codex_image2",
        "style_bible_path": "./风格设定.json",
        "input_dir": "./00_输入",
        "effective_input_path": "./00_输入/生效输入.json",
        "script_brief_path": "./00_输入/脚本创作简报.json",
        "source_input_path": f"./{archived_inputs['source_input_path']}" if archived_inputs and archived_inputs.get("source_input_path") else "",
        "source_research_notes_path": f"./{archived_inputs['source_research_notes_path']}" if archived_inputs and archived_inputs.get("source_research_notes_path") else "",
        "source_research_report_path": f"./{archived_inputs['source_research_report_path']}" if archived_inputs and archived_inputs.get("source_research_report_path") else "",
        "source_market_reference_assets_path": f"./{archived_inputs['source_market_reference_assets_path']}" if archived_inputs and archived_inputs.get("source_market_reference_assets_path") else "",
        "source_market_mining_summary_path": f"./{archived_inputs['source_market_mining_summary_path']}" if archived_inputs and archived_inputs.get("source_market_mining_summary_path") else "",
        "storyboard_master_path": "./01_分镜/分镜总表.json",
        "detailed_script_json_path": "./01_分镜/详细脚本.json",
        "detailed_script_md_path": "./01_分镜/详细脚本.md",
        "research_dir": "./00_调研",
        "market_signal_map_path": "./00_调研/市场信号映射.json",
        "visual_demand_matrix_path": "./00_调研/视觉需求矩阵.json",
        "shot_group_plan_path": "./00_调研/镜头组规划.json",
        "image_root_dir": "./03_图片",
        "approved_count": review_summary["approved_count"],
        "failed_count": review_summary["failed_count"],
        "manual_review_count": review_summary["manual_review_count"],
        "generated_image_count": generated_image_count,
        "project_dir": str(project_dir),
    }


def _detailed_script_items(storyboard: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = []
    for shot in storyboard:
        reference_plan = shot.get("reference_image_plan", {})
        reference_dependency = shot.get("reference_dependency") or _reference_dependency_from_plan(reference_plan)
        items.append(
            {
                "shot_id": shot["shot_id"],
                "shot_title": shot["shot_title"],
                "scene_group": shot.get("scene_group", ""),
                "detailed_script": shot.get("detailed_script", ""),
                "market_basis": shot.get("research_basis", {}).get("market_basis", ""),
                "buyer_use_cases": shot.get("research_basis", {}).get("buyer_use_cases", []),
                "subject_main": shot.get("subject_main", ""),
                "subject_secondary": shot.get("subject_secondary", []),
                "action_description": shot.get("action_description", ""),
                "scene_context": shot.get("scene_context", ""),
                "shot_size": shot.get("shot_size", ""),
                "camera_angle": shot.get("camera_angle", ""),
                "camera_movement": shot.get("camera_movement", ""),
                "direct_use_composition": shot.get("direct_use_composition", shot.get("copy_space", "")),
                "video_motion_intent": shot.get("video_motion_intent", ""),
                "generation_risk_notes": shot.get("generation_risk_notes", []),
                "reference_dependency": reference_dependency,
                "reference_frame_ids": shot.get("reference_frame_ids", []),
                "reference_frame_paths": shot.get("reference_frame_paths", []),
                "reference_frame_usage_notes": shot.get("reference_frame_usage_notes", ""),
            }
        )
    return items


def _detailed_script_markdown(storyboard: List[Dict[str, Any]]) -> str:
    lines = [
        "# AI 视频素材详细脚本",
        "",
        "> 每条脚本面向直接生图和后续生视频，画面完整、信息饱满，可直接剪辑使用。",
        "",
    ]
    current_group = ""
    for shot in storyboard:
        group = shot.get("scene_group", "未分组")
        if group != current_group:
            current_group = group
            lines.extend(["", f"## {group}", ""])
        reference_plan = shot.get("reference_dependency") or shot.get("reference_image_plan", {})
        reference_role = reference_plan.get("role", reference_plan.get("reference_role", "standalone"))
        anchor_shot_id = reference_plan.get("anchor_shot_id", reference_plan.get("reference_shot_id"))
        market_refs = reference_plan.get("market_reference_asset_paths", [])
        lines.extend(
            [
                f"### {shot['shot_id']} {shot['shot_title']}",
                "",
                shot.get("detailed_script", ""),
                "",
                f"- 直接使用构图：{shot.get('direct_use_composition', shot.get('copy_space', ''))}",
                f"- 视频运动意图：{shot.get('video_motion_intent', '')}",
                f"- 参考依赖：{reference_role}"
                + (
                    f"，参考锚点 {anchor_shot_id}"
                    if anchor_shot_id
                    else ""
                ),
                f"- 精选参考帧：{', '.join(shot.get('reference_frame_ids', [])) if shot.get('reference_frame_ids') else '无'}",
                f"- 市场参考图：{', '.join(market_refs) if market_refs else '无'}",
                f"- 生成风险：{'；'.join(shot.get('generation_risk_notes', []))}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _attach_reference_dependencies_to_storyboard(
    storyboard: List[Dict[str, Any]],
    reference_plan: Dict[str, Any],
) -> None:
    plan_by_shot = {
        item.get("shot_id"): item
        for item in reference_plan.get("items", [])
        if item.get("shot_id")
    }
    for shot in storyboard:
        item = plan_by_shot.get(shot.get("shot_id"), {})
        dependency = _reference_dependency_from_plan(item)
        shot["reference_dependency"] = dependency
        dependency_text = _reference_dependency_text(dependency)
        if dependency_text and dependency_text not in shot.get("detailed_script", ""):
            shot["detailed_script"] = f"{shot.get('detailed_script', '')}\n参考依赖规划：{dependency_text}"


def _reference_dependency_from_plan(reference_plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role": reference_plan.get("role", reference_plan.get("reference_role", "standalone")),
        "anchor_shot_id": reference_plan.get("anchor_shot_id", reference_plan.get("reference_shot_id")),
        "reference_image_path": reference_plan.get("reference_image_path"),
        "market_reference_asset_ids": reference_plan.get("market_reference_asset_ids", []),
        "market_reference_asset_paths": reference_plan.get("market_reference_asset_paths", []),
        "market_reference_scores": reference_plan.get("market_reference_scores", []),
        "market_reference_categories": reference_plan.get("market_reference_categories", []),
        "market_reference_decisions": reference_plan.get("market_reference_decisions", []),
        "reference_reason": reference_plan.get("reference_reason", ""),
        "market_reference_usage": reference_plan.get("market_reference_usage", ""),
        "reference_frame_ids": reference_plan.get("reference_frame_ids", []),
        "reference_frame_paths": reference_plan.get("reference_frame_paths", []),
        "reference_frame_usage": reference_plan.get("reference_frame_usage", ""),
        "reference_usage_role": reference_plan.get("reference_usage_role", ""),
        "reference_reuse_group": reference_plan.get("reference_reuse_group", ""),
        "reference_reuse_budget": reference_plan.get("reference_reuse_budget", 0),
    }


def _reference_dependency_text(dependency: Dict[str, Any]) -> str:
    role = dependency.get("role", "standalone")
    parts = []
    if role == "anchor":
        parts.append("旧项目锚点镜头；新素材包默认不再自动生成锚点派生链。")
    elif role == "derived_view":
        parts.append(
            f"旧项目派生镜头，参考锚点 {dependency.get('anchor_shot_id')}；新素材包默认使用 standalone 独立镜头复用参考素材。"
        )
    else:
        parts.append("本镜头独立生成，按 style_bible 保持整套素材风格一致；参考素材只作为可选构图、光线、动作或材质依据。")
    market_paths = dependency.get("market_reference_asset_paths") or []
    if market_paths:
        parts.append(
            "可参考市场图 "
            + "、".join(str(path) for path in market_paths[:2])
            + " 的题材、景别、构图和商业质感，但必须原创，不能复刻原图、Logo、水印、品牌包装或可识别版权画面。"
        )
    frame_ids = dependency.get("reference_frame_ids") or []
    frame_paths = dependency.get("reference_frame_paths") or []
    if frame_ids:
        parts.append(
            "精选参考帧 "
            + "、".join(str(frame_id) for frame_id in frame_ids[:3])
            + " 用于题材、构图、镜头语言、光线、色彩和商业质感参考；原文件 "
            + "、".join(str(path) for path in frame_paths[:3])
            + "；允许相似参考，但最终生成图与来源帧相似度目标不得超过 90%。"
        )
    return "".join(parts)


def _refresh_storyboard_outputs_after_reference_binding(project_dir: str | Path) -> Dict[str, Any]:
    project_path = Path(project_dir)
    storyboard = _load_storyboard(project_path)
    style_bible = _read_json_or_default(project_path / "风格设定.json", {})
    manifest = _read_json_or_default(project_path / "项目清单.json", {})
    aspect_ratio = manifest.get("aspect_ratio") or "16:9"
    prompt_paths = []
    for shot in storyboard:
        shot_id = shot.get("shot_id")
        if not shot_id:
            continue
        prompt_data = build_image_prompt(shot, style_bible, aspect_ratio)
        prompt_path = project_path / PROMPT_DIR_NAME / prompt_json_file(shot_id)
        write_json(prompt_path, prompt_data)
        write_json(project_path / STORYBOARD_DIR_NAME / shot_json_file(shot_id), shot)
        prompt_paths.append(str(prompt_path))
    write_json(project_path / STORYBOARD_DIR_NAME / "分镜总表.json", storyboard)
    write_csv(project_path / STORYBOARD_DIR_NAME / "分镜总表.csv", storyboard_csv_rows(storyboard), storyboard_csv_fields())
    write_json(project_path / STORYBOARD_DIR_NAME / "详细脚本.json", _detailed_script_items(storyboard))
    write_text(project_path / STORYBOARD_DIR_NAME / "详细脚本.md", _detailed_script_markdown(storyboard))
    return {
        "system_output_refreshed_prompt_count": len(prompt_paths),
        "system_output_refreshed_prompts": prompt_paths,
    }


def _load_storyboard(project_path: Path) -> List[Dict[str, Any]]:
    master_path = project_path / STORYBOARD_DIR_NAME / "分镜总表.json"
    if master_path.exists():
        return read_json(master_path)
    shots = []
    for shot_file in sorted((project_path / STORYBOARD_DIR_NAME).glob("镜头_*.json")):
        shots.append(read_json(shot_file))
    return shots


def _replace_shot_in_master(project_path: Path, updated_shot: Dict[str, Any]) -> None:
    storyboard = _load_storyboard(project_path)
    replaced = False
    for index, shot in enumerate(storyboard):
        if shot.get("shot_id") == updated_shot["shot_id"]:
            storyboard[index] = updated_shot
            replaced = True
            break
    if not replaced:
        storyboard.append(updated_shot)
    write_json(project_path / STORYBOARD_DIR_NAME / "分镜总表.json", storyboard)
    write_csv(
        project_path / STORYBOARD_DIR_NAME / "分镜总表.csv",
        storyboard_csv_rows(storyboard),
        storyboard_csv_fields(),
    )


def _refresh_review_exports(project_path: Path) -> None:
    storyboard = _load_storyboard(project_path)
    reviews = []
    for shot in storyboard:
        review_path = project_path / IMAGE_DIR_NAME / artifact_id(shot["shot_id"]) / REVIEW_FILE
        if review_path.exists():
            reviews.append(read_json(review_path))

    approved_list = [review for review in reviews if review.get("review_status") == "approved"]
    failed_queue = [
        review
        for review in reviews
        if review.get("review_status") not in {"approved", "manual_review"}
    ]
    write_json(project_path / REVIEW_DIR_NAME / "通过清单.json", approved_list)
    write_json(project_path / REVIEW_DIR_NAME / "失败队列.json", failed_queue)
    write_json(project_path / EXPORT_DIR_NAME / "通过清单汇总.json", approved_list)
    _write_delivery_index(project_path, storyboard)


def _write_delivery_index(project_dir: Path, storyboard: List[Dict[str, Any]]) -> Path:
    rows = []
    for shot in storyboard:
        shot_id = shot["shot_id"]
        shot_artifact_id = artifact_id(shot_id)
        current_image = project_dir / IMAGE_DIR_NAME / shot_artifact_id / CURRENT_IMAGE_FILE
        rows.append(
            {
                "shot_id": shot_id,
                "shot_title": shot["shot_title"],
                "scene_group": shot.get("scene_group", ""),
                "current_image": relative_path(current_image, project_dir) if current_image.exists() else "",
                "prompt_path": f"{PROMPT_DIR_NAME}/{prompt_json_file(shot_id)}",
                "review_path": f"{IMAGE_DIR_NAME}/{shot_artifact_id}/{REVIEW_FILE}",
                "status": shot.get("generate_status", ""),
                "direct_use_composition": shot.get("direct_use_composition", shot.get("copy_space", "")),
            }
        )
    return write_csv(
        project_dir / EXPORT_DIR_NAME / "交付索引.csv",
        rows,
        [
            "shot_id",
            "shot_title",
            "scene_group",
            "current_image",
            "prompt_path",
            "review_path",
            "status",
            "direct_use_composition",
        ],
    )


if __name__ == "__main__":
    main()
