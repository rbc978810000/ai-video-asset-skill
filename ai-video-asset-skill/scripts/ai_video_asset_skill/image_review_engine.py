"""生成图片素材的基础质检模块。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def review_image(
    shot: Dict[str, Any],
    image_path: str | Path,
    image_version: str,
    style_bible: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return a uniform review JSON object.

    MVP 只能验证文件系统和字段级检查。离线占位图会通过视觉项，
    以便验证完整目录和清单流程。
    """

    path = Path(image_path)
    file_exists = path.exists() and path.is_file()
    failure_reasons: List[str] = []
    if not file_exists:
        failure_reasons.append("image file does not exist")

    checks = {
        "file_exists": file_exists,
        "subject_match": file_exists,
        "style_consistency": file_exists,
        "copy_space_ok": file_exists,
        "no_logo": file_exists,
        "no_text": file_exists,
        "no_watermark": file_exists,
        "composition_ok": file_exists,
        "lighting_ok": file_exists,
        "machinery_ok": file_exists,
        "people_anatomy_ok": file_exists,
        "commercial_quality_ok": file_exists,
    }
    approved = all(checks.values())
    return {
        "shot_id": shot["shot_id"],
        "image_version": image_version,
        "review_status": "approved" if approved else "needs_regeneration",
        "stock_readiness_score": 92 if approved else 0,
        "checks": checks,
        "failure_reasons": failure_reasons,
        "suggested_fix_prompt": "" if approved else "请重新生成，确保文件成功写入并保留商业素材约束。",
    }


def summarize_reviews(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    approved = [review for review in reviews if review.get("review_status") == "approved"]
    manual_review = [review for review in reviews if review.get("review_status") == "manual_review"]
    failed = [
        review
        for review in reviews
        if review.get("review_status") not in {"approved", "manual_review"}
    ]
    return {
        "approved_count": len(approved),
        "failed_count": len(failed),
        "manual_review_count": len(manual_review),
    }
