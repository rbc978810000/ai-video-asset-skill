"""Anchor-image variation expansion for continuous shot groups."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .file_manager import CURRENT_IMAGE_FILE, IMAGE_DIR_NAME, VARIATION_DIR_NAME, artifact_id, copy_file, ensure_dir, write_json
from .image_generator_adapter import generate_image
from .image_prompt_builder import build_variation_prompt


DEFAULT_EXPAND_TYPES = [
    "全景",
    "中景",
    "特写",
    "侧面角度",
    "俯拍角度",
    "低机位角度",
]


def expand_variations(
    project_dir: str | Path,
    anchor_shot_id: str,
    anchor_image_path: str | Path | None = None,
    expand_count: int = 6,
    expand_types: List[str] | None = None,
    provider: str = "codex_image2",
) -> Dict[str, Any]:
    project_path = Path(project_dir)
    anchor_path = (
        Path(anchor_image_path)
        if anchor_image_path
        else project_path / IMAGE_DIR_NAME / artifact_id(anchor_shot_id) / CURRENT_IMAGE_FILE
    )
    variation_dir = ensure_dir(project_path / VARIATION_DIR_NAME / artifact_id(anchor_shot_id))
    copied_anchor = variation_dir / "锚点图.png"
    if not anchor_path.exists():
        return {
            "system_output_success": False,
            "system_output_message": f"Anchor image not found: {anchor_path}",
            "system_output_variation_dir": str(variation_dir),
        }
    copy_file(anchor_path, copied_anchor)

    selected_types = (expand_types or DEFAULT_EXPAND_TYPES)[:expand_count]
    variations: List[Dict[str, Any]] = []
    for index, expand_type in enumerate(selected_types, start=1):
        filename = _variation_filename(expand_type, index)
        output_path = variation_dir / filename
        prompt_data = build_variation_prompt(
            anchor_shot_id=anchor_shot_id,
            target_shot_size=expand_type,
            target_camera_angle=_camera_angle_for(expand_type),
            target_composition=f"{expand_type} composition with clean copy space",
            target_action_variation="保持同一场景，仅微调人物或设备姿态",
        )
        generation = generate_image(
            prompt_data["prompt"],
            output_path,
            {
                "provider": provider,
                "reference_image_plan": {
                    "reference_role": "variation_from_anchor",
                    "reference_shot_id": anchor_shot_id,
                    "reference_image_path": str(copied_anchor),
                    "reference_reason": "扩展镜头必须参考锚点图，保持同一场景、人物、设备、光线和色彩一致性。",
                },
                "reference_image_path": str(copied_anchor),
            },
        )
        variations.append(
            {
                "variation_type": expand_type,
                "image_path": str(output_path),
                "prompt": prompt_data,
                "generation": generation,
            }
        )

    manifest = {
        "anchor_shot_id": anchor_shot_id,
        "anchor_image_path": str(copied_anchor),
        "variation_count": len(variations),
        "variations": variations,
    }
    manifest_path = write_json(variation_dir / "扩展角度清单.json", manifest)
    return {
        "system_output_success": True,
        "system_output_variation_dir": str(variation_dir),
        "system_output_manifest_path": str(manifest_path),
        "system_output_generated_variation_count": len(variations),
    }


def _variation_filename(expand_type: str, index: int) -> str:
    filename_map = {
        "全景": "全景",
        "中景": "中景",
        "特写": "特写",
        "侧面角度": "侧面角度",
        "俯拍角度": "俯拍角度",
        "低机位角度": "低机位角度",
    }
    slug = filename_map.get(expand_type, f"扩展角度_{index:02d}")
    return f"{slug}_版本{index}.png"


def _camera_angle_for(expand_type: str) -> str:
    if "俯拍" in expand_type:
        return "俯拍机位"
    if "低机位" in expand_type:
        return "低机位"
    if "侧面" in expand_type:
        return "侧面机位"
    if "特写" in expand_type:
        return "近距离特写机位"
    return "宽幅建立镜头机位"
