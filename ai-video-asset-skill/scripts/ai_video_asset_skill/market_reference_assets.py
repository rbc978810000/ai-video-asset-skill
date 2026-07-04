"""Collect public market reference cover images into a project research folder."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .file_manager import (
    REFERENCE_ASSETS_DIR_NAME,
    RESEARCH_DIR_NAME,
    ensure_dir,
    relative_path,
    slug_text,
    write_json,
    write_text,
)
from .research_planner import (
    ALLOWED_RESEARCH_SOURCES,
    BLOCKED_RESEARCH_DOMAINS,
    _domain_from_url,
    _domain_matches,
)


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
)

IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def collect_market_reference_assets(
    source_json_path: str | Path,
    project_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    max_images: int = 24,
    delay_seconds: float = 0.35,
) -> Dict[str, Any]:
    """Download public cover/detail preview images listed in a browser export JSON."""

    source_path = Path(source_json_path)
    data = json.loads(source_path.read_text(encoding="utf-8-sig"))
    resolved_project = Path(project_dir) if project_dir else None
    if output_dir:
        asset_dir = Path(output_dir)
    elif resolved_project:
        asset_dir = resolved_project / RESEARCH_DIR_NAME / REFERENCE_ASSETS_DIR_NAME
    else:
        asset_dir = source_path.parent / REFERENCE_ASSETS_DIR_NAME
    ensure_dir(asset_dir)

    candidates = _collect_candidates(data)
    manifest_assets: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()

    for candidate in candidates:
        if len(manifest_assets) >= max_images:
            break
        image_url = candidate["image_url"]
        normalized_url = _normalize_url_for_dedupe(image_url)
        if normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)
        if not _is_allowed_market_source(candidate):
            continue
        if not _looks_like_reference_image(candidate):
            continue

        try:
            body, content_type = _download_image(image_url, candidate.get("source_page_url") or candidate.get("page_url"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            failed.append({**candidate, "error": str(exc)})
            continue

        sha256 = hashlib.sha256(body).hexdigest()
        if sha256 in seen_hashes:
            continue
        seen_hashes.add(sha256)
        ext = _extension_for(image_url, content_type)
        asset_id = f"参考图_{len(manifest_assets) + 1:03d}"
        title = candidate.get("title") or candidate.get("alt") or "市场参考图"
        filename = f"{asset_id}_{slug_text(title, max_length=44)}{ext}"
        local_path = asset_dir / filename
        local_path.write_bytes(body)
        score_profile = _score_reference_candidate(candidate, content_type, len(body))

        manifest_assets.append(
            {
                "asset_id": asset_id,
                "title": title,
                "kind": candidate.get("kind", "market_reference"),
                "page_url": candidate.get("page_url", ""),
                "source_page_url": candidate.get("source_page_url", ""),
                "image_url": image_url,
                "local_path": _manifest_path(local_path, resolved_project),
                "content_type": content_type,
                "bytes": len(body),
                "sha256": sha256,
                "purchase_count": candidate.get("purchase_count"),
                "keywords": candidate.get("keywords", []),
                "visual_tags": candidate.get("visual_tags", []),
                "category_tags": score_profile["category_tags"],
                "reference_score": score_profile["reference_score"],
                "score_breakdown": score_profile["score_breakdown"],
                "can_be_image_reference": score_profile["can_be_image_reference"],
                "reference_decision": score_profile["reference_decision"],
                "reference_risk_flags": score_profile["reference_risk_flags"],
                "source_risk_flags": _as_list(candidate.get("risk_flags")) + _as_list(candidate.get("visual_risk_flags")),
                "usage_notes": [
                    "仅用于市场调研、构图分析、题材覆盖和风格方向参考。",
                    "高分图可作为 image2 参考图方向输入，但必须原创化重构，不得复刻原图、Logo、水印、真实品牌包装或可识别版权画面。",
                ],
            }
        )
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    output_root = resolved_project / RESEARCH_DIR_NAME if resolved_project else asset_dir.parent
    contact_sheet_path = _maybe_build_contact_sheet(asset_dir, output_root / "市场参考图总览.jpg")

    manifest = {
        "schema_version": "market-reference-assets/v1",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_json": str(source_path),
        "asset_dir": _manifest_path(asset_dir, resolved_project),
        "contact_sheet": _manifest_path(contact_sheet_path, resolved_project) if contact_sheet_path else "",
        "usage_policy": [
            "只从调研白名单素材平台采集公开可见封面、页面预览图或搜索页缩略图；不下载付费素材原片。",
            "本地参考图用于理解市场题材、构图、色彩、镜头类型和关键词，不作为最终交付素材。",
            "按 reference_score 选择可参考图；高分图可进入 image2 图生图参考计划，低分或高风险图只作为市场证据。",
            "后续 image2 生图必须生成原创画面，避免照搬参考图构图、人物、包装、文字、水印和可识别版权元素。",
        ],
        "assets": manifest_assets,
        "failed": failed,
    }
    manifest_path = write_json(output_root / "市场参考图清单.json", manifest)
    gallery_path = write_text(output_root / "市场参考图说明.md", _build_gallery_markdown(manifest))
    return {
        "system_output_success": True,
        "system_output_source_json": str(source_path),
        "system_output_asset_dir": str(asset_dir),
        "system_output_manifest": str(manifest_path),
        "system_output_gallery": str(gallery_path),
        "system_output_contact_sheet": str(contact_sheet_path) if contact_sheet_path else "",
        "system_output_asset_count": len(manifest_assets),
        "system_output_failed_count": len(failed),
    }


def _collect_candidates(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    root_keywords = data.get("keywords", [])
    pages = data.get("pages") or [data]
    for page in pages:
        page_url = page.get("page_url") or page.get("url") or page.get("location") or ""
        page_title = page.get("title", "")
        page_keywords = _as_list(page.get("keywords")) or root_keywords

        for image in _as_list(page.get("images")):
            candidate = _candidate_from_image(image, page_url, page_title, page_keywords)
            if candidate:
                candidates.append(candidate)

        for item in _as_list(page.get("items")):
            candidate = _candidate_from_item(item, page_url, page_keywords)
            if candidate:
                candidates.append(candidate)

        for node in _as_list(page.get("nodes")):
            image = node.get("img") if isinstance(node, dict) else None
            if not image:
                continue
            text = str(node.get("text", "")).strip()
            purchase_count = _extract_purchase_count(text)
            candidate = _candidate_from_image(image, page_url, page_title, page_keywords)
            if candidate:
                candidate.update(
                    {
                        "title": image.get("alt") or _clean_purchase_text(text) or candidate["title"],
                        "page_url": node.get("href", ""),
                        "purchase_count": purchase_count,
                        "kind": "related_cover" if "/watch/" in str(node.get("href", "")) else "page_image",
                    }
                )
                candidates.append(candidate)

        direct_image_url = page.get("image_url") or page.get("src")
        if direct_image_url:
            candidates.append(
                {
                    "title": page_title or page.get("alt", "market_reference"),
                    "kind": page.get("kind", "page_image"),
                    "page_url": page_url,
                    "source_page_url": page_url,
                    "image_url": urllib.parse.urljoin(page_url, direct_image_url),
                    "purchase_count": page.get("purchase_count"),
                    "keywords": page_keywords,
                    "visual_tags": _as_list(page.get("visual_tags")),
                }
            )
    return candidates


def _candidate_from_image(
    image: Dict[str, Any],
    page_url: str,
    page_title: str,
    page_keywords: Iterable[str],
) -> Dict[str, Any] | None:
    if not isinstance(image, dict):
        return None
    src = image.get("image_url") or image.get("src") or image.get("currentSrc")
    if not src:
        return None
    return {
        "title": image.get("title") or image.get("alt") or page_title or "market_reference",
        "kind": image.get("kind", "page_image"),
        "page_url": image.get("page_url") or page_url,
        "source_page_url": page_url,
        "image_url": urllib.parse.urljoin(page_url, src),
        "purchase_count": image.get("purchase_count"),
        "keywords": _as_list(image.get("keywords")) or list(page_keywords),
        "visual_tags": _as_list(image.get("visual_tags")),
        "risk_flags": _as_list(image.get("risk_flags")),
        "visual_risk_flags": _as_list(image.get("visual_risk_flags")),
        "width": image.get("width"),
        "height": image.get("height"),
    }


def _candidate_from_item(item: Dict[str, Any], page_url: str, page_keywords: Iterable[str]) -> Dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    image_url = item.get("image_url") or item.get("cover_url") or item.get("src")
    if not image_url and isinstance(item.get("img"), dict):
        image_url = item["img"].get("src")
    if not image_url:
        return None
    title = item.get("title") or item.get("alt")
    if not title and isinstance(item.get("img"), dict):
        title = item["img"].get("alt")
    return {
        "title": title or "market_reference",
        "kind": item.get("kind", "related_cover"),
        "page_url": item.get("page_url") or item.get("href") or "",
        "source_page_url": page_url,
        "image_url": urllib.parse.urljoin(page_url, image_url),
        "purchase_count": item.get("purchase_count"),
        "download_count": item.get("download_count"),
        "material_income": item.get("material_income"),
        "upload_time": item.get("upload_time"),
        "preview_video_url": item.get("preview_video_url"),
        "keywords": _as_list(item.get("keywords")) or list(page_keywords),
        "visual_tags": _as_list(item.get("visual_tags")),
        "risk_flags": _as_list(item.get("risk_flags")),
        "visual_risk_flags": _as_list(item.get("visual_risk_flags")),
    }


def _download_image(image_url: str, referer: str | None = None) -> Tuple[bytes, str]:
    request = urllib.request.Request(
        image_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": referer or "https://www.vjshi.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
        body = response.read()
    if content_type not in IMAGE_CONTENT_TYPES:
        raise OSError(f"非支持图片类型：{content_type or 'unknown'}")
    return body, content_type


def _looks_like_reference_image(candidate: Dict[str, Any]) -> bool:
    image_url = candidate.get("image_url", "")
    parsed = urllib.parse.urlparse(image_url)
    path = parsed.path.lower()
    if not parsed.scheme.startswith("http"):
        return False
    if path.endswith(".svg"):
        return False
    blocked = ["avatar", "logo", "assets/", "copyright-cover", "original-cover", "np-cover"]
    if any(token in image_url.lower() for token in blocked):
        return False
    if "pic.vjshi.com" in parsed.netloc:
        return True
    return any(path.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"])


def _is_allowed_market_source(candidate: Dict[str, Any]) -> bool:
    source_url = candidate.get("source_page_url") or candidate.get("page_url") or ""
    domain = _domain_from_url(source_url)
    if not domain:
        return False
    if any(_domain_matches(domain, blocked) for blocked in BLOCKED_RESEARCH_DOMAINS):
        return False
    return any(
        _domain_matches(domain, allowed)
        for source in ALLOWED_RESEARCH_SOURCES
        for allowed in source["domains"]
    )


def _extension_for(image_url: str, content_type: str) -> str:
    if content_type in IMAGE_CONTENT_TYPES:
        return IMAGE_CONTENT_TYPES[content_type]
    suffix = Path(urllib.parse.urlparse(image_url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return mimetypes.guess_extension(content_type) or ".jpg"


def _score_reference_candidate(candidate: Dict[str, Any], content_type: str, byte_count: int) -> Dict[str, Any]:
    text = _candidate_text(candidate)
    market_score = _market_signal_score(candidate)
    quality_score = _preview_quality_score(candidate, content_type, byte_count)
    relevance_score = _metadata_relevance_score(candidate)
    safety_score, risk_flags = _reference_safety_score(text)
    source_risk_flags = _as_list(candidate.get("risk_flags")) + _as_list(candidate.get("visual_risk_flags"))
    for flag in source_risk_flags:
        if flag and flag not in risk_flags:
            risk_flags.append(str(flag))
    auto_exclude_flags = {
        "watermark_or_platform_badge",
        "watermark_or_logo",
        "readable_text",
        "multi_panel_preview",
        "brand_or_logo",
    }
    if any(flag in auto_exclude_flags for flag in risk_flags):
        safety_score = min(safety_score, 45)
    platform_score = _platform_score(candidate)
    reference_score = round(
        market_score * 0.32
        + quality_score * 0.18
        + relevance_score * 0.2
        + safety_score * 0.22
        + platform_score * 0.08,
        1,
    )
    category_tags = _category_tags_for_text(text)
    can_be_image_reference = (
        reference_score >= 70
        and safety_score >= 65
        and not any(flag in auto_exclude_flags for flag in risk_flags)
    )
    if can_be_image_reference:
        decision = "可作为 image2 方向参考图，使用时必须原创化重构。"
    elif reference_score >= 55:
        decision = "仅作为市场证据和关键词参考，人工确认后才可作图生图参考。"
    else:
        decision = "不建议作为图生图参考，只保留为低权重市场证据。"
    return {
        "category_tags": category_tags,
        "reference_score": reference_score,
        "score_breakdown": {
            "market_signal_score": market_score,
            "preview_quality_score": quality_score,
            "metadata_relevance_score": relevance_score,
            "reference_safety_score": safety_score,
            "platform_score": platform_score,
        },
        "can_be_image_reference": can_be_image_reference,
        "reference_decision": decision,
        "reference_risk_flags": risk_flags,
    }


def _market_signal_score(candidate: Dict[str, Any]) -> int:
    score = 45
    purchase_count = candidate.get("purchase_count")
    if isinstance(purchase_count, (int, float)):
        score += min(35, int(purchase_count) // 4)
    download_count = candidate.get("download_count")
    if isinstance(download_count, (int, float)):
        score += min(20, int(download_count) // 10)
    material_income = candidate.get("material_income")
    if isinstance(material_income, (int, float)):
        score += min(20, int(material_income) // 100)
    kind = str(candidate.get("kind", ""))
    if kind in {"related_cover", "market_reference"}:
        score += 8
    if candidate.get("page_url"):
        score += 6
    return _clamp_score(score)


def _preview_quality_score(candidate: Dict[str, Any], content_type: str, byte_count: int) -> int:
    score = 45
    width = candidate.get("width")
    height = candidate.get("height")
    if isinstance(width, (int, float)) and isinstance(height, (int, float)):
        pixels = int(width) * int(height)
        if pixels >= 600_000:
            score += 25
        elif pixels >= 250_000:
            score += 15
        elif pixels >= 90_000:
            score += 8
    if byte_count >= 180_000:
        score += 18
    elif byte_count >= 70_000:
        score += 10
    elif byte_count >= 25_000:
        score += 5
    if content_type == "image/webp":
        score += 3
    return _clamp_score(score)


def _metadata_relevance_score(candidate: Dict[str, Any]) -> int:
    score = 35
    title = str(candidate.get("title", "")).strip()
    keywords = _as_list(candidate.get("keywords"))
    visual_tags = _as_list(candidate.get("visual_tags"))
    if title and title != "market_reference":
        score += 15
    score += min(25, len([item for item in keywords if str(item).strip()]) * 4)
    score += min(20, len([item for item in visual_tags if str(item).strip()]) * 5)
    if _category_tags_for_text(_candidate_text(candidate)):
        score += 10
    return _clamp_score(score)


def _reference_safety_score(text: str) -> tuple[int, List[str]]:
    score = 85
    risk_flags: List[str] = []
    risk_rules = [
        ("watermark_or_logo", ["水印", "logo", "Logo", "LOGO", "标志", "商标"]),
        ("brand_or_packaging", ["品牌", "包装", "礼盒包装", "厂牌", "车标", "型号"]),
        ("readable_text", ["文字", "字幕", "标题", "海报", "字体", "UI", "界面", "数据大屏"]),
        ("recognizable_people", ["明星", "名人", "肖像", "儿童", "人像"]),
        ("template_like", ["模板", "片头", "字幕条", "标题包装", "MG", "ae模板", "pr模板"]),
    ]
    for flag, keywords in risk_rules:
        if any(keyword.lower() in text.lower() for keyword in keywords):
            risk_flags.append(flag)
            score -= 12
    return _clamp_score(score), risk_flags


def _platform_score(candidate: Dict[str, Any]) -> int:
    domain = _domain_from_url(candidate.get("source_page_url") or candidate.get("page_url") or "")
    primary_domains = [
        "vjshi.com",
        "stock.xinpianchang.com",
        "vcg.com",
        "pond5.com",
        "shutterstock.com",
        "stock.adobe.com",
        "gettyimages.com",
        "istockphoto.com",
    ]
    cinematic_domains = ["artgrid.io", "filmsupply.com", "dissolve.com"]
    if any(_domain_matches(domain, item) for item in primary_domains):
        return 90
    if any(_domain_matches(domain, item) for item in cinematic_domains):
        return 78
    return 60


def _category_tags_for_text(text: str) -> List[str]:
    rules = [
        ("产品特写", ["产品", "礼盒", "月饼", "茶席", "美食", "包装", "特写", "微距", "晶圆", "芯片"]),
        ("人物情绪", ["家庭", "团圆", "人物", "工程师", "团队", "孩子", "父母", "老人", "人像"]),
        ("场景建立", ["全景", "建立", "城市", "工厂", "车间", "园区", "街巷", "航拍", "外景"]),
        ("技术卖点", ["AI", "智能", "数字孪生", "机械臂", "自动化", "AGV", "控制室", "数据"]),
        ("节日氛围", ["中秋", "春节", "节日", "灯笼", "月亮", "桂花", "团圆", "祝福"]),
        ("转场收尾", ["收尾", "片尾", "转场", "背景", "空镜", "祝福"]),
    ]
    tags = [tag for tag, keywords in rules if any(keyword.lower() in text.lower() for keyword in keywords)]
    return tags or ["未分类"]


def _candidate_text(candidate: Dict[str, Any]) -> str:
    values = [
        candidate.get("title", ""),
        candidate.get("kind", ""),
        candidate.get("page_url", ""),
        candidate.get("source_page_url", ""),
        " ".join(str(item) for item in _as_list(candidate.get("keywords"))),
        " ".join(str(item) for item in _as_list(candidate.get("visual_tags"))),
    ]
    return " ".join(str(value) for value in values if str(value).strip())


def _clamp_score(score: int | float) -> int:
    return min(100, max(0, int(round(score))))


def _build_gallery_markdown(manifest: Dict[str, Any]) -> str:
    lines = [
        "# 市场参考图采集索引",
        "",
        "> 这些图片只用于市场调研、构图分析和参考图规划，不作为最终商业交付素材。",
        "",
    ]
    if manifest.get("contact_sheet"):
        lines.extend(["## 总览拼图", "", f"![市场参考图总览]({manifest['contact_sheet']})", ""])
    for asset in manifest["assets"]:
        local_path = asset["local_path"]
        lines.extend(
            [
                f"## {asset['asset_id']} {asset['title']}",
                "",
                f"- 来源作品：{asset.get('page_url') or asset.get('source_page_url')}",
                f"- 购买量：{asset.get('purchase_count') if asset.get('purchase_count') is not None else ''}",
                f"- 参考评分：{asset.get('reference_score', '')}",
                f"- 参考决策：{asset.get('reference_decision', '')}",
                f"- 分类标签：{', '.join(asset.get('category_tags', []))}",
                f"- 本地文件：`{local_path}`",
                "",
                f"![{asset['title']}]({local_path})",
                "",
            ]
        )
    return "\n".join(lines)


def _maybe_build_contact_sheet(asset_dir: Path, output_path: Path) -> Path | None:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None

    image_paths = sorted(
        list(asset_dir.glob("*.jpg")) + list(asset_dir.glob("*.jpeg")) + list(asset_dir.glob("*.png")) + list(asset_dir.glob("*.webp"))
    )
    if not image_paths:
        return None

    thumbs = []
    for path in image_paths:
        try:
            image = Image.open(path).convert("RGB")
        except Exception:
            continue
        image.thumbnail((360, 220))
        canvas = Image.new("RGB", (360, 260), "white")
        canvas.paste(image, ((360 - image.width) // 2, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 228), path.stem[:32], fill=(20, 20, 20))
        thumbs.append(canvas)
    if not thumbs:
        return None

    cols = 2
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 360, rows * 260), (245, 245, 245))
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((index % cols) * 360, (index // cols) * 260))

    ensure_dir(output_path.parent)
    sheet.save(output_path, quality=92)
    return output_path


def _manifest_path(path: Path, project_dir: Path | None) -> str:
    return relative_path(path, project_dir) if project_dir else str(path)


def _normalize_url_for_dedupe(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _extract_purchase_count(text: str) -> int | None:
    match = re.search(r"(\d+)\s*购买", text)
    return int(match.group(1)) if match else None


def _clean_purchase_text(text: str) -> str:
    return re.sub(r"^\d+\s*购买\s*", "", text).strip()
