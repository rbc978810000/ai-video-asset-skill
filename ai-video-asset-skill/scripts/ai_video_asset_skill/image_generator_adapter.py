"""生图适配层。

正式生产路径使用 codex_image2：脚本写出 生图请求.json，由执行 Skill 的
Codex 调用内置 image2 生图能力后，再用 register-image 登记结果。
mock_placeholder 只用于离线测试目录、版本和清单逻辑。
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Any, Dict

from .file_manager import CURRENT_IMAGE_FILE, ensure_dir, write_json


MOCK_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def generate_image(prompt: str, output_path: str | Path, options: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """根据 provider 创建生图结果或待调用请求，并返回 JSON 对象。"""

    options = options or {}
    provider = options.get("provider", "codex_image2")
    output = Path(output_path)
    ensure_dir(output.parent)

    if provider in {"codex_image2", "image2"}:
        request_path = output.parent / "生图请求.json"
        request = {
            "provider": "codex_image2",
            "model": "image2",
            "prompt": prompt,
            "negative_prompt": options.get("negative_prompt", ""),
            "aspect_ratio": options.get("aspect_ratio", "16:9"),
            "target_output_path": str(output),
            "target_current_path": str(output.parent / CURRENT_IMAGE_FILE),
            "reference_image_plan": options.get("reference_image_plan", {}),
            "reference_dependency": options.get("reference_dependency", {}),
            "reference_frame_ids": options.get("reference_frame_ids", []),
            "reference_frame_paths": options.get("reference_frame_paths", []),
            "reference_frame_usage_notes": options.get("reference_frame_usage_notes", ""),
            "reference_image_path": options.get("reference_image_path", ""),
            "market_reference_asset_paths": options.get("market_reference_asset_paths", []),
            "market_reference_asset_ids": options.get("market_reference_asset_ids", []),
            "market_reference_scores": options.get("market_reference_scores", []),
            "market_reference_categories": options.get("market_reference_categories", []),
            "market_reference_decisions": options.get("market_reference_decisions", []),
            "market_reference_usage": options.get("market_reference_usage", ""),
            "prompt_hash": _prompt_hash(prompt),
            "codex_action": "请使用 Codex 内置 image2 生图能力生成图片，然后用 register-image 登记结果。",
        }
        write_json(request_path, request)
        return {
            "success": False,
            "provider": "codex_image2",
            "image_path": str(output),
            "request_path": str(request_path),
            "adapter_status": "requires_codex_image2_tool",
            "message": "已创建 生图请求.json，等待 Codex 调用内置 image2 并登记图片。",
            "prompt_hash": request["prompt_hash"],
            "cost_units": "由 Codex image2 实际调用决定",
        }

    if provider != "mock_placeholder":
        return {
            "success": False,
            "provider": provider,
            "image_path": str(output),
            "adapter_status": "provider_not_configured",
            "message": "未配置该 provider。正式路径使用 codex_image2，离线测试使用 mock_placeholder。",
        }

    overwrite = bool(options.get("overwrite", True))
    if output.exists() and not overwrite:
        return {
            "success": True,
            "provider": "mock_placeholder",
            "image_path": str(output),
            "adapter_status": "existing_file_reused",
            "prompt_hash": _prompt_hash(prompt),
            "cost_units": 0,
        }

    output.write_bytes(base64.b64decode(MOCK_PNG_BASE64))
    return {
        "success": True,
        "provider": "mock_placeholder",
        "image_path": str(output),
        "adapter_status": "mock_placeholder_generated",
        "prompt_hash": _prompt_hash(prompt),
        "cost_units": 0,
    }


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
