"""Two-pass VJShi market keyword mining and commercial direction analysis."""

from __future__ import annotations

import html as html_lib
import base64
import gzip
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from .file_manager import MARKET_MINING_DIR_NAME, RESEARCH_DIR_NAME, ensure_dir, write_json
from .production_text import clean_visual_phrase, clean_visual_terms


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
)

VJSHI_HOME = "https://www.vjshi.com/"
VJSHI_VIDEO_MATERIAL_CATEGORY_ID = "230"
DEFAULT_FIRST_PASS_LIMIT = 20
DEFAULT_DETAIL_LIMIT = 10
DEFAULT_SECOND_PASS_LIMIT = 10
POST_RESEARCH_NEXT_STEP_QUESTION = (
    "调研已完成。是否继续采集高价值作品的公开预览视频并去水印拆帧，"
    "供你在 Electron 参考帧视图中挑选？这些帧只作为镜头语言、构图、光线和节奏参考，"
    "不能作为最终交付或商用素材。"
)

TOPIC_DOMAIN_MARKERS = {
    "business_signing": ["商务签约", "商务握手", "签约", "签约成功", "合作签约", "合作握手", "握手", "洽谈", "签字", "会议室"],
    "science_lab": ["新材料", "科研", "实验室", "研发", "大学科研", "科研人员", "科研团队", "材料实验室", "材料测试"],
    "duanwu_festival": ["端午", "端午节", "粽子", "粽叶", "龙舟", "赛龙舟", "艾草", "香囊", "五彩绳"],
    "festival_ecommerce": ["礼盒", "节日", "促销", "电商", "购物节", "618"],
    "shenzhen_city": ["深圳", "福田", "南山", "前海", "深圳湾", "湾区", "地标", "城市天际线"],
}

OFF_TOPIC_DOMAIN_TOKENS = {
    "business_signing": ["商务签约", "商务握手", "签约成功", "合作签约", "合作握手", "握手", "洽谈", "签字"],
    "duanwu_festival": ["端午", "端午节", "粽子", "粽叶", "龙舟", "赛龙舟", "艾草", "香囊", "五彩绳"],
    "festival_ecommerce": ["礼盒", "节日", "促销", "电商", "购物节", "618"],
    "shenzhen_city": ["深圳", "福田", "南山", "前海", "深圳湾", "湾区", "地标", "城市天际线"],
}

GENERIC_TOPIC_ANCHOR_TERMS = {
    "商务",
    "宣传片",
    "素材",
    "视频素材",
    "商业素材",
    "AI",
    "ai",
    "团队",
    "人员",
    "企业",
    "公司",
    "合作",
    "高端",
}

GENERIC_TOPIC_ANCHOR_FRAGMENTS = {
    "商务宣传片",
    "宣传片素材",
    "商务素材",
    "视频素材",
    "商业素材",
}

CAMERA_TERMS = {
    "航拍",
    "俯拍",
    "特写",
    "微距",
    "近景",
    "中景",
    "远景",
    "全景",
    "空镜",
    "延时",
    "升格",
    "慢动作",
    "推近",
    "拉远",
    "环绕",
    "跟拍",
    "横移",
    "俯视",
    "仰拍",
}

VISUAL_TERMS = {
    "龙舟",
    "赛龙舟",
    "粽子",
    "粽叶",
    "糯米",
    "蒸汽",
    "艾草",
    "香囊",
    "雄黄酒",
    "五彩绳",
    "江面",
    "水花",
    "鼓手",
    "家庭",
    "手部",
    "礼盒",
    "食物",
    "美食",
    "城市",
    "深圳",
    "深圳湾",
    "前海",
    "福田",
    "南山",
    "罗湖",
    "宝安",
    "深圳CBD",
    "福田CBD",
    "南山CBD",
    "城市天际线",
    "城市夜景",
    "万家灯火",
    "深圳地标",
    "平安金融中心",
    "平安大厦",
    "市民中心",
    "人才公园",
    "欢乐港湾",
    "粤港澳大湾区",
    "超级总部",
    "总部基地",
    "摩天大楼",
    "古镇",
    "民俗",
    "国风",
    "节日",
    "人群",
    "河道",
    "湖面",
}

COMMERCIAL_USE_TERMS = {
    "广告",
    "宣传片",
    "电商",
    "海报",
    "片头",
    "转场",
    "背景",
    "节日活动",
    "促销",
    "开场",
    "包装",
    "礼盒",
    "商用",
    "竖版",
    "横版",
    "短视频",
}

RISK_KEYWORDS = {
    "watermark_or_platform_badge": ["水印", "角标", "平台", "vjshi", "样片", "预览"],
    "readable_text": ["文字", "字幕", "海报", "标题", "字体", "书法", "对联"],
    "multi_panel_preview": ["九宫格", "多宫格", "拼图", "合集", "组图"],
    "brand_or_logo": ["logo", "Logo", "LOGO", "品牌", "商标", "厂牌"],
    "recognizable_people": ["明星", "名人", "肖像", "儿童", "人像"],
}


def mine_market(
    project_dir: str | Path,
    topic: str,
    seed_keywords: Sequence[str] | str | None = None,
    per_keyword: int = DEFAULT_FIRST_PASS_LIMIT,
    detail_top: int = DEFAULT_DETAIL_LIMIT,
    second_pass_top: int = DEFAULT_SECOND_PASS_LIMIT,
    delay_seconds: float = 0.35,
    fetch_live: bool = True,
    first_pass_source_json: str | Path | None = None,
    second_pass_source_json: str | Path | None = None,
    video_material_only: bool = True,
) -> Dict[str, Any]:
    """Run first-pass mining, keyword analysis, second-pass mining, and write artifacts."""

    project_path = Path(project_dir)
    mining_dir = ensure_dir(project_path / RESEARCH_DIR_NAME / MARKET_MINING_DIR_NAME)
    seeds = _normalize_seed_keywords(seed_keywords) or build_seed_keywords(topic)
    generated_at = _now()

    seed_payload = {
        "schema_version": "market-mining-seed-keywords/v1",
        "topic": topic,
        "platform": "vjshi",
        "sort_policy": "preserve the platform default ranking after the video-material filter; sales/download/income are analysis signals only",
        "video_material_only": video_material_only,
        "search_filter_policy": (
            "VJShi search URLs must include categoryIdForSoftware=230&st=y so that candidates come from 视频素材."
            if video_material_only
            else "All media types allowed by explicit operator override."
        ),
        "seed_keywords": seeds[:5],
        "generated_at": generated_at,
    }
    write_json(mining_dir / "种子关键词.json", seed_payload)

    first_search_results = _load_search_source(first_pass_source_json, "first_pass") if first_pass_source_json else []
    if not first_search_results and fetch_live:
        first_search_results = _run_search_pass(
            seeds[:5],
            pass_name="first_pass",
            per_keyword=per_keyword,
            sort_mode="platform_default",
            delay_seconds=delay_seconds,
            video_material_only=video_material_only,
        )
    first_search_results = _dedupe_works(first_search_results)
    _write_jsonl(mining_dir / "光厂第一轮搜索结果.jsonl", first_search_results)

    first_details = _load_detail_source(first_pass_source_json, first_search_results, "first_pass") if first_pass_source_json else []
    if not first_details:
        first_details = _detail_pass(
            first_search_results,
            pass_name="first_pass",
            limit=detail_top,
            delay_seconds=delay_seconds,
            fetch_live=fetch_live,
            balanced_by_search_keyword=True,
        )
    first_details = _dedupe_works(first_details)
    _write_jsonl(mining_dir / "光厂第一轮作品详情.jsonl", first_details)

    initial_analysis = analyze_market_keywords(topic, seeds[:5], first_details, [], use_market_signals=False)
    prompts_for_second_pass, rejected_prompts = _filter_topic_relevant_buyer_prompts(
        initial_analysis["buyer_search_prompts"],
        topic,
        seeds[:5],
        first_details,
    )
    rejected_prompts_path = write_json(
        mining_dir / "买家搜索提示词_已排除.json",
        {
            "schema_version": "buyer-search-prompts-rejected/v1",
            "topic": topic,
            "rejection_policy": "Prompts must match the requested theme before any second-pass crawling.",
            "rejected_prompts": rejected_prompts,
        },
    )

    second_search_results = _load_search_source(second_pass_source_json, "second_pass") if second_pass_source_json else []
    if not second_search_results and fetch_live:
        second_search_results = _run_search_pass(
            [item["prompt"] for item in prompts_for_second_pass],
            pass_name="second_pass",
            per_keyword=second_pass_top,
            sort_mode="platform_default",
            delay_seconds=delay_seconds,
            video_material_only=video_material_only,
        )
    second_search_results = _dedupe_works(second_search_results)
    _write_jsonl(mining_dir / "光厂第二轮搜索结果.jsonl", second_search_results)

    second_details = _load_detail_source(second_pass_source_json, second_search_results, "second_pass") if second_pass_source_json else []
    if not second_details:
        second_details = _detail_pass(
            second_search_results,
            pass_name="second_pass",
            limit=second_pass_top,
            delay_seconds=delay_seconds,
            fetch_live=fetch_live,
            balanced_by_search_keyword=True,
        )
    second_details = _dedupe_works(second_details)
    _write_jsonl(mining_dir / "光厂第二轮作品详情.jsonl", second_details)

    final_analysis = analyze_market_keywords(topic, seeds[:5], first_details, second_details, use_market_signals=True)
    prompts_with_second_pass = _attach_second_pass_counts(prompts_for_second_pass, second_search_results, second_details)
    directions = _attach_second_pass_evidence(final_analysis["commercial_ai_directions"], second_details)

    keyword_analysis_path = write_json(mining_dir / "关键词分析.json", final_analysis["keyword_analysis"])
    directions_path = write_json(
        mining_dir / "商业AI方向.json",
        {
            "schema_version": "commercial-ai-directions/v1",
            "topic": topic,
            "platform_priority": ["vjshi"],
            "directions": directions,
        },
    )
    prompts_path = write_json(
        mining_dir / "买家搜索提示词.json",
        {
            "schema_version": "buyer-search-prompts/v1",
            "topic": topic,
            "prompt_definition": "buyer-facing commercial search phrases for stock media platforms",
            "topic_relevance_policy": "Only prompts accepted by topic_relevance_gate are used for second-pass crawling.",
            "prompts": prompts_with_second_pass,
        },
    )
    summary = _build_market_mining_summary(
        topic,
        seeds[:5],
        directions,
        prompts_with_second_pass,
        final_analysis["keyword_analysis"],
        first_details,
        second_details,
    )
    summary_path = write_json(mining_dir / "市场反挖摘要.json", summary)
    review_path = _ensure_operator_review(mining_dir, project_path)
    next_step_path = _write_post_research_next_step(mining_dir, project_path)

    return {
        "system_output_success": True,
        "system_output_project_dir": str(project_path),
        "system_output_market_mining_dir": str(mining_dir),
        "system_output_seed_keywords": str(mining_dir / "种子关键词.json"),
        "system_output_first_pass_search_results": str(mining_dir / "光厂第一轮搜索结果.jsonl"),
        "system_output_first_pass_work_details": str(mining_dir / "光厂第一轮作品详情.jsonl"),
        "system_output_keyword_analysis": str(keyword_analysis_path),
        "system_output_commercial_ai_directions": str(directions_path),
        "system_output_buyer_search_prompts": str(prompts_path),
        "system_output_rejected_buyer_search_prompts": str(rejected_prompts_path),
        "system_output_second_pass_search_results": str(mining_dir / "光厂第二轮搜索结果.jsonl"),
        "system_output_second_pass_work_details": str(mining_dir / "光厂第二轮作品详情.jsonl"),
        "system_output_market_mining_summary": str(summary_path),
        "system_output_operator_review": str(review_path),
        "system_output_post_research_next_step": str(next_step_path),
        "system_output_recommended_next_action": "ask_user_before_collect_high_value_video_frames",
        "system_output_next_step_question": POST_RESEARCH_NEXT_STEP_QUESTION,
        "system_output_next_step_commands": _post_research_next_step_commands(project_path),
        "system_output_seed_keyword_count": len(seeds[:5]),
        "system_output_first_pass_work_count": len(first_details),
        "system_output_second_pass_work_count": len(second_details),
        "system_output_buyer_prompt_count": len(prompts_with_second_pass),
        "system_output_rejected_buyer_prompt_count": len(rejected_prompts),
        "system_output_message": (
            "光厂两轮关键词反挖产物已生成；第二轮查询使用 买家搜索提示词.json 中的买家搜索提示词。"
            "下一步应询问用户是否继续采集高价值作品的公开预览视频并去水印拆帧，供参考帧挑选。"
        ),
    }


def build_seed_keywords(topic: str, max_keywords: int = 5) -> List[str]:
    """Build 3-5 conservative seed keywords from the user's theme."""

    cleaned = _clean_text(topic)
    base = re.sub(r"(AI|ai|视频|素材|商业|高清|4K|模板|参考|调研)", " ", cleaned)
    base = re.sub(r"\s+", " ", base).strip()
    seeds: List[str] = []
    if base:
        seeds.append(base)
    if cleaned and cleaned not in seeds:
        seeds.append(cleaned)
    if any(token in cleaned for token in ["端午", "端午节", "龙舟", "粽子"]):
        seeds.extend(["端午节", "赛龙舟", "粽子", "包粽子", "端午习俗"])
    if any(token in cleaned for token in ["中秋", "月饼", "团圆"]):
        seeds.extend(["中秋节", "月饼", "团圆", "赏月", "中秋礼盒"])
    seeds.extend(_tokenize_terms(base))
    return _unique_nonempty(seeds)[:max(3, max_keywords)]


def parse_vjshi_search_results(
    html_source: str,
    search_keyword: str,
    source_url: str = "",
    pass_name: str = "first_pass",
    sort_mode: str = "platform_default",
    limit: int = DEFAULT_FIRST_PASS_LIMIT,
) -> List[Dict[str, Any]]:
    """Parse a VJShi search/list page into normalized work rows."""

    source = _normalize_html_source(html_source)
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    pattern = re.compile(r"(?:(?:https?:)?//(?:www\.)?vjshi\.com)?/watch/(\d+)\.html", re.I)
    for match in pattern.finditer(source):
        work_id = match.group(1)
        if work_id in seen:
            continue
        seen.add(work_id)
        start = max(0, match.start() - 1500)
        end = min(len(source), match.end() + 2200)
        window = source[start:end]
        work_url = f"https://www.vjshi.com/watch/{work_id}.html"
        image_urls = _extract_image_urls(window)
        title = _extract_title(window, fallback=f"vjshi_{work_id}")
        purchase_count = _extract_count(window, ["购买", "销量", "使用"])
        rows.append(
            {
                "schema_version": "vjshi-search-result/v1",
                "source_platform": "vjshi",
                "pass_name": pass_name,
                "search_keyword": search_keyword,
                "sort_mode": sort_mode,
                "rank": len(rows) + 1,
                "work_id": work_id,
                "title": title,
                "work_url": work_url,
                "cover_url": image_urls[0] if image_urls else "",
                "purchase_count": purchase_count,
                "download_count": _extract_download_count(window),
                "resolution": _extract_resolution(window),
                "duration": _extract_duration(window),
                "aigc_flag": _has_aigc_flag(window),
                "video_material_filter": _has_vjshi_video_material_filter(source_url),
                "material_scope": "video_material" if _has_vjshi_video_material_filter(source_url) else "",
                "risk_flags": _risk_flags_from_text(window),
                "source_search_url": source_url,
                "captured_at": _now(),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def parse_vjshi_work_detail(html_source: str, base_work: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Parse a VJShi detail page into normalized work detail fields."""

    base = dict(base_work or {})
    source = _normalize_html_source(html_source)
    text = _clean_text(_strip_tags(source))
    structured = _extract_video_object(source)
    material_fields = _extract_material_detail_fields(source)
    work_id = str(base.get("work_id") or _first_match(source, r"/watch/(\d+)\.html") or "")
    title = (
        base.get("title")
        or material_fields.get("素材标题")
        or _clean_video_title(str(structured.get("name") or ""))
        or _extract_title(source, fallback=f"vjshi_{work_id}" if work_id else "vjshi_work")
    )
    detail_keywords = _extract_detail_keywords(source, title)
    preview_images = _extract_image_urls(source)[:12]
    preview_video_url = str(structured.get("contentUrl") or "") or _extract_video_url(source)
    sample_video_url = _extract_sample_video_url(source)
    src_file_type = _extract_src_file_type(source)
    material_type = material_fields.get("素材类型") or _material_type_from_src_file_type(src_file_type)
    upload_time = material_fields.get("上传日期") or _date_from_iso(str(structured.get("uploadDate") or "")) or _extract_date(source)
    purchase_count = _first_int(base.get("purchase_count")) or _first_int(material_fields.get("购买")) or _extract_count(source, ["购买", "销量"])
    download_count = _first_int(base.get("download_count")) or _extract_download_count(source)
    if download_count is None and purchase_count is not None and _has_download_times_marker(source):
        download_count = purchase_count
    detail = {
        "schema_version": "vjshi-work-detail/v1",
        "source_platform": "vjshi",
        "pass_name": base.get("pass_name", ""),
        "search_keyword": base.get("search_keyword", ""),
        "rank": base.get("rank"),
        "source_search_url": base.get("source_search_url", ""),
        "video_material_filter": bool(base.get("video_material_filter")) or _has_vjshi_video_material_filter(str(base.get("source_search_url") or "")),
        "material_scope": base.get("material_scope", ""),
        "work_id": work_id,
        "title": title,
        "work_url": base.get("work_url") or (f"https://www.vjshi.com/watch/{work_id}.html" if work_id else ""),
        "cover_url": base.get("cover_url") or (preview_images[0] if preview_images else ""),
        "purchase_count": purchase_count,
        "download_count": download_count,
        "resolution": base.get("resolution") or _extract_resolution(source),
        "duration": base.get("duration") or _format_iso_duration(str(structured.get("duration") or "")) or _extract_duration(source),
        "aigc_flag": bool(base.get("aigc_flag")) or bool(material_fields.get("AIGC说明")) or _has_aigc_flag(source),
        "detail_keywords": detail_keywords,
        "material_income": _extract_money(source),
        "upload_time": upload_time,
        "click_count": _first_int(material_fields.get("点击")) or _json_ld_interaction_count(structured),
        "file_size": material_fields.get("文件大小") or "",
        "material_type": material_type,
        "src_file_type": src_file_type,
        "transparent_channel": material_fields.get("透明通道") or "",
        "seamless_loop": material_fields.get("无缝循环") or "",
        "aigc_description": material_fields.get("AIGC说明") or "",
        "preview_note": _extract_preview_note(text),
        "preview_images": preview_images,
        "sample_video_url": sample_video_url,
        "preview_video_url": preview_video_url,
        "preview_video_source": "sample_video_url" if sample_video_url else ("video_object_content_url" if preview_video_url else ""),
        "author": _json_ld_author(structured) or _extract_labeled_text(source, ["作者", "设计师", "上传者", "店铺"]),
        "category": _extract_labeled_text(source, ["分类", "类别", "频道"]),
        "related_work_urls": _unique_nonempty(
            f"https://www.vjshi.com/watch/{item}.html"
            for item in re.findall(r"/watch/(\d+)\.html", source)
            if item != work_id
        )[:16],
        "risk_flags": _unique_nonempty(_as_list(base.get("risk_flags")) + _risk_flags_from_text(text)),
        "captured_at": _now(),
    }
    detail["market_signal_score"] = _work_market_signal_score(detail)
    detail["commercial_terms"] = [term for term in detail_keywords if term in COMMERCIAL_USE_TERMS]
    detail["camera_terms"] = [term for term in detail_keywords if term in CAMERA_TERMS]
    detail["visual_terms"] = [term for term in detail_keywords if term in VISUAL_TERMS]
    return detail


def fetch_vjshi_work_detail(
    work_url: str,
    output_json: str | Path | None = None,
    referer: str | None = None,
    search_keyword: str = "",
) -> Dict[str, Any]:
    """Fetch one public VJShi work detail page and optionally write the parsed JSON."""

    work_id = _work_id_from_url(work_url)
    canonical_url = f"https://www.vjshi.com/watch/{work_id}.html" if work_id else work_url
    html_source = _fetch_url(work_url, referer=referer or VJSHI_HOME)
    detail = parse_vjshi_work_detail(
        html_source,
        {
            "work_id": work_id,
            "work_url": canonical_url,
            "source_url": work_url,
            "search_keyword": search_keyword,
            "pass_name": "single_work",
        },
    )
    detail["source_url"] = work_url
    if output_json:
        write_json(Path(output_json), detail)
    return detail


def fetch_vjshi_work_details_batch(
    urls: Sequence[str] | str | None = None,
    url_file: str | Path | None = None,
    output_jsonl: str | Path | None = None,
    output_json: str | Path | None = None,
    referer: str | None = None,
    search_keyword: str = "",
    delay_seconds: float = 0.35,
) -> Dict[str, Any]:
    """Fetch multiple public VJShi work detail pages."""

    work_urls = _normalize_batch_urls(urls) + _load_batch_urls(url_file)
    work_urls = _unique_nonempty(work_urls)
    details: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for index, work_url in enumerate(work_urls, start=1):
        try:
            detail = fetch_vjshi_work_detail(work_url, referer=referer, search_keyword=search_keyword)
            detail["batch_index"] = index
            details.append(detail)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            errors.append(
                {
                    "batch_index": index,
                    "work_url": work_url,
                    "error": str(exc),
                    "captured_at": _now(),
                }
            )
        if delay_seconds > 0 and index < len(work_urls):
            time.sleep(delay_seconds)

    payload = {
        "schema_version": "vjshi-work-details-batch/v1",
        "source_platform": "vjshi",
        "requested_count": len(work_urls),
        "success_count": len(details),
        "error_count": len(errors),
        "generated_at": _now(),
        "details": details,
        "errors": errors,
    }
    if output_jsonl:
        _write_jsonl(Path(output_jsonl), details + errors)
    if output_json:
        write_json(Path(output_json), payload)
    return payload


def _normalize_batch_urls(urls: Sequence[str] | str | None) -> List[str]:
    if not urls:
        return []
    if isinstance(urls, str):
        return _unique_nonempty(re.split(r"[\n,]+", urls))
    return _unique_nonempty(str(item) for item in urls)


def _load_batch_urls(url_file: str | Path | None) -> List[str]:
    if not url_file:
        return []
    path = Path(url_file)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".json", ".jsonl"}:
        if path.suffix.lower() == ".jsonl":
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            data = json.loads(text)
            rows = list(_iter_source_items(data)) if isinstance(data, dict) else _as_list(data)
        urls = []
        for row in rows:
            if isinstance(row, str):
                urls.append(row)
            elif isinstance(row, dict):
                urls.append(str(row.get("work_url") or row.get("url") or row.get("page_url") or ""))
        return _unique_nonempty(urls)
    return _unique_nonempty(line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#"))


def analyze_market_keywords(
    topic: str,
    seed_keywords: Sequence[str],
    first_pass_details: Sequence[Dict[str, Any]],
    second_pass_details: Sequence[Dict[str, Any]] | None = None,
    use_market_signals: bool = False,
) -> Dict[str, Any]:
    """Analyze mined works and produce keyword stats, directions, and buyer prompts."""

    second_pass_details = second_pass_details or []
    all_details = list(first_pass_details) + list(second_pass_details)
    analysis_mode = "market_signal_weighted" if use_market_signals else "semantic_only"
    term_counter: Counter[str] = Counter()
    weighted_counter: Counter[str] = Counter()
    cooccurrence: Counter[tuple[str, str]] = Counter()
    term_work_ids: defaultdict[str, set[str]] = defaultdict(set)

    for work in all_details:
        terms = _work_terms(work)
        signal = max(1, _work_market_signal_score(work)) if use_market_signals else 1
        for term in terms:
            term_counter[term] += 1
            weighted_counter[term] += signal
            if work.get("work_id"):
                term_work_ids[term].add(str(work["work_id"]))
        for left_index, left in enumerate(terms):
            for right in terms[left_index + 1 : left_index + 8]:
                if left != right:
                    cooccurrence[tuple(sorted((left, right)))] += max(1, signal // 10)

    classified = _classify_terms(weighted_counter)
    directions = _build_commercial_directions(
        topic,
        seed_keywords,
        all_details,
        classified,
        weighted_counter,
        use_market_signals=use_market_signals,
    )
    prompts = _build_buyer_prompts(topic, directions, all_details, use_market_signals=use_market_signals)
    keyword_analysis = {
        "schema_version": "market-keyword-analysis/v1",
        "topic": topic,
        "seed_keywords": list(seed_keywords),
        "analysis_mode": analysis_mode,
        "market_signals_used_for_keyword_weighting": use_market_signals,
        "generated_at": _now(),
        "source_work_count": len(first_pass_details),
        "second_pass_work_count": len(second_pass_details),
        "term_frequency": _counter_rows(term_counter, term_work_ids),
        "weighted_terms": _weighted_term_rows(weighted_counter, term_work_ids),
        "classified_terms": classified,
        "cooccurrence": [
            {"terms": list(pair), "score": score}
            for pair, score in cooccurrence.most_common(80)
        ],
        "analysis_notes": _keyword_analysis_notes(use_market_signals),
    }
    return {
        "keyword_analysis": keyword_analysis,
        "commercial_ai_directions": directions,
        "buyer_search_prompts": prompts,
    }


def _keyword_analysis_notes(use_market_signals: bool) -> List[str]:
    if use_market_signals:
        return [
            "第二轮详情采集后，购买/下载量、素材收入等市场信号只用于商业方向、参考图和镜头比例优先级。",
            "买家搜索提示词是素材平台检索短语，不是最终 image2 长 prompt。",
            "带角标、水印、多宫格、可读文字、品牌包装的画面只作为证据，默认不进入图生图参考。",
        ]
    return [
        "第一轮关键词分析只使用标题、详情关键词和来源搜索词，不使用购买量、点击量、上传时间、素材收入等市场信号。",
        "第一轮输出主题相关关键词和买家搜索提示词候选，用于第二轮反挖搜索。",
        "买家搜索提示词是素材平台检索短语，不是最终 image2 长 prompt。",
    ]


def _run_search_pass(
    keywords: Sequence[str],
    pass_name: str,
    per_keyword: int,
    sort_mode: str,
    delay_seconds: float,
    video_material_only: bool = True,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for keyword in _unique_nonempty(keywords):
        search_url = build_vjshi_search_url(keyword, sort_mode, video_material_only=video_material_only)
        try:
            html_source = _fetch_url(search_url, referer=VJSHI_HOME)
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
        rows.extend(parse_vjshi_search_results(html_source, keyword, search_url, pass_name, sort_mode, per_keyword))
        if delay_seconds > 0:
            time.sleep(delay_seconds)
    return rows


def _detail_pass(
    search_results: Sequence[Dict[str, Any]],
    pass_name: str,
    limit: int,
    delay_seconds: float,
    fetch_live: bool,
    balanced_by_search_keyword: bool = False,
) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []
    rows = _select_detail_rows(search_results, limit, balanced_by_search_keyword)
    for row in rows:
        base = {**row, "pass_name": pass_name}
        if fetch_live and row.get("work_url"):
            try:
                html_source = _fetch_url(str(row["work_url"]), referer=row.get("source_search_url") or VJSHI_HOME)
                detail = parse_vjshi_work_detail(html_source, base)
            except (urllib.error.URLError, TimeoutError, OSError):
                detail = _detail_from_search_row(base)
        else:
            detail = _detail_from_search_row(base)
        details.append(detail)
        if delay_seconds > 0 and fetch_live:
            time.sleep(delay_seconds)
    return details


def _select_detail_rows(
    search_results: Sequence[Dict[str, Any]],
    limit: int,
    balanced_by_search_keyword: bool = False,
) -> List[Dict[str, Any]]:
    capped_limit = max(0, int(limit))
    if not balanced_by_search_keyword:
        return list(search_results)[:capped_limit]
    counts: Counter[str] = Counter()
    selected: List[Dict[str, Any]] = []
    for row in search_results:
        key = str(row.get("search_keyword") or "")
        if counts[key] >= capped_limit:
            continue
        selected.append(row)
        counts[key] += 1
    return selected


def build_vjshi_search_url(keyword: str, sort_mode: str = "platform_default", video_material_only: bool = True) -> str:
    params = {"wd": keyword}
    if video_material_only:
        params.update({"categoryIdForSoftware": VJSHI_VIDEO_MATERIAL_CATEGORY_ID, "st": "y"})
    if sort_mode not in {"", "default", "platform_default"}:
        params["sort"] = sort_mode
    query = urllib.parse.urlencode(params)
    path = "so" if video_material_only else "search"
    return f"https://www.vjshi.com/{path}?{query}"


def _fetch_url(url: str, referer: str | None = None, cookie: str | None = None) -> str:
    text = _fetch_url_once(url, referer=referer, cookie=cookie)
    if cookie is None and "acw_sc__v2" in text and "arg1" in text:
        challenge_cookie = _solve_acw_sc_v2_cookie(text)
        if challenge_cookie:
            return _fetch_url_once(url, referer=referer, cookie=challenge_cookie)
    return text


def _fetch_url_once(url: str, referer: str | None = None, cookie: str | None = None) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
        "Referer": referer or VJSHI_HOME,
    }
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(
        url,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        body = response.read()
        encoding = response.headers.get_content_charset() or "utf-8"
        content_encoding = response.headers.get("Content-Encoding", "")
    if "gzip" in content_encoding.lower() or body.startswith(b"\x1f\x8b"):
        body = gzip.decompress(body)
    return _decode_http_body(body, encoding)


def _decode_http_body(body: bytes, declared_encoding: str | None) -> str:
    encodings = []
    declared = (declared_encoding or "").strip().lower()
    if declared and declared not in {"iso-8859-1", "latin-1", "latin1"}:
        encodings.append(declared)
    encodings.extend(["utf-8", "gb18030", "gbk"])
    best_text = ""
    best_score = None
    for encoding in _unique_nonempty(encodings):
        try:
            text = body.decode(encoding, errors="strict")
        except UnicodeDecodeError:
            text = body.decode(encoding, errors="replace")
        score = _mojibake_score(text)
        if best_score is None or score < best_score:
            best_text = text
            best_score = score
    return best_text


def _mojibake_score(text: str) -> int:
    markers = ["�", "鏂", "鐢", "杞", "拌兘", "婧", "嚭琛", "鍔", "姹"]
    return sum(text.count(marker) for marker in markers)


def _has_vjshi_video_material_filter(url: str) -> bool:
    if not url:
        return False
    parsed = urllib.parse.urlparse(str(url))
    query = urllib.parse.parse_qs(parsed.query)
    return (
        query.get("categoryIdForSoftware", [""])[0] == VJSHI_VIDEO_MATERIAL_CATEGORY_ID
        and query.get("st", [""])[0].lower() == "y"
    )


def _solve_acw_sc_v2_cookie(html_source: str) -> str:
    arg1_match = re.search(r"arg1=['\"]([0-9a-fA-F]+)['\"]", html_source)
    pos_match = re.search(r"posList=\[([^\]]+)\]", html_source)
    if not arg1_match or not pos_match:
        return ""
    arg1 = arg1_match.group(1)
    pos_list = [int(item.strip(), 0) for item in pos_match.group(1).split(",") if item.strip()]
    mask = ""
    for token in re.findall(r"['\"]([A-Za-z0-9+/=]{12,})['\"]", html_source):
        try:
            decoded = base64.b64decode(token).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        if len(decoded) >= len(arg1) and re.fullmatch(r"[0-9a-fA-F]+", decoded):
            mask = decoded
            break
    if not mask or len(pos_list) < len(arg1):
        return ""
    reordered = [""] * len(pos_list)
    for index, char in enumerate(arg1):
        for pos_index, pos in enumerate(pos_list):
            if pos == index + 1:
                reordered[pos_index] = char
                break
    arg2 = "".join(reordered)
    output = []
    for index in range(0, min(len(arg2), len(mask)), 2):
        output.append(f"{int(arg2[index:index + 2], 16) ^ int(mask[index:index + 2], 16):02x}")
    value = "".join(output)
    return f"acw_sc__v2={value}" if value else ""


def _load_search_source(source_path: str | Path | None, pass_name: str) -> List[Dict[str, Any]]:
    if not source_path:
        return []
    data = json.loads(Path(source_path).read_text(encoding="utf-8-sig"))
    rows = []
    for item in _iter_source_items(data):
        if not isinstance(item, dict):
            continue
        html_source = item.get("html") or item.get("html_source") or item.get("page_html")
        keyword = str(item.get("search_keyword") or item.get("keyword") or item.get("query") or "")
        if html_source:
            rows.extend(
                parse_vjshi_search_results(
                    html_source,
                    keyword,
                    item.get("page_url") or item.get("source_url") or "",
                    pass_name,
                    item.get("sort_mode") or "source_json",
                    item.get("limit") or DEFAULT_FIRST_PASS_LIMIT,
                )
            )
            continue
        row = _normalize_source_search_item(item, pass_name)
        if row:
            rows.append(row)
    return rows


def _load_detail_source(
    source_path: str | Path | None,
    search_rows: Sequence[Dict[str, Any]],
    pass_name: str,
) -> List[Dict[str, Any]]:
    if not source_path:
        return []
    data = json.loads(Path(source_path).read_text(encoding="utf-8-sig"))
    base_by_id = {str(row.get("work_id")): row for row in search_rows if row.get("work_id")}
    details = []
    for item in _iter_source_items(data):
        if not isinstance(item, dict):
            continue
        if not _looks_like_detail_source_item(item):
            continue
        work_id = str(item.get("work_id") or _work_id_from_url(item.get("work_url") or item.get("page_url") or ""))
        base = {**base_by_id.get(work_id, {}), **item, "pass_name": pass_name}
        html_source = item.get("detail_html") or item.get("html") or item.get("html_source")
        details.append(parse_vjshi_work_detail(html_source, base) if html_source else _detail_from_search_row(base))
    return _dedupe_works(details)


def _iter_source_items(data: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
        return
    if not isinstance(data, dict):
        return
    for key in ["work_details", "details", "search_results", "items", "works", "nodes"]:
        for item in _as_list(data.get(key)):
            if isinstance(item, dict):
                yield item
    for page in _as_list(data.get("pages")):
        if not isinstance(page, dict):
            continue
        if page.get("html") or page.get("html_source") or page.get("page_html"):
            yield page
        for item in _as_list(page.get("items")) + _as_list(page.get("works")) + _as_list(page.get("nodes")):
            if isinstance(item, dict):
                merged = {**item}
                merged.setdefault("search_keyword", page.get("search_keyword") or page.get("keyword") or page.get("query"))
                merged.setdefault("source_url", page.get("page_url") or page.get("url"))
                yield merged


def _normalize_source_search_item(item: Dict[str, Any], pass_name: str) -> Dict[str, Any] | None:
    work_url = item.get("work_url") or item.get("page_url") or item.get("href") or item.get("url") or ""
    work_id = str(item.get("work_id") or _work_id_from_url(work_url))
    if not work_id and "/watch/" not in str(work_url):
        return None
    work_url = str(work_url) or f"https://www.vjshi.com/watch/{work_id}.html"
    if work_url.startswith("/"):
        work_url = urllib.parse.urljoin(VJSHI_HOME, work_url)
    return {
        "schema_version": "vjshi-search-result/v1",
        "source_platform": "vjshi",
        "pass_name": pass_name,
        "search_keyword": item.get("search_keyword") or item.get("keyword") or item.get("query") or "",
        "sort_mode": item.get("sort_mode") or "source_json",
        "rank": _first_int(item.get("rank")) or 0,
        "work_id": work_id or _work_id_from_url(work_url),
        "title": item.get("title") or item.get("name") or "",
        "work_url": work_url,
        "cover_url": item.get("cover_url") or item.get("image_url") or item.get("src") or "",
        "purchase_count": _first_int(item.get("purchase_count") or item.get("sales_count") or item.get("buy_count")),
        "download_count": _first_int(item.get("download_count")),
        "resolution": item.get("resolution") or "",
        "duration": item.get("duration") or "",
        "aigc_flag": bool(item.get("aigc_flag") or item.get("is_aigc")),
        "material_type": item.get("material_type") or item.get("素材类型") or "",
        "src_file_type": item.get("src_file_type") or item.get("srcFileType") or "",
        "video_material_filter": bool(item.get("video_material_filter"))
        or _has_vjshi_video_material_filter(str(item.get("source_search_url") or item.get("source_url") or "")),
        "material_scope": item.get("material_scope") or "",
        "risk_flags": _as_list(item.get("risk_flags")),
        "source_search_url": item.get("source_search_url") or item.get("source_url") or "",
        "captured_at": item.get("captured_at") or _now(),
    }


def _looks_like_detail_source_item(item: Dict[str, Any]) -> bool:
    detail_keys = {
        "detail_keywords",
        "keywords",
        "material_income",
        "upload_time",
        "preview_images",
        "preview_video_url",
        "detail_html",
    }
    return any(key in item for key in detail_keys)


def _detail_from_search_row(row: Dict[str, Any]) -> Dict[str, Any]:
    title = row.get("title") or ""
    detail_keywords = _unique_nonempty(_as_list(row.get("detail_keywords")) + _as_list(row.get("keywords")) + _tokenize_terms(title))
    detail = {
        "schema_version": "vjshi-work-detail/v1",
        "source_platform": "vjshi",
        "pass_name": row.get("pass_name", ""),
        "search_keyword": row.get("search_keyword", ""),
        "rank": row.get("rank"),
        "source_search_url": row.get("source_search_url", ""),
        "video_material_filter": bool(row.get("video_material_filter")) or _has_vjshi_video_material_filter(str(row.get("source_search_url") or "")),
        "material_scope": row.get("material_scope", ""),
        "work_id": str(row.get("work_id") or _work_id_from_url(row.get("work_url") or "")),
        "title": title,
        "work_url": row.get("work_url", ""),
        "cover_url": row.get("cover_url", ""),
        "purchase_count": _first_int(row.get("purchase_count")),
        "download_count": _first_int(row.get("download_count")),
        "resolution": row.get("resolution") or "",
        "duration": row.get("duration") or "",
        "aigc_flag": bool(row.get("aigc_flag")),
        "detail_keywords": detail_keywords,
        "material_income": _first_float(row.get("material_income")),
        "upload_time": row.get("upload_time") or "",
        "preview_images": _as_list(row.get("preview_images")) or ([row["cover_url"]] if row.get("cover_url") else []),
        "sample_video_url": row.get("sample_video_url") or "",
        "preview_video_url": row.get("preview_video_url") or "",
        "preview_video_source": row.get("preview_video_source") or "",
        "author": row.get("author") or "",
        "category": row.get("category") or "",
        "material_type": row.get("material_type") or "",
        "src_file_type": row.get("src_file_type") or "",
        "related_work_urls": _as_list(row.get("related_work_urls")),
        "risk_flags": _unique_nonempty(_as_list(row.get("risk_flags")) + _risk_flags_from_text(" ".join([title] + detail_keywords))),
        "captured_at": row.get("captured_at") or _now(),
    }
    detail["market_signal_score"] = _work_market_signal_score(detail)
    return detail


def _classify_terms(weighted_counter: Counter[str]) -> Dict[str, List[Dict[str, Any]]]:
    buckets: Dict[str, Counter[str]] = {
        "topic_terms": Counter(),
        "visual_terms": Counter(),
        "camera_terms": Counter(),
        "commercial_use_terms": Counter(),
    }
    for term, score in weighted_counter.items():
        if term in CAMERA_TERMS or any(token in term for token in CAMERA_TERMS):
            buckets["camera_terms"][term] = score
        elif term in COMMERCIAL_USE_TERMS or any(token in term for token in COMMERCIAL_USE_TERMS):
            buckets["commercial_use_terms"][term] = score
        elif term in VISUAL_TERMS or any(token in term for token in VISUAL_TERMS):
            buckets["visual_terms"][term] = score
        else:
            buckets["topic_terms"][term] = score
    return {
        key: [{"term": term, "weighted_score": round(score, 2)} for term, score in counter.most_common(30)]
        for key, counter in buckets.items()
    }


def _build_commercial_directions(
    topic: str,
    seed_keywords: Sequence[str],
    works: Sequence[Dict[str, Any]],
    classified_terms: Dict[str, List[Dict[str, Any]]],
    weighted_terms: Counter[str],
    use_market_signals: bool = True,
) -> List[Dict[str, Any]]:
    candidates = _direction_candidates(topic, seed_keywords, classified_terms, weighted_terms)
    directions = []
    for index, candidate in enumerate(candidates, start=1):
        evidence = _evidence_for_direction(candidate, works, use_market_signals=use_market_signals)
        market_signal = (
            _direction_market_signal(evidence, candidate)
            if use_market_signals
            else _direction_semantic_signal(evidence, candidate)
        )
        risk_score = _direction_risk_score(evidence, candidate)
        directions.append(
            {
                "direction_id": f"direction_{index:02d}",
                "direction_name": candidate["direction_name"],
                "buyer_search_prompts": candidate["buyer_search_prompts"],
                "evidence_work_ids": [str(work.get("work_id")) for work in evidence if work.get("work_id")],
                "market_signal_score": market_signal,
                "ai_generation_feasibility": candidate["ai_generation_feasibility"],
                "video_motion_potential": candidate["video_motion_potential"],
                "commercial_reuse_value": candidate["commercial_reuse_value"],
                "risk_score": risk_score,
                "recommended_shot_count": max(1, min(12, int(round(market_signal * 0.8)))),
                "prompt_guidance_for_image_generation": candidate["prompt_guidance_for_image_generation"],
                "source_evidence": _evidence_summary_rows(evidence),
                "risk_notes": candidate["risk_notes"] + _risk_notes_from_evidence(evidence),
                "keyword_basis": candidate["keyword_basis"],
            }
        )
    return directions


def _direction_candidates(
    topic: str,
    seed_keywords: Sequence[str],
    classified_terms: Dict[str, List[Dict[str, Any]]],
    weighted_terms: Counter[str],
) -> List[Dict[str, Any]]:
    topic_anchor = _topic_anchor(topic, seed_keywords)
    visual_terms = [item["term"] for item in classified_terms.get("visual_terms", [])]
    camera_terms = [item["term"] for item in classified_terms.get("camera_terms", [])]
    commercial_terms = [item["term"] for item in classified_terms.get("commercial_use_terms", [])]
    candidates: List[Dict[str, Any]] = []

    def has_any(tokens: Sequence[str]) -> bool:
        text = " ".join(list(weighted_terms.keys()) + [topic])
        return any(token in text for token in tokens)

    def context_has_any(tokens: Sequence[str]) -> bool:
        text = " ".join([topic] + list(seed_keywords))
        return any(token in text for token in tokens)

    data_driven_candidates = _data_driven_direction_candidates(
        topic,
        seed_keywords,
        classified_terms,
        weighted_terms,
    )
    if data_driven_candidates:
        return data_driven_candidates[:8]

    topic_is_business_signing = context_has_any(
        [
            "\u5546\u52a1\u7b7e\u7ea6",
            "\u5546\u52a1\u63e1\u624b",
            "\u7b7e\u7ea6",
            "\u7b7e\u7ea6\u6210\u529f",
            "\u5408\u4f5c\u7b7e\u7ea6",
            "\u5408\u4f5c\u63e1\u624b",
            "\u63e1\u624b",
            "\u6d3d\u8c08",
            "\u7b7e\u5b57",
            "\u7b7e\u7ea6\u4eea\u5f0f",
        ]
    )
    topic_is_science_lab = context_has_any(
        [
            "\u65b0\u6750\u6599",
            "\u79d1\u7814",
            "\u5b9e\u9a8c\u5ba4",
            "\u7814\u53d1",
            "\u5927\u5b66\u79d1\u7814",
            "\u79d1\u7814\u4eba\u5458",
            "\u79d1\u7814\u56e2\u961f",
            "\u6750\u6599\u5b9e\u9a8c\u5ba4",
        ]
    )
    topic_is_duanwu = context_has_any(
        [
            "\u7aef\u5348",
            "\u7aef\u5348\u8282",
            "\u7cbd\u5b50",
            "\u9f99\u821f",
            "\u8d5b\u9f99\u821f",
            "\u827e\u8349",
            "\u9999\u56ca",
            "\u7cbd\u53f6",
            "\u8282\u65e5\u793c\u76d2",
        ]
    )
    topic_is_shenzhen_city = context_has_any(
        [
            "\u6df1\u5733",
            "\u57ce\u5e02",
            "\u57ce\u5e02\u7d20\u6750",
            "\u57ce\u5e02\u5ba3\u4f20\u7247",
            "\u822a\u62cd",
            "\u5730\u6807",
            "CBD",
            "\u6e7e\u533a",
            "\u524d\u6d77",
            "\u798f\u7530",
            "\u5357\u5c71",
        ]
    )

    if topic_is_business_signing and has_any(
        [
            "\u5546\u52a1\u63e1\u624b",
            "\u7b7e\u7ea6",
            "\u7b7e\u7ea6\u6210\u529f",
            "\u5408\u4f5c\u63e1\u624b",
            "\u6210\u529f\u4eba\u58eb",
            "\u5408\u4f5c\u5171\u8d62",
        ]
    ):
        candidates.append(
            _direction(
                "\u5546\u52a1\u7b7e\u7ea6\u6210\u529f\u4e0e\u5408\u4f5c\u63e1\u624b",
                [
                    "\u5546\u52a1\u63e1\u624b",
                    "\u7b7e\u7ea6\u6210\u529f",
                    "\u5408\u4f5c\u7b7e\u7ea6 \u63e1\u624b",
                    "\u5546\u52a1\u4eba\u58eb \u5408\u4f5c\u63e1\u624b",
                ],
                [
                    "\u5546\u52a1\u63e1\u624b",
                    "\u5546\u52a1\u5408\u4f5c",
                    "\u7b7e\u7ea6",
                    "\u5408\u4f5c\u63e1\u624b",
                    "\u6210\u529f\u4eba\u58eb",
                    "\u5408\u4f5c\u5171\u8d62",
                ],
                "\u56f4\u7ed5\u7b7e\u7ea6\u5b8c\u6210\u540e\u7684\u63e1\u624b\u3001\u5fae\u7b11\u3001\u6587\u4ef6\u4ea4\u6362\u548c\u56e2\u961f\u5408\u5f71\uff0c\u9002\u5408\u4f01\u4e1a\u5ba3\u4f20\u7247\u3001\u91d1\u878d\u5408\u4f5c\u548c\u9879\u76ee\u8fbe\u6210\u53d9\u4e8b\u3002",
                9,
                8,
                10,
                [
                    "\u907f\u514d\u771f\u5b9e\u516c\u53f8 Logo\u3001\u5408\u540c\u53ef\u8bfb\u6587\u5b57\u3001\u5ba2\u6237\u8096\u50cf\u548c\u5e73\u53f0\u6c34\u5370\u3002"
                ],
            )
        )

    if topic_is_science_lab and has_any(
        [
            "\u65b0\u6750\u6599",
            "\u79d1\u7814",
            "\u5b9e\u9a8c\u5ba4",
            "\u7814\u53d1",
            "\u5927\u5b66\u79d1\u7814",
            "\u79d1\u7814\u4eba\u5458",
            "\u79d1\u7814\u56e2\u961f",
            "\u6750\u6599\u5b9e\u9a8c\u5ba4",
        ]
    ):
        candidates.append(
            _direction(
                "\u65b0\u6750\u6599\u79d1\u7814\u56e2\u961f\u4e0e\u5b9e\u9a8c\u5ba4\u7814\u53d1",
                [
                    "\u65b0\u6750\u6599 \u79d1\u7814 \u5b9e\u9a8c\u5ba4",
                    "\u5b9e\u9a8c\u5ba4 \u7814\u53d1\u56e2\u961f",
                    "\u5927\u5b66 \u79d1\u7814\u4eba\u5458 \u5b9e\u9a8c\u5ba4",
                    "\u6750\u6599\u5b9e\u9a8c\u5ba4 \u6d4b\u8bd5",
                ],
                [
                    "\u65b0\u6750\u6599",
                    "\u79d1\u7814",
                    "\u5b9e\u9a8c\u5ba4",
                    "\u7814\u53d1\u56e2\u961f",
                    "\u5927\u5b66\u79d1\u7814",
                    "\u79d1\u7814\u4eba\u5458",
                    "\u6750\u6599\u5b9e\u9a8c\u5ba4",
                    "\u6750\u6599\u6d4b\u8bd5",
                ],
                "\u767d\u5927\u8902\u6216\u5b9e\u9a8c\u670d\u79d1\u7814\u4eba\u5458\u5728\u73b0\u4ee3\u5b9e\u9a8c\u5ba4\u8fdb\u884c\u6750\u6599\u89c2\u5bdf\u3001\u4eea\u5668\u64cd\u4f5c\u3001\u6837\u54c1\u6d4b\u8bd5\u548c\u56e2\u961f\u8ba8\u8bba\uff0c\u9002\u5408\u9ad8\u6821\u79d1\u7814\u3001\u65b0\u6750\u6599\u4f01\u4e1a\u548c\u4ea7\u5b66\u7814\u5ba3\u4f20\u7247\u3002",
                8,
                8,
                9,
                [
                    "\u907f\u514d\u771f\u5b9e\u6821\u5fbd\u3001\u5b9e\u9a8c\u5ba4\u95e8\u724c\u3001\u4eea\u5668\u54c1\u724c Logo\u3001\u5c4f\u5e55\u53ef\u8bfb\u6570\u636e\u548c\u771f\u5b9e\u8bba\u6587\u6807\u9898\u3002"
                ],
            )
        )
    if topic_is_science_lab and has_any(
        [
            "\u4eea\u5668",
            "\u6d4b\u8bd5",
            "\u6837\u54c1",
            "\u6750\u6599",
            "\u663e\u5fae",
            "\u8bd5\u9a8c",
        ]
    ):
        candidates.append(
            _direction(
                "\u6750\u6599\u6d4b\u8bd5\u4eea\u5668\u64cd\u4f5c\u4e0e\u6837\u54c1\u89c2\u5bdf",
                [
                    "\u6750\u6599 \u5b9e\u9a8c \u4eea\u5668",
                    "\u79d1\u7814\u4eba\u5458 \u64cd\u4f5c\u4eea\u5668",
                    "\u5b9e\u9a8c\u5ba4 \u6837\u54c1 \u6d4b\u8bd5",
                    "\u65b0\u6750\u6599 \u663e\u5fae \u89c2\u5bdf",
                ],
                [
                    "\u6750\u6599",
                    "\u4eea\u5668",
                    "\u6d4b\u8bd5",
                    "\u6837\u54c1",
                    "\u663e\u5fae",
                    "\u5b9e\u9a8c",
                    "\u89c2\u5bdf",
                ],
                "\u7a81\u51fa\u79d1\u7814\u4eea\u5668\u3001\u6837\u54c1\u76d2\u3001\u663e\u5fae\u89c2\u5bdf\u3001\u6570\u636e\u8bb0\u5f55\u548c\u624b\u90e8\u64cd\u4f5c\u7ec6\u8282\uff0c\u53ef\u4f5c\u5ba3\u4f20\u7247\u4e2d\u7684\u7814\u53d1\u5b9e\u529b\u548c\u6280\u672f\u4fe1\u4efb\u955c\u5934\u3002",
                8,
                7,
                9,
                [
                    "\u4eea\u5668\u9762\u677f\u548c\u7535\u8111\u5c4f\u5e55\u4e0d\u8981\u6709\u53ef\u8bfb\u54c1\u724c\u6216\u771f\u5b9e\u6570\u636e\uff0c\u6837\u54c1\u6807\u7b7e\u9700\u62bd\u8c61\u5316\u3002"
                ],
            )
        )
    if topic_is_business_signing and has_any(
        [
            "\u7b7e\u5b57",
            "\u5546\u52a1\u4f1a\u8bae",
            "\u6218\u7565\u5408\u4f5c",
            "\u4f01\u4e1a\u7b7e\u7ea6",
            "\u5199\u5b57\u697c",
            "\u91d1\u878d\u6295\u8d44",
        ]
    ):
        candidates.append(
            _direction(
                "\u4f1a\u8bae\u5ba4\u7b7e\u5b57\u4e0e\u6218\u7565\u5408\u4f5c\u4eea\u5f0f",
                [
                    "\u5546\u52a1\u7b7e\u7ea6 \u7b7e\u5b57",
                    "\u4f01\u4e1a\u7b7e\u7ea6\u4eea\u5f0f",
                    "\u6218\u7565\u5408\u4f5c \u7b7e\u7ea6",
                    "\u4f1a\u8bae\u5ba4 \u7b7e\u5b57 \u5408\u4f5c",
                ],
                [
                    "\u7b7e\u5b57",
                    "\u5546\u52a1\u4f1a\u8bae",
                    "\u6218\u7565\u5408\u4f5c",
                    "\u4f01\u4e1a\u5ba3\u4f20\u7247",
                    "\u5199\u5b57\u697c",
                    "\u91d1\u878d\u6295\u8d44",
                ],
                "\u8868\u73b0\u4f1a\u8bae\u5ba4\u3001\u5408\u540c\u7b7e\u5b57\u3001\u63e1\u624b\u8fbe\u6210\u548c\u56e2\u961f\u89c1\u8bc1\uff0c\u53ef\u4f5c\u4f01\u4e1a\u5ba3\u4f20\u7247\u4e2d\u7684\u5173\u952e\u7ed3\u679c\u955c\u5934\u3002",
                8,
                7,
                9,
                [
                    "\u5408\u540c\u3001\u80cc\u677f\u548c\u5c4f\u5e55\u9700\u505a\u65e0\u54c1\u724c\u5316\uff0c\u4e0d\u8981\u751f\u6210\u5177\u4f53\u516c\u53f8\u540d\u79f0\u6216\u771f\u5b9e\u6761\u6b3e\u3002"
                ],
            )
        )
    if topic_is_business_signing and has_any(
        [
            "\u6d3d\u8c08",
            "\u9ad8\u7aef\u5546\u52a1",
            "\u5546\u52a1\u4eba\u58eb",
            "\u5546\u52a1\u4ea4\u6d41",
            "\u529e\u516c\u5ba4",
            "\u56e2\u961f\u5408\u4f5c",
        ]
    ):
        candidates.append(
            _direction(
                "\u9ad8\u7aef\u5546\u52a1\u6d3d\u8c08\u4e0e\u5408\u4f5c\u8fbe\u6210",
                [
                    "\u5546\u52a1\u6d3d\u8c08 \u5408\u4f5c",
                    "\u9ad8\u7aef\u5546\u52a1 \u6d3d\u8c08",
                    "\u5546\u52a1\u4eba\u58eb \u4f1a\u8bae\u6d3d\u8c08",
                    "\u5546\u52a1\u4ea4\u6d41 \u5199\u5b57\u697c",
                ],
                [
                    "\u6d3d\u8c08",
                    "\u9ad8\u7aef\u5546\u52a1",
                    "\u5546\u52a1\u4eba\u58eb",
                    "\u5546\u52a1\u4ea4\u6d41",
                    "\u5199\u5b57\u697c",
                    "\u529e\u516c\u5ba4",
                ],
                "\u4ee5\u9ad8\u7aef\u529e\u516c\u7a7a\u95f4\u3001\u81ea\u7136\u4ea4\u8c08\u3001\u5fae\u7b11\u70b9\u5934\u548c\u8fbe\u6210\u5171\u8bc6\u4e3a\u6838\u5fc3\uff0c\u8865\u8db3\u7b7e\u7ea6\u524d\u540e\u7684\u60c5\u7eea\u94fa\u57ab\u955c\u5934\u3002",
                8,
                8,
                8,
                [
                    "\u4eba\u7269\u8868\u60c5\u3001\u624b\u90e8\u548c\u5546\u52a1\u7740\u88c5\u8981\u81ea\u7136\uff0c\u907f\u514d\u5938\u5f20\u6446\u62cd\u548c\u53ef\u8bfb\u6587\u5b57\u9053\u5177\u3002"
                ],
            )
        )

    if topic_is_duanwu and has_any(["龙舟", "赛龙舟", "水花", "鼓手"]):
        candidates.append(
            _direction(
                "龙舟竞渡与团队拼搏",
                [f"{topic_anchor} 龙舟 航拍", "赛龙舟 水花 特写", f"{topic_anchor} 龙舟 鼓手", "龙舟 竞渡 慢动作"],
                ["龙舟", "赛龙舟", "水花", "鼓手", "航拍"],
                "写实江面龙舟竞渡、鼓手节奏、水花和队伍动作，避免真实赛事标识和可读文字。",
                8,
                10,
                8,
                ["真实赛事队名、横幅文字、运动员肖像需规避。"],
            )
        )
    if topic_is_duanwu and has_any(["粽子", "粽叶", "糯米", "蒸汽", "美食"]):
        candidates.append(
            _direction(
                "粽子产品与食物特写",
                [f"{topic_anchor} 粽子 特写", "粽子 蒸汽 特写", "粽叶 糯米 微距", f"{topic_anchor} 美食 静物"],
                ["粽子", "粽叶", "糯米", "蒸汽", "特写", "微距"],
                "无品牌粽子、粽叶纹理、蒸汽和食物质感，适合电商、节日活动、TVC 插入镜头。",
                9,
                7,
                10,
                ["品牌包装、礼盒文字、可读标签默认排除。"],
            )
        )
    if topic_is_duanwu and has_any(["包粽子", "手部", "家庭", "民俗"]):
        candidates.append(
            _direction(
                "家庭包粽子与民俗手作",
                [f"{topic_anchor} 包粽子 手部", "包粽子 家庭", f"{topic_anchor} 民俗 手作", "粽叶 手部 特写"],
                ["包粽子", "手部", "家庭", "民俗"],
                "中国家庭自然包粽子、手部动作和温暖节日关系，适合品牌情绪片与生活方式短视频。",
                7,
                8,
                8,
                ["人物手部和表情要自然，避免摆拍和夸张民俗服化。"],
            )
        )
    if topic_is_duanwu and has_any(["艾草", "香囊", "五彩绳", "习俗"]):
        candidates.append(
            _direction(
                "艾草香囊与端午习俗静物",
                [f"{topic_anchor} 艾草 香囊", "端午 香囊 特写", "艾草 门前 空镜", "五彩绳 手部"],
                ["艾草", "香囊", "五彩绳", "习俗", "静物"],
                "艾草、香囊、五彩绳等端午识别物，构成低风险无品牌节日空镜和转场素材。",
                9,
                6,
                7,
                ["香囊上的小字和图案不要复刻。"],
            )
        )
    if topic_is_duanwu and has_any(["礼盒", "电商", "广告", "促销"]):
        candidates.append(
            _direction(
                "无品牌礼盒与节日促销场景",
                [f"{topic_anchor} 礼盒 无品牌", "端午 礼盒 电商", "粽子 礼盒 广告", "节日 促销 背景"],
                ["礼盒", "电商", "广告", "促销", "无品牌"],
                "无品牌节日礼盒、干净背景和留白，可服务电商 KV、活动片头和促销短视频。",
                7,
                6,
                9,
                ["严禁真实品牌、包装文字、商标和可识别包装设计。"],
            )
        )
    if topic_is_shenzhen_city and has_any(["深圳", "深圳CBD", "福田", "南山", "罗湖", "城市天际线", "航拍"]):
        candidates.append(
            _direction(
                "深圳CBD天际线与城市航拍",
                ["深圳 城市天际线 航拍", "深圳 CBD 城市全景", "深圳 福田 南山 航拍", "深圳 宣传片 空镜"],
                ["深圳", "深圳CBD", "福田", "南山", "罗湖", "城市天际线", "航拍", "城市全景"],
                "写实深圳一线城市天际线、福田/南山 CBD、高楼与道路纵深，适合城市宣传片、企业片和湾区经济叙事。",
                8,
                9,
                10,
                ["真实楼体 Logo、楼顶标识、车牌和可读广告牌需要规避。"],
            )
        )
    if topic_is_shenzhen_city and has_any(["深圳湾", "前海", "超级总部", "总部基地", "人才公园", "粤港澳大湾区"]):
        candidates.append(
            _direction(
                "深圳湾前海与湾区总部经济",
                ["深圳湾 超级总部 航拍", "前海 深圳湾 延时", "粤港澳大湾区 深圳 航拍", "深圳 人才公园 天际线"],
                ["深圳湾", "前海", "超级总部", "总部基地", "人才公园", "粤港澳大湾区", "湾区经济"],
                "突出深圳湾、前海、超级总部基地、人才公园和湾区经济空间，画面要现代、干净、商务感强。",
                8,
                8,
                9,
                ["总部楼宇和真实企业标识需弱化或无品牌化。"],
            )
        )
    if topic_is_shenzhen_city and has_any(["夜景", "城市夜景", "万家灯火", "内透", "深夜cbd"]):
        candidates.append(
            _direction(
                "深圳夜景内透与万家灯火",
                ["深圳 夜景 航拍", "深圳 城市夜景 内透", "深圳 CBD 夜景", "深圳 万家灯火 延时"],
                ["深圳", "夜景", "城市夜景", "万家灯火", "内透", "CBD", "延时"],
                "深圳夜景、CBD 内透、道路车流与万家灯火，适合作为城市活力、科技感和片尾情绪镜头。",
                7,
                9,
                8,
                ["夜景广告牌和楼体文字容易出现可读文字，生图时需要虚化或无文字化。"],
            )
        )
    if topic_is_shenzhen_city and has_any(["地标", "深圳地标", "平安金融中心", "市民中心", "世界之窗", "大疆", "天空之城"]):
        candidates.append(
            _direction(
                "深圳地标与城市识别空镜",
                ["深圳 地标 航拍", "深圳 平安金融中心 航拍", "深圳 市民中心 延时", "深圳 城市宣传片 地标"],
                ["深圳地标", "地标", "平安金融中心", "市民中心", "世界之窗", "天空之城", "城市识别"],
                "用无品牌化方式提炼深圳地标识别度：高楼、广场、公园、城市道路和现代建筑群，不复刻具体商标文字。",
                6,
                8,
                8,
                ["具体地标存在可识别建筑和标识风险，只用于方向参考，生成时要做原创化城市综合体。"],
            )
        )
    if topic_is_shenzhen_city and has_any(["延时", "延时摄影", "日转夜", "云海", "朝霞", "晚霞"]):
        candidates.append(
            _direction(
                "深圳延时摄影与日转夜变化",
                ["深圳 延时摄影 日转夜", "深圳 云海 航拍", "深圳 朝霞 晚霞 城市", "深圳 车流 延时"],
                ["深圳", "延时", "延时摄影", "日转夜", "云海", "朝霞", "晚霞", "车流"],
                "城市日出、晚霞、云海、车流和日转夜变化，适合片头、转场和宏观城市发展叙事。",
                7,
                10,
                8,
                ["避免把多个时间段硬塞进单张图，静帧应表达一个明确瞬间和运动预期。"],
            )
        )

    if not candidates:
        visual_top = visual_terms[:4] or [topic_anchor]
        camera_top = camera_terms[:2] or ["特写", "全景"]
        commercial_top = commercial_terms[:2] or ["宣传片", "短视频"]
        for index, term in enumerate(visual_top[:4], start=1):
            prompts = _unique_nonempty(
                [
                    f"{topic_anchor} {term} {camera_top[0]}",
                    f"{term} {camera_top[-1]}",
                    f"{topic_anchor} {term} {commercial_top[0]}",
                ]
            )
            candidates.append(
                _direction(
                    f"{term}商业化素材方向",
                    prompts,
                    [term] + camera_top + commercial_top,
                    f"围绕 {term} 建立可商用、无品牌、可剪辑的 AI 视频素材画面。",
                    7,
                    7,
                    7,
                    ["需人工复查是否存在品牌、文字或平台水印。"],
                )
            )

    candidates = sorted(
        candidates,
        key=lambda item: sum(weighted_terms.get(term, 0) for term in item["keyword_basis"]),
        reverse=True,
    )
    return candidates[:8]


def _direction(
    name: str,
    prompts: Sequence[str],
    keyword_basis: Sequence[str],
    image_guidance: str,
    ai_feasibility: int,
    motion_potential: int,
    reuse_value: int,
    risk_notes: Sequence[str],
) -> Dict[str, Any]:
    cleaned_keywords = clean_visual_terms(keyword_basis)
    return {
        "direction_name": clean_visual_phrase(name, fallback=name),
        "buyer_search_prompts": clean_visual_terms(prompts, max_items=10),
        "keyword_basis": cleaned_keywords,
        "prompt_guidance_for_image_generation": image_guidance,
        "ai_generation_feasibility": ai_feasibility,
        "video_motion_potential": motion_potential,
        "commercial_reuse_value": reuse_value,
        "risk_notes": list(risk_notes),
    }


def _data_driven_direction_candidates(
    topic: str,
    seed_keywords: Sequence[str],
    classified_terms: Dict[str, List[Dict[str, Any]]],
    weighted_terms: Counter[str],
) -> List[Dict[str, Any]]:
    topic_domains = _topic_domains_for_text(" ".join([topic] + list(seed_keywords)))
    anchors = _data_driven_anchor_terms(topic, seed_keywords)
    relevant_terms = _data_driven_relevant_terms(weighted_terms, topic_domains, anchors)
    if not anchors:
        anchors = relevant_terms[:5]
    if not relevant_terms:
        relevant_terms = anchors

    camera_terms = [
        item["term"]
        for item in classified_terms.get("camera_terms", [])
        if _is_term_allowed_for_topic(item["term"], topic_domains)
    ][:3]
    commercial_terms = [
        item["term"]
        for item in classified_terms.get("commercial_use_terms", [])
        if _is_term_allowed_for_topic(item["term"], topic_domains)
    ][:3]
    candidates: List[Dict[str, Any]] = []
    for anchor in anchors[:5]:
        support_terms = [
            term
            for term in relevant_terms
            if term != anchor and term not in anchor and anchor not in term
        ][:6]
        if not support_terms:
            support_terms = [term for term in relevant_terms if term != anchor][:4]
        prompts = _buyer_prompts_from_terms(anchor, support_terms, camera_terms, commercial_terms, topic_domains)
        if not prompts:
            continue
        keyword_basis = _unique_nonempty([anchor, *support_terms, *camera_terms, *commercial_terms])
        candidates.append(
            _direction(
                f"{anchor}商业化素材方向",
                prompts,
                keyword_basis,
                f"基于第一轮作品标题、详情关键词和来源搜索词提炼：{anchor}；优先参考 {', '.join(keyword_basis[:6])} 等高相关画面元素，生成无品牌、可商用、适合宣传片剪辑的 AI 视频素材。",
                7,
                7,
                7,
                ["需人工复查是否存在品牌、真实机构标识、实验室门牌、屏幕可读文字或平台水印。"],
            )
        )
    return candidates


def _data_driven_anchor_terms(topic: str, seed_keywords: Sequence[str]) -> List[str]:
    anchors: List[str] = []
    for value in [*seed_keywords, clean_visual_phrase(topic)]:
        for term in _topic_anchor_terms(str(value)):
            if _is_generic_topic_anchor(term):
                continue
            anchors.append(term)
    anchors.sort(key=lambda item: (-len(item), item))
    return _unique_nonempty(anchors)[:8]


def _data_driven_relevant_terms(
    weighted_terms: Counter[str],
    topic_domains: set[str],
    anchors: Sequence[str],
) -> List[str]:
    anchor_text = " ".join(anchors)
    relevant: List[str] = []
    for term, _score in weighted_terms.most_common(160):
        clean_term = _clean_text(str(term))
        if not clean_term or _is_generic_topic_anchor(clean_term):
            continue
        if not _is_good_buyer_search_term(clean_term):
            continue
        if not _is_term_allowed_for_topic(clean_term, topic_domains):
            continue
        if anchors and not _term_matches_topic(clean_term, anchor_text, topic_domains):
            continue
        relevant.append(clean_term)
    return _unique_nonempty(relevant)[:24]


def _term_matches_topic(term: str, anchor_text: str, topic_domains: set[str]) -> bool:
    if term in anchor_text or any(anchor in term for anchor in _tokenize_terms(anchor_text)):
        return True
    if "science_lab" in topic_domains and any(
        marker in term
        for marker in ["科研", "实验", "实验室", "研发", "材料", "新材料", "大学", "研究", "仪器", "样品", "测试", "显微"]
    ):
        return True
    if "business_signing" in topic_domains and any(
        marker in term
        for marker in ["签约", "握手", "合作签约", "合作握手", "签字", "洽谈", "会议室"]
    ):
        return True
    if "duanwu_festival" in topic_domains and any(
        marker in term
        for marker in ["端午", "粽子", "粽叶", "龙舟", "艾草", "香囊", "五彩绳"]
    ):
        return True
    if "shenzhen_city" in topic_domains and any(
        marker in term
        for marker in ["深圳", "福田", "南山", "前海", "深圳湾", "城市", "地标", "航拍"]
    ):
        return True
    return False


def _buyer_prompts_from_terms(
    anchor: str,
    support_terms: Sequence[str],
    camera_terms: Sequence[str],
    commercial_terms: Sequence[str],
    topic_domains: set[str] | None = None,
) -> List[str]:
    prompts: List[str] = []
    anchor = clean_visual_phrase(anchor)
    topic_domains = topic_domains or set()
    if anchor:
        prompts.append(anchor)

    if "business_signing" in topic_domains:
        prompts.extend(_business_signing_expansion_prompts(anchor, support_terms))

    for term in support_terms[:4]:
        term = clean_visual_phrase(term)
        if not _is_good_buyer_search_term(term):
            continue
        prompts.append(f"{anchor} {term}")
    for term in camera_terms[:2]:
        term = clean_visual_phrase(term)
        if not term or term not in CAMERA_TERMS:
            continue
        prompts.append(f"{anchor} {term}")
    for term in commercial_terms[:1]:
        term = clean_visual_phrase(term)
        if not _is_good_buyer_search_term(term):
            continue
        prompts.append(f"{anchor} {term}")
    if not prompts and anchor:
        prompts.append(anchor)
    return clean_visual_terms(prompts, max_items=10)


def _business_signing_expansion_prompts(anchor: str, support_terms: Sequence[str]) -> List[str]:
    """Build second-pass prompts that broaden within business signing intent."""

    support_text = " ".join(clean_visual_phrase(term) for term in support_terms)
    has_signing = "签约" in anchor or "签字" in anchor or "签约" in support_text or "签字" in support_text
    has_handshake = "握手" in anchor or "握手" in support_text
    prompts = [
        "商务合作 握手",
        "合作签约",
        "商务洽谈 签约",
        "合同签约 握手",
        "高端商务 签约",
        "会议室 商务合作",
        "商务谈判 握手",
        "战略合作 签约",
        "合作共赢 握手",
        "签字 合同",
    ]
    if has_signing:
        prompts.extend(["签约握手", "签约成功", "商务签约"])
    if has_handshake:
        prompts.extend(["合作握手", "商务握手", "洽谈握手"])
    if anchor:
        prompts.extend([f"{anchor} 洽谈", f"{anchor} 会议室"])
    return [prompt for prompt in prompts if _is_good_buyer_search_term(prompt)]


def _topic_domains_for_text(text: str) -> set[str]:
    cleaned = _clean_text(text)
    return {
        domain
        for domain, markers in TOPIC_DOMAIN_MARKERS.items()
        if any(marker in cleaned for marker in markers)
    }


def _is_term_allowed_for_topic(term: str, topic_domains: set[str]) -> bool:
    for domain, tokens in OFF_TOPIC_DOMAIN_TOKENS.items():
        if domain in topic_domains:
            continue
        if any(token in term for token in tokens):
            return False
    return True


def _is_generic_topic_anchor(term: str) -> bool:
    cleaned = _clean_text(str(term))
    if cleaned in GENERIC_TOPIC_ANCHOR_TERMS or len(cleaned) < 2:
        return True
    if any(fragment in cleaned for fragment in GENERIC_TOPIC_ANCHOR_FRAGMENTS):
        has_specific_domain_marker = any(
            marker in cleaned
            for marker in [
                "新材料",
                "科研",
                "实验室",
                "研发",
                "大学科研",
                "材料",
                "端午",
                "龙舟",
                "粽子",
                "深圳",
                "签约",
                "握手",
            ]
        )
        if not has_specific_domain_marker:
            return True
    return False


def _is_good_buyer_search_term(term: str) -> bool:
    cleaned = _clean_text(str(term))
    if not cleaned or len(cleaned) > 12:
        return False
    if "宣传片" in cleaned or "素材" in cleaned:
        return False
    if re.search(r"[A-Za-z]{3,}", cleaned):
        return False
    if any(fragment in cleaned for fragment in ["阿莱", "拍摄高校", "专家教授", "键盘打字"]):
        return False
    return True


def _filter_topic_relevant_buyer_prompts(
    prompts: Sequence[Dict[str, Any]],
    topic: str,
    seed_keywords: Sequence[str],
    first_pass_details: Sequence[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    topic_profile = _topic_relevance_profile(topic, seed_keywords, first_pass_details)
    for item in prompts:
        decision = _buyer_prompt_topic_relevance(item, topic_profile)
        enriched = {**item, "topic_relevance": decision}
        if decision["accepted"]:
            accepted.append(enriched)
        else:
            rejected.append(enriched)
    return accepted, rejected


def _topic_relevance_profile(
    topic: str,
    seed_keywords: Sequence[str],
    first_pass_details: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    topic_text = _clean_text(" ".join([topic] + list(seed_keywords)))
    topic_domains = _topic_domains_for_text(topic_text)
    anchor_terms: set[str] = set()
    for value in [topic, *seed_keywords]:
        anchor_terms.update(_topic_anchor_terms(str(value)))
    for detail in first_pass_details:
        anchor_terms.update(_topic_anchor_terms(str(detail.get("search_keyword") or "")))
    anchor_terms = {
        term
        for term in anchor_terms
        if len(term) >= 2 and not _is_generic_topic_anchor(term) and _is_term_allowed_for_topic(term, topic_domains)
    }
    return {
        "topic": topic,
        "seed_keywords": list(seed_keywords),
        "topic_text": topic_text,
        "topic_domains": sorted(topic_domains),
        "anchor_terms": sorted(anchor_terms),
    }


def _topic_anchor_terms(text: str) -> set[str]:
    cleaned = clean_visual_phrase(_clean_text(text))
    terms = set(_tokenize_terms(cleaned))
    terms.update(part for part in re.split(r"[\s,，、/|]+", cleaned) if len(part) >= 2)
    for marker_group in TOPIC_DOMAIN_MARKERS.values():
        terms.update(marker for marker in marker_group if marker in cleaned)
    return {term for term in terms if not _is_generic_topic_anchor(term)}


def _buyer_prompt_topic_relevance(item: Dict[str, Any], topic_profile: Dict[str, Any]) -> Dict[str, Any]:
    prompt = _clean_text(str(item.get("prompt") or ""))
    direction_name = _clean_text(str(item.get("direction_name") or ""))
    text = f"{prompt} {direction_name}"
    topic_domains = set(topic_profile.get("topic_domains") or [])
    blocked_domains: List[str] = []
    for domain, tokens in OFF_TOPIC_DOMAIN_TOKENS.items():
        if domain in topic_domains:
            continue
        if any(token in text for token in tokens):
            blocked_domains.append(domain)
    if blocked_domains:
        return {
            "accepted": False,
            "score": 0,
            "matched_terms": [],
            "blocked_domains": blocked_domains,
            "reason": "提示词包含当前主题之外的领域词，已禁止进入第二轮搜索。",
        }

    anchor_terms = list(topic_profile.get("anchor_terms") or [])
    matched_terms = [term for term in anchor_terms if term and term in text]
    if not matched_terms:
        return {
            "accepted": False,
            "score": 0,
            "matched_terms": [],
            "blocked_domains": [],
            "reason": "提示词没有命中主题词、种子词或第一轮搜索词，已禁止进入第二轮搜索。",
        }
    score = min(10, 4 + len(matched_terms) * 2)
    return {
        "accepted": True,
        "score": score,
        "matched_terms": matched_terms[:8],
        "blocked_domains": [],
        "reason": "提示词命中当前主题锚点，允许进入第二轮搜索。",
    }


def _build_buyer_prompts(
    topic: str,
    directions: Sequence[Dict[str, Any]],
    works: Sequence[Dict[str, Any]],
    use_market_signals: bool = False,
) -> List[Dict[str, Any]]:
    prompts: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for direction in directions:
        for prompt in direction.get("buyer_search_prompts", []):
            clean_prompt = _clean_text(prompt)
            if not clean_prompt or clean_prompt in seen:
                continue
            seen.add(clean_prompt)
            evidence = _evidence_for_prompt(clean_prompt, works, direction, use_market_signals=use_market_signals)
            prompts.append(
                {
                    "prompt_id": f"buyer_prompt_{len(prompts) + 1:02d}",
                    "prompt": clean_prompt,
                    "topic": topic,
                    "direction_name": direction.get("direction_name", ""),
                    "evidence_work_ids": [str(work.get("work_id")) for work in evidence if work.get("work_id")],
                    "weighted_score": (
                        _prompt_weighted_score(clean_prompt, evidence, direction)
                        if use_market_signals
                        else _prompt_semantic_score(clean_prompt, evidence, direction)
                    ),
                    "market_signal_summary": (
                        _prompt_market_signal_summary(evidence)
                        if use_market_signals
                        else "第一轮语义候选：仅基于标题、详情关键词和来源搜索词，不使用购买量、销售额或点击量。"
                    ),
                    "commercial_use": _commercial_use_for_prompt(clean_prompt, direction),
                    "ai_generation_feasibility": direction.get("ai_generation_feasibility"),
                    "risk_notes": direction.get("risk_notes", []),
                    "used_in_second_pass": True,
                }
            )
    return prompts[:24]


def _attach_second_pass_counts(
    prompts: Sequence[Dict[str, Any]],
    second_search_results: Sequence[Dict[str, Any]],
    second_details: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    search_by_prompt: Counter[str] = Counter(str(row.get("search_keyword", "")) for row in second_search_results)
    detail_by_prompt: Counter[str] = Counter(str(row.get("search_keyword", "")) for row in second_details)
    output = []
    for prompt in prompts:
        item = dict(prompt)
        item["second_pass_search_result_count"] = search_by_prompt.get(str(prompt.get("prompt", "")), 0)
        item["second_pass_detail_count"] = detail_by_prompt.get(str(prompt.get("prompt", "")), 0)
        output.append(item)
    return output


def _attach_second_pass_evidence(
    directions: Sequence[Dict[str, Any]],
    second_details: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    output = []
    for direction in directions:
        item = dict(direction)
        prompts = set(item.get("buyer_search_prompts", []))
        matched = [
            work
            for work in second_details
            if work.get("search_keyword") in prompts or _work_matches_terms(work, item.get("keyword_basis", []))
        ]
        item["second_pass_evidence_work_ids"] = [str(work.get("work_id")) for work in matched if work.get("work_id")]
        if matched:
            item["market_signal_score"] = max(item.get("market_signal_score", 1), _direction_market_signal(matched, item))
            item["source_evidence"] = _evidence_summary_rows(_merge_evidence_by_id(item.get("source_evidence", []), matched))
        output.append(item)
    return output


def _build_market_mining_summary(
    topic: str,
    seed_keywords: Sequence[str],
    directions: Sequence[Dict[str, Any]],
    prompts: Sequence[Dict[str, Any]],
    keyword_analysis: Dict[str, Any],
    first_details: Sequence[Dict[str, Any]],
    second_details: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    source_notes = []
    shot_group_plan_seed = []
    for index, direction in enumerate(directions, start=1):
        source_notes.append(
            {
                "source_id": f"market_mining_{index:02d}",
                "source_type": "vjshi_keyword_reverse_mining",
                "title": direction["direction_name"],
                "url": VJSHI_HOME,
                "summary": (
                    f"光厂两轮反挖方向：{direction['direction_name']}；"
                    f"买家搜索提示词：{', '.join(direction.get('buyer_search_prompts', []))}。"
                ),
                "keywords": direction.get("keyword_basis", []),
                "representative_visuals": direction.get("buyer_search_prompts", []),
                "high_purchase_examples": [
                    row.get("title", "")
                    for row in direction.get("source_evidence", [])
                    if row.get("title")
                ],
                "purchase_count": direction.get("market_signal_score"),
                "avoid_notes": direction.get("risk_notes", []),
            }
        )
        shot_group_plan_seed.append(
            {
                "group_name": direction["direction_name"],
                "shot_count": direction["recommended_shot_count"],
                "reason": direction["prompt_guidance_for_image_generation"],
                "market_demand_score": direction["market_signal_score"],
                "ai_generation_feasibility": direction["ai_generation_feasibility"],
                "video_motion_potential": direction["video_motion_potential"],
                "commercial_reuse_value": direction["commercial_reuse_value"],
                "risk_score": direction["risk_score"],
                "market_basis": f"来自光厂作品证据：{', '.join(direction.get('evidence_work_ids', [])[:8])}",
                "buyer_use_cases": direction.get("buyer_search_prompts", []),
                "representative_scenes": direction.get("buyer_search_prompts", []),
                "core_elements": direction.get("keyword_basis", []),
                "creative_angles": direction.get("buyer_search_prompts", []),
                "avoid_patterns": direction.get("risk_notes", []),
                "evidence_keywords": direction.get("keyword_basis", []),
            }
        )
    return {
        "schema_version": "market-mining-summary/v1",
        "topic": topic,
        "platform_priority": ["vjshi"],
        "generated_at": _now(),
        "seed_keywords": list(seed_keywords),
        "first_pass_work_count": len(first_details),
        "second_pass_work_count": len(second_details),
        "buyer_search_prompts": list(prompts),
        "commercial_ai_directions": list(directions),
        "keyword_analysis_path_hint": "00_调研/市场反挖/关键词分析.json",
        "source_notes": source_notes,
        "visual_demand_matrix_inputs": shot_group_plan_seed,
        "shot_group_plan_seed": shot_group_plan_seed,
        "reference_gallery_policy": {
            "can_collect_public_previews": True,
            "never_download_paid_originals": True,
            "auto_exclude_image2_reference_flags": [
                "watermark_or_platform_badge",
                "readable_text",
                "multi_panel_preview",
                "brand_or_logo",
            ],
        },
        "second_pass_query_source": "买家搜索提示词.json",
        "top_weighted_terms": keyword_analysis.get("weighted_terms", [])[:30],
    }


def _ensure_operator_review(mining_dir: Path, project_dir: Path) -> Path:
    path = mining_dir / "人工审核.json"
    if path.exists():
        return path
    return write_json(
        path,
        {
            "schema_version": "operator-review/v1",
            "project_dir": str(project_dir),
            "updated_at": _now(),
            "review_labels": ["high_value", "evidence_only", "excluded", "image2_reference", "needs_recheck"],
            "work_reviews": {},
            "direction_reviews": {},
            "prompt_reviews": {},
            "asset_reviews": {},
            "notes": [],
        },
    )


def _post_research_next_step_commands(project_dir: Path) -> List[str]:
    project_arg = str(project_dir)
    return [
        f'python .\\run_mvp.py prepare-high-value-video-frame-queue --project-dir "{project_arg}" --max-works 30',
        f'python .\\run_mvp.py collect-high-value-video-frames --project-dir "{project_arg}" --initial-works 10 --min-total-frames 300 --max-works 30 --workers 6',
    ]


def _write_post_research_next_step(mining_dir: Path, project_dir: Path) -> Path:
    path = mining_dir / "后续动作确认.json"
    return write_json(
        path,
        {
            "schema_version": "post-research-next-step/v1",
            "project_dir": str(project_dir),
            "updated_at": _now(),
            "status": "pending_user_confirmation",
            "recommended_action": "ask_user_before_collect_high_value_video_frames",
            "question": POST_RESEARCH_NEXT_STEP_QUESTION,
            "confirmation_required": True,
            "default_if_user_does_not_confirm": "skip_video_preview_collection",
            "commands_if_confirmed": _post_research_next_step_commands(project_dir),
            "expected_outputs_if_confirmed": [
                "00_调研/视频参考帧/高价值视频拆帧队列.json",
                "00_调研/视频参考帧/视频参考帧清单.json",
                "00_调研/视频参考帧/视频参考帧总览.jpg",
            ],
            "usage_policy": {
                "source_scope": "public_preview_videos_only",
                "never_download_paid_originals": True,
                "frames_are_reference_only": True,
                "not_final_delivery_or_commercial_assets": True,
                "must_be_selected_by_user_in_electron_before_binding": True,
                "scene_sampling_policy": "one_representative_frame_per_detected_scene",
                "supplement_policy": "if initial 10 works produce fewer than 300 frames, keep adding high-value works until at least 300 frames or 30 works total; do not use dense per-second sampling just to inflate count",
            },
            "cost_and_storage_notes": [
                "采集公开视频和拆帧会产生网络请求、本地文件和处理耗时。",
                "未获得用户确认前不要自动运行 prepare-high-value-video-frame-queue 或 collect-high-value-video-frames。",
            ],
        },
    )


def _write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> Path:
    ensure_dir(path.parent)
    content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text((content + "\n") if content else "", encoding="utf-8")
    return path


def _normalize_seed_keywords(seed_keywords: Sequence[str] | str | None) -> List[str]:
    if seed_keywords is None:
        return []
    if isinstance(seed_keywords, str):
        parts = re.split(r"[,，;\n|]+", seed_keywords)
    else:
        parts = list(seed_keywords)
    return _unique_nonempty(_clean_text(str(item)) for item in parts)[:5]


def _normalize_html_source(html_source: str) -> str:
    source = str(html_source or "")
    source = source.replace("\\/", "/")
    source = source.replace("\\u002F", "/")
    try:
        source = bytes(source, "utf-8").decode("unicode_escape") if "\\u" in source else source
    except UnicodeError:
        pass
    return html_lib.unescape(source)


def _extract_image_urls(source: str) -> List[str]:
    patterns = [
        r"https?://[^\"'<>\\\s]+?\.(?:jpg|jpeg|png|webp)(?:\?[^\"'<>\\\s]*)?",
        r"//[^\"'<>\\\s]*pic\.vjshi\.com[^\"'<>\\\s]+?\.(?:jpg|jpeg|png|webp)(?:\?[^\"'<>\\\s]*)?",
    ]
    urls: List[str] = []
    for pattern in patterns:
        for item in re.findall(pattern, source, flags=re.I):
            url = item if item.startswith("http") else f"https:{item}"
            if "avatar" in url.lower() or "logo" in url.lower():
                continue
            urls.append(url)
    return _unique_nonempty(urls)


def _extract_video_url(source: str) -> str:
    match = re.search(r"https?://[^\"'<>\\\s]+?\.(?:mp4|m3u8)(?:\?[^\"'<>\\\s]*)?", source, flags=re.I)
    return match.group(0) if match else ""


def _extract_sample_video_url(source: str) -> str:
    sample_window = re.search(r"(?:sample|小样)[^\"'<>]{0,240}(https?://[^\"'<>\\\s]+?\.(?:mp4|m3u8)(?:\?[^\"'<>\\\s]*)?)", source, flags=re.I)
    if sample_window:
        return sample_window.group(1)
    key_window = re.search(
        r"(?:sampleVideoUrl|sampleUrl|sample_video_url)[\"']?\s*[:=]\s*[\"']([^\"']+\.(?:mp4|m3u8)[^\"']*)[\"']",
        source,
        flags=re.I,
    )
    return key_window.group(1) if key_window else ""


def _extract_src_file_type(source: str) -> str:
    for pattern in [
        r"srcFileType[\"']?\s*[:=]\s*[\"']([A-Z_]+)[\"']",
        r"[\"']srcFileType[\"']\s*,\s*[\"']([A-Z_]+)[\"']",
        r"src_file_type[\"']?\s*[:=]\s*[\"']([A-Z_]+)[\"']",
    ]:
        match = re.search(pattern, source, flags=re.I)
        if match:
            return match.group(1).upper()
    return ""


def _material_type_from_src_file_type(src_file_type: str) -> str:
    mapping = {
        "VIDEO": "视频素材",
        "TEMPLATE": "模板素材",
        "PACKAGE": "包装/工程包",
        "PPT": "PPT模板",
    }
    return mapping.get(str(src_file_type or "").upper(), "")


def _extract_video_object(source: str) -> Dict[str, Any]:
    for block in re.findall(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        source,
        flags=re.I | re.S,
    ):
        try:
            data = json.loads(html_lib.unescape(block).strip())
        except json.JSONDecodeError:
            continue
        for item in _as_list(data):
            if isinstance(item, dict) and item.get("@type") == "VideoObject":
                return item
    return {}


def _extract_material_detail_fields(source: str) -> Dict[str, str]:
    text = _clean_text(_strip_tags(source))
    start = text.find("素材详情")
    if start < 0:
        return {}
    end_candidates = [text.find(marker, start + 1) for marker in ["素材配乐", "相似推荐", "相关推荐"]]
    end_candidates = [item for item in end_candidates if item > start]
    section = text[start : min(end_candidates) if end_candidates else start + 2000]
    labels = ["素材标题", "素材编号", "素材类型", "透明通道", "无缝循环", "AIGC说明", "文件大小", "上传日期", "点击", "购买"]
    fields: Dict[str, str] = {}
    for index, label in enumerate(labels):
        label_pos = section.find(label)
        if label_pos < 0:
            continue
        value_start = label_pos + len(label)
        next_positions = [section.find(item, value_start) for item in labels[index + 1 :] if section.find(item, value_start) >= 0]
        value_end = min(next_positions) if next_positions else len(section)
        value = section[value_start:value_end].strip()
        if value:
            fields[label] = value
    return fields


def _clean_video_title(value: str) -> str:
    cleaned = _clean_text(value)
    cleaned = re.sub(r"[_-]?视频素材下载.*$", "", cleaned).strip()
    return cleaned


def _date_from_iso(value: str) -> str:
    match = re.match(r"(20\d{2}-\d{1,2}-\d{1,2})", value)
    return match.group(1) if match else ""


def _format_iso_duration(value: str) -> str:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return ""
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    total_seconds = hours * 3600 + minutes * 60 + seconds
    if total_seconds <= 0:
        return ""
    if total_seconds % 60 == 0:
        return f"{total_seconds // 60}分钟"
    return f"{total_seconds // 60}:{total_seconds % 60:02d}"


def _json_ld_author(video_object: Dict[str, Any]) -> str:
    author = video_object.get("author")
    if isinstance(author, dict):
        return str(author.get("name") or "")
    return str(author or "")


def _json_ld_interaction_count(video_object: Dict[str, Any]) -> int | None:
    statistic = video_object.get("interactionStatistic")
    if isinstance(statistic, dict):
        return _first_int(statistic.get("userInteractionCount"))
    return None


def _extract_preview_note(text: str) -> str:
    match = re.search(r"(\d+分\d+秒以前为快速预览，后面为正常速度。)", text)
    return match.group(1) if match else ""


def _extract_title(source: str, fallback: str) -> str:
    candidates = []
    for pattern in [
        r"<title[^>]*>(.*?)</title>",
        r"(?:alt|title|aria-label)=[\"']([^\"']{3,120})[\"']",
        r"<h1[^>]*>(.*?)</h1>",
        r"<h2[^>]*>(.*?)</h2>",
    ]:
        candidates.extend(re.findall(pattern, source, flags=re.I | re.S))
    for candidate in candidates:
        cleaned = _clean_text(_strip_tags(candidate))
        cleaned = re.sub(r"[-_]?视频素材.*$", "", cleaned).strip()
        if cleaned and len(cleaned) >= 2:
            return cleaned[:120]
    return fallback


def _extract_count(source: str, labels: Sequence[str]) -> int | None:
    counts = []
    for label in labels:
        for match in re.finditer(rf"(\d{{1,8}})\s*{re.escape(label)}", source):
            counts.append(int(match.group(1)))
        for match in re.finditer(rf"{re.escape(label)}\D{{0,8}}(\d{{1,8}})", source):
            counts.append(int(match.group(1)))
    return max(counts) if counts else None


def _extract_download_count(source: str) -> int | None:
    for candidate in [source, html_lib.unescape(source)]:
        for pattern in [
            r'\\*"downloadTimes\\*"\s*[:,]\s*(\d{1,8})',
            r'["\']downloadTimes["\']\s*[:,]\s*(\d{1,8})',
        ]:
            match = re.search(pattern, candidate)
            if match:
                return int(match.group(1))

    text = _clean_text(_strip_tags(source))
    counts = []
    patterns = [
        r"(\d{1,8})\s*(?:次)?\s*下载(?!后|小样|素材|包|，|,|、|。)",
        r"下载(?:次数|量)?[:：\s]{0,4}(\d{1,8})(?!\d)(?!\s*[PpKk])\s*(?:次)?",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            counts.append(int(match.group(1)))
    return max(counts) if counts else None


def _has_download_times_marker(source: str) -> bool:
    return "downloadTimes" in source or "downloadTimes" in html_lib.unescape(source)


def _extract_resolution(source: str) -> str:
    match = re.search(r"\b(8K|6K|4K|2K|1080P|720P|HD|FHD|UHD)\b", source, flags=re.I)
    return match.group(1).upper() if match else ""


def _extract_duration(source: str) -> str:
    for pattern in [r"\b\d{1,2}:\d{2}(?::\d{2})?\b", r"\b\d{1,3}\s*秒\b", r"\b\d{1,3}'\d{1,2}\"?\b"]:
        match = re.search(pattern, source)
        if match:
            return match.group(0)
    return ""


def _has_aigc_flag(source: str) -> bool:
    lowered = source.lower()
    return any(token in lowered for token in ["aigc", "ai生成", "ai 生成", "ai视频", "ai 视频"])


def _extract_money(source: str) -> float | None:
    text = _clean_text(_strip_tags(source))
    matches: List[float] = []
    label_pattern = r"素材收入"
    money_after_label_patterns = [
        rf"{label_pattern}\D{{0,12}}(?:￥|¥)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(万元|万|元)?",
        rf"{label_pattern}\D{{0,12}}([0-9][0-9,]*(?:\.[0-9]+)?)\s*(万元|万|元)",
    ]

    for pattern in money_after_label_patterns:
        for number, unit in re.findall(pattern, text):
            value = _money_to_number(number, unit)
            if value is not None:
                matches.append(value)

    for label_match in re.finditer(label_pattern, text):
        prefix = text[max(0, label_match.start() - 180) : label_match.start()]
        amount_matches = list(re.finditer(r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(万元|万|元)", prefix))
        if not amount_matches:
            continue
        nearest = amount_matches[-1]
        context = prefix[max(0, nearest.start() - 8) : nearest.end()]
        if "30天收入" in context or "近30天" in context or "作者收入" in context:
            continue
        value = _money_to_number(nearest.group(1), nearest.group(2))
        if value is not None:
            matches.append(value)
    return matches[0] if matches else None


def _money_to_number(number: str, unit: str = "") -> float | None:
    try:
        value = float(str(number).replace(",", ""))
    except ValueError:
        return None
    if unit in {"万", "万元"}:
        value *= 10000
    return value


def _extract_date(source: str) -> str:
    match = re.search(r"(20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?)", source)
    return match.group(1).replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-") if match else ""


def _extract_labeled_text(source: str, labels: Sequence[str]) -> str:
    text = _clean_text(_strip_tags(source))
    for label in labels:
        match = re.search(rf"{re.escape(label)}[:：\s]{{0,4}}([A-Za-z0-9_\-\u4e00-\u9fff]{{2,40}})", text)
        if match:
            return match.group(1).strip()
    return ""


def _extract_detail_keywords(source: str, title: str) -> List[str]:
    keywords: List[str] = []
    for pattern in [
        r"<meta[^>]+name=[\"']keywords[\"'][^>]+content=[\"']([^\"']+)[\"']",
        r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+name=[\"']keywords[\"']",
        r"(?:关键词|标签|素材关键词)[:：]\s*([^<]{2,220})",
    ]:
        for match in re.findall(pattern, source, flags=re.I | re.S):
            keywords.extend(re.split(r"[,，;；、\s]+", _clean_text(match)))
    keywords.extend(_tokenize_terms(title))
    return _unique_nonempty(keyword for keyword in keywords if len(keyword) >= 2)[:60]


def _risk_flags_from_text(text: str) -> List[str]:
    lowered = str(text).lower()
    flags = []
    for flag, terms in RISK_KEYWORDS.items():
        if any(term.lower() in lowered for term in terms):
            flags.append(flag)
    return flags


def _work_terms(work: Dict[str, Any]) -> List[str]:
    text_parts = [
        work.get("title", ""),
        work.get("search_keyword", ""),
        work.get("category", ""),
        work.get("material_type", ""),
        work.get("src_file_type", ""),
        " ".join(str(item) for item in _as_list(work.get("detail_keywords"))),
    ]
    terms = []
    for value in text_parts:
        terms.extend(_tokenize_terms(str(value)))
    terms.extend(str(item).strip() for item in _as_list(work.get("detail_keywords")))
    return _unique_nonempty(term for term in terms if len(term) >= 2 and not term.isdigit())[:80]


def _tokenize_terms(text: str) -> List[str]:
    cleaned = _clean_text(text)
    raw_parts = re.split(r"[,，;；、\s/|_\-]+", cleaned)
    terms: List[str] = []
    for part in raw_parts:
        part = part.strip()
        if len(part) >= 2:
            terms.append(part)
    for match in re.findall(r"[\u4e00-\u9fff]{2,8}", cleaned):
        if len(match) <= 8:
            terms.append(match)
    for match in re.findall(r"[A-Za-z][A-Za-z0-9+]{1,20}", cleaned):
        terms.append(match)
    stopwords = {"视频", "素材", "高清", "下载", "模板", "背景", "版权", "原创", "拍摄", "合集"}
    return _unique_nonempty(term for term in terms if term not in stopwords)


def _work_market_signal_score(work: Dict[str, Any]) -> int:
    purchases = _first_int(work.get("purchase_count")) or 0
    downloads = _first_int(work.get("download_count")) or 0
    income = _first_float(work.get("material_income")) or 0.0
    score = 1 + min(5, purchases // 20) + min(3, downloads // 50) + min(3, int(income // 100))
    if work.get("preview_video_url"):
        score += 1
    if work.get("aigc_flag"):
        score += 1
    return max(1, min(10, int(score)))


def _direction_market_signal(evidence: Sequence[Dict[str, Any]], candidate: Dict[str, Any]) -> int:
    if not evidence:
        basis_bonus = min(4, len(candidate.get("keyword_basis", [])))
        return max(1, min(10, 2 + basis_bonus))
    average = sum(_work_market_signal_score(work) for work in evidence) / max(1, len(evidence))
    coverage_bonus = min(2, len(evidence) // 3)
    return max(1, min(10, int(round(average + coverage_bonus))))


def _direction_semantic_signal(evidence: Sequence[Dict[str, Any]], candidate: Dict[str, Any]) -> int:
    basis_bonus = min(3, len(candidate.get("keyword_basis", [])) // 2)
    evidence_bonus = min(4, len(evidence))
    return max(1, min(10, 2 + basis_bonus + evidence_bonus))


def _direction_risk_score(evidence: Sequence[Dict[str, Any]], candidate: Dict[str, Any]) -> int:
    flags = []
    for work in evidence:
        flags.extend(_as_list(work.get("risk_flags")))
    base = len(set(flags)) + len(candidate.get("risk_notes", [])) // 2
    return max(1, min(10, 2 + base))


def _evidence_for_direction(
    candidate: Dict[str, Any],
    works: Sequence[Dict[str, Any]],
    use_market_signals: bool = True,
) -> List[Dict[str, Any]]:
    terms = candidate.get("keyword_basis", [])
    matched = [work for work in works if _work_matches_terms(work, terms)]
    if use_market_signals:
        return sorted(matched, key=_work_market_signal_score, reverse=True)[:12]
    return matched[:12]


def _evidence_for_prompt(
    prompt: str,
    works: Sequence[Dict[str, Any]],
    direction: Dict[str, Any],
    use_market_signals: bool = True,
) -> List[Dict[str, Any]]:
    terms = _tokenize_terms(prompt) + direction.get("keyword_basis", [])
    return _evidence_for_direction({"keyword_basis": terms}, works, use_market_signals=use_market_signals)[:8]


def _work_matches_terms(work: Dict[str, Any], terms: Sequence[str]) -> bool:
    text = " ".join(
        [
            str(work.get("title", "")),
            str(work.get("search_keyword", "")),
            " ".join(str(item) for item in _as_list(work.get("detail_keywords"))),
        ]
    )
    return any(term and term in text for term in terms)


def _evidence_summary_rows(evidence: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for work in evidence[:12]:
        if not isinstance(work, dict):
            continue
        rows.append(
            {
                "work_id": str(work.get("work_id", "")),
                "title": work.get("title", ""),
                "work_url": work.get("work_url", ""),
                "search_keyword": work.get("search_keyword", ""),
                "purchase_count": work.get("purchase_count"),
                "download_count": work.get("download_count"),
                "material_income": work.get("material_income"),
                "market_signal_score": _work_market_signal_score(work),
                "risk_flags": _as_list(work.get("risk_flags")),
            }
        )
    return rows


def _merge_evidence_by_id(existing_rows: Sequence[Dict[str, Any]], new_works: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for row in existing_rows:
        if isinstance(row, dict):
            merged[str(row.get("work_id", ""))] = row
    for work in new_works:
        if isinstance(work, dict):
            merged[str(work.get("work_id", ""))] = work
    return list(merged.values())


def _risk_notes_from_evidence(evidence: Sequence[Dict[str, Any]]) -> List[str]:
    flags = _unique_nonempty(flag for work in evidence for flag in _as_list(work.get("risk_flags")))
    notes = []
    if "watermark_or_platform_badge" in flags:
        notes.append("存在平台角标/水印迹象，只能作市场证据，不能自动进入图生图参考。")
    if "readable_text" in flags:
        notes.append("包含可读文字风险，生图时需要重构为无文字画面。")
    if "multi_panel_preview" in flags:
        notes.append("多宫格或合集预览不适合作为单张图生图参考。")
    if "brand_or_logo" in flags:
        notes.append("品牌或 Logo 风险，需要无品牌化。")
    return notes


def _prompt_weighted_score(prompt: str, evidence: Sequence[Dict[str, Any]], direction: Dict[str, Any]) -> float:
    term_bonus = len(_tokenize_terms(prompt)) * 0.5
    evidence_score = sum(_work_market_signal_score(work) for work in evidence) / max(1, len(evidence))
    direction_score = float(direction.get("market_signal_score") or 5)
    return round(min(10.0, max(1.0, evidence_score * 0.45 + direction_score * 0.35 + term_bonus)), 2)


def _prompt_semantic_score(prompt: str, evidence: Sequence[Dict[str, Any]], direction: Dict[str, Any]) -> float:
    prompt_terms = _tokenize_terms(prompt)
    basis_terms = set(direction.get("keyword_basis", []))
    term_overlap = sum(1 for term in prompt_terms if term in basis_terms)
    evidence_bonus = min(4, len(evidence)) * 0.7
    term_bonus = min(4, len(prompt_terms)) * 0.5 + term_overlap * 0.4
    return round(min(10.0, max(1.0, 1.5 + evidence_bonus + term_bonus)), 2)


def _prompt_market_signal_summary(evidence: Sequence[Dict[str, Any]]) -> str:
    if not evidence:
        return "来自方向关键词组合，暂无第二轮作品证据。"
    purchase_total = sum(_first_int(work.get("purchase_count")) or 0 for work in evidence)
    income_total = sum(_first_float(work.get("material_income")) or 0 for work in evidence)
    return f"命中 {len(evidence)} 个作品，购买量合计 {purchase_total}，可见收入信号合计 {round(income_total, 2)}。"


def _commercial_use_for_prompt(prompt: str, direction: Dict[str, Any]) -> List[str]:
    text = f"{prompt} {direction.get('direction_name', '')}"
    uses = []
    if any(term in text for term in ["礼盒", "电商", "促销"]):
        uses.extend(["电商活动", "节日促销"])
    if any(term in text for term in ["龙舟", "竞渡", "航拍"]):
        uses.extend(["节日宣传片", "城市文旅"])
    if any(term in text for term in ["粽子", "美食", "蒸汽"]):
        uses.extend(["食品广告", "TVC 插入镜头"])
    if any(term in text for term in ["家庭", "手部", "民俗"]):
        uses.extend(["品牌情绪片", "生活方式短视频"])
    return _unique_nonempty(uses or ["商业视频素材检索"])


def _counter_rows(counter: Counter[str], term_work_ids: Dict[str, set[str]]) -> List[Dict[str, Any]]:
    return [
        {"term": term, "count": count, "work_ids": sorted(term_work_ids.get(term, set()))[:12]}
        for term, count in counter.most_common(120)
    ]


def _weighted_term_rows(counter: Counter[str], term_work_ids: Dict[str, set[str]]) -> List[Dict[str, Any]]:
    return [
        {"term": term, "weighted_score": round(score, 2), "work_ids": sorted(term_work_ids.get(term, set()))[:12]}
        for term, score in counter.most_common(120)
    ]


def _topic_anchor(topic: str, seed_keywords: Sequence[str]) -> str:
    for seed in seed_keywords:
        if seed and len(seed) <= 8:
            return seed
    tokens = _tokenize_terms(topic)
    return tokens[0] if tokens else topic[:8]


def _dedupe_works(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    by_key: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        work_id = str(row.get("work_id") or _work_id_from_url(row.get("work_url") or ""))
        key = work_id or str(row.get("work_url") or row.get("title") or len(output))
        normalized = {**row}
        if work_id:
            normalized["work_id"] = work_id
        _attach_dedupe_trace(normalized, row)
        if key in by_key:
            existing = by_key[key]
            _merge_dedupe_trace(existing, row)
            existing["duplicate_search_count"] = int(existing.get("duplicate_search_count") or 1) + 1
            continue
        normalized["duplicate_search_count"] = 1
        by_key[key] = normalized
        output.append(normalized)
    return output


def _attach_dedupe_trace(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    keyword = str(source.get("search_keyword") or "").strip()
    if keyword:
        target["matched_search_keywords"] = _unique_nonempty(
            [*target.get("matched_search_keywords", []), keyword]
        )
    search_url = str(source.get("source_search_url") or "").strip()
    if search_url:
        target["source_search_urls"] = _unique_nonempty([*target.get("source_search_urls", []), search_url])
    rank = source.get("rank")
    if rank not in (None, ""):
        ranks = list(target.get("source_ranks", []))
        ranks.append({"search_keyword": keyword, "rank": rank})
        target["source_ranks"] = ranks


def _merge_dedupe_trace(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    _attach_dedupe_trace(target, source)


def _work_id_from_url(url: str) -> str:
    match = re.search(r"/watch/(\d+)\.html", str(url))
    return match.group(1) if match else ""


def _first_match(source: str, pattern: str) -> str:
    match = re.search(pattern, source)
    return match.group(1) if match else ""


def _first_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"\d+", value.replace(",", ""))
        if match:
            return int(match.group(0))
    return None


def _first_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"\d+(?:\.\d+)?", value.replace(",", ""))
        if match:
            return float(match.group(0))
    return None


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value or "")


def _clean_text(value: str) -> str:
    text = html_lib.unescape(str(value or ""))
    text = _repair_mojibake(text)
    text = re.sub(r"\s+", " ", text.replace("\u3000", " ")).strip()
    return text


def _repair_mojibake(value: str) -> str:
    if not value or not any("\u00c0" <= char <= "\u00ff" for char in value):
        return value
    try:
        repaired = value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value
    original_cjk = sum("\u4e00" <= char <= "\u9fff" for char in value)
    repaired_cjk = sum("\u4e00" <= char <= "\u9fff" for char in repaired)
    return repaired if repaired_cjk > original_cjk else value


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _unique_nonempty(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(str(value))
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
