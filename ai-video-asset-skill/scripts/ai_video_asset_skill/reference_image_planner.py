"""Plan optional standalone image references for storyboard shots."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .file_manager import CURRENT_IMAGE_FILE, IMAGE_DIR_NAME, RESEARCH_DIR_NAME, artifact_id, read_json


def build_reference_image_plan(storyboard: List[Dict[str, Any]], project_dir: str | Path) -> Dict[str, Any]:
    """Write default standalone reference metadata for every shot."""

    project_path = Path(project_dir)
    plan_items: List[Dict[str, Any]] = []

    for shot in storyboard:
        shot_id = shot["shot_id"]
        group_name = shot.get("scene_group") or "默认场景组"
        current_path = project_path / IMAGE_DIR_NAME / artifact_id(shot_id) / CURRENT_IMAGE_FILE
        item = {
            "shot_id": shot_id,
            "scene_group": group_name,
            "reference_role": "standalone",
            "reference_shot_id": None,
            "reference_image_path": None,
            "planned_current_image_path": str(current_path),
            "reference_reason": "本镜头独立生成；如后续绑定市场参考图或精选参考帧，只作为构图、光线、动作或材质参考，不产生锚点派生依赖。",
            "consistency_requirements": [
                "保持整套素材的全局风格、色调和商业质感一致。",
                "同场景多机位可复用同一参考素材，但必须改变景别、机位、动作阶段、前景遮挡、运镜或留白方向。",
                "不得因为同组镜头而自动引用上一张生成图。",
            ],
        }
        shot["reference_image_plan"] = item
        plan_items.append(item)

    return {
        "strategy": "每条分镜默认 standalone；参考图是可选素材池，允许高价值参考图在 1-3 个独立镜头中复用，但不生成 anchor/derived 派生关系。",
        "items": plan_items,
    }


def reference_plan_for_shot(reference_plan: Dict[str, Any], shot_id: str) -> Dict[str, Any] | None:
    for item in reference_plan.get("items", []):
        if item.get("shot_id") == shot_id:
            return item
    return None


def attach_market_reference_assets(
    reference_plan: Dict[str, Any],
    storyboard: List[Dict[str, Any]],
    project_dir: str | Path,
    manifest_path: str | Path | None = None,
    max_assets_per_shot: int = 2,
) -> Dict[str, Any]:
    """Attach locally collected market reference images to matching shots."""

    project_path = Path(project_dir)
    manifest = Path(manifest_path) if manifest_path else project_path / RESEARCH_DIR_NAME / "市场参考图清单.json"
    if not manifest.exists():
        return reference_plan

    try:
        assets = read_json(manifest).get("assets", [])
    except Exception:
        return reference_plan
    if not assets:
        return reference_plan

    asset_project_path = manifest.parent.parent if manifest.parent.name == RESEARCH_DIR_NAME else project_path
    shot_by_id = {shot["shot_id"]: shot for shot in storyboard}
    for item in reference_plan.get("items", []):
        shot = shot_by_id.get(item.get("shot_id"))
        if not shot:
            continue
        selected = _select_assets_for_shot(shot, assets, project_path, asset_project_path, max_assets_per_shot)
        if not selected:
            continue
        item["market_reference_asset_ids"] = [asset["asset_id"] for asset in selected]
        item["market_reference_asset_paths"] = [asset["resolved_local_path"] for asset in selected]
        item["market_reference_scores"] = [asset.get("reference_score") for asset in selected]
        item["market_reference_categories"] = [asset.get("category_tags", []) for asset in selected]
        item["market_reference_decisions"] = [asset.get("reference_decision", "") for asset in selected]
        item["market_reference_usage"] = (
            "高分市场参考图可用于 image2 图生图方向参考，仅借鉴题材、构图、色彩和画面模块；"
            "正式生图必须原创，不得复刻原图、Logo、水印、真实品牌包装或可识别版权画面。"
        )
        shot["reference_image_plan"] = item
    return reference_plan


def _select_assets_for_shot(
    shot: Dict[str, Any],
    assets: List[Dict[str, Any]],
    project_path: Path,
    asset_project_path: Path,
    max_assets: int,
) -> List[Dict[str, Any]]:
    shot_text = " ".join(
        str(value)
        for value in [
            shot.get("shot_title", ""),
            shot.get("scene_goal", ""),
            shot.get("scene_group", ""),
            shot.get("subject_main", ""),
            " ".join(str(item) for item in shot.get("subject_secondary", [])),
            shot.get("action_description", ""),
            shot.get("scene_context", ""),
        ]
    )
    scored: List[tuple[float, int, Dict[str, Any]]] = []
    for asset in assets:
        if asset.get("can_be_image_reference") is False:
            continue
        tokens = [asset.get("title", "")]
        tokens.extend(str(item) for item in asset.get("keywords", []))
        tokens.extend(str(item) for item in asset.get("visual_tags", []))
        tokens.extend(str(item) for item in asset.get("category_tags", []))
        score = sum(1 for token in tokens if token and token in shot_text)
        if score <= 0:
            continue
        local_path = Path(asset.get("local_path", ""))
        if local_path.is_absolute():
            resolved = local_path
        elif (project_path / local_path).exists():
            resolved = project_path / local_path
        else:
            resolved = asset_project_path / local_path
        if not resolved.exists():
            continue
        enriched = dict(asset)
        enriched["resolved_local_path"] = str(resolved.resolve())
        reference_score = float(enriched.get("reference_score") or 60)
        combined_score = score * 10 + reference_score
        scored.append((combined_score, score, enriched))

    scored.sort(key=lambda item: (-item[0], -int(item[2].get("purchase_count") or 0), item[2].get("asset_id", "")))
    return [asset for _, _, asset in scored[:max_assets]]
