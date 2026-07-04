"""主题前期调研计划生成模块。"""

from __future__ import annotations

import urllib.parse
from typing import Any, Dict, List


ALLOWED_RESEARCH_SOURCES = [
    {
        "name": "光厂/VJShi",
        "domains": ["vjshi.com"],
        "tier": "domestic_primary",
    },
    {
        "name": "新片场素材",
        "domains": ["stock.xinpianchang.com"],
        "tier": "domestic_primary",
    },
    {
        "name": "视觉中国 VCG",
        "domains": ["vcg.com"],
        "tier": "domestic_primary",
    },
    {
        "name": "Pond5",
        "domains": ["pond5.com"],
        "tier": "overseas_primary",
    },
    {
        "name": "Shutterstock Video",
        "domains": ["shutterstock.com"],
        "tier": "overseas_primary",
    },
    {
        "name": "Adobe Stock Video",
        "domains": ["stock.adobe.com"],
        "tier": "overseas_primary",
    },
    {
        "name": "Getty Images Creative Video",
        "domains": ["gettyimages.com"],
        "tier": "overseas_primary",
    },
    {
        "name": "iStock Footage",
        "domains": ["istockphoto.com"],
        "tier": "overseas_primary",
    },
    {
        "name": "Artgrid",
        "domains": ["artgrid.io"],
        "tier": "overseas_cinematic",
    },
    {
        "name": "Filmsupply",
        "domains": ["filmsupply.com"],
        "tier": "overseas_cinematic",
    },
    {
        "name": "Dissolve",
        "domains": ["dissolve.com"],
        "tier": "overseas_cinematic",
    },
]

BLOCKED_RESEARCH_DOMAINS = [
    "699pic.com",
    "ibaotu.com",
    "58pic.com",
    "135editor.com",
    "stock.tuchong.com",
    "storyblocks.com",
    "motionarray.com",
    "envato.com",
    "elements.envato.com",
]


def build_research_plan(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """生成联网调研计划和搜索词，不直接抓取网页。"""

    topic = user_input["user_input_topic_title"]
    industry = user_input["user_input_industry_name"]
    usages = " ".join(user_input.get("user_input_target_usage", []))
    visual_style = user_input.get("user_input_visual_style", "")
    seed_keywords = _topic_keywords(topic, industry, visual_style)

    query_templates = [
        ("国内主力素材市场", "{topic} {industry} site:vjshi.com 最多购买 视频素材"),
        ("国内主力素材市场", "{topic} {industry} site:stock.xinpianchang.com 正版视频素材"),
        ("国内主力素材市场", "{topic} {industry} site:vcg.com 视频素材"),
        ("国外主力素材市场", "{topic} {industry} stock footage site:pond5.com"),
        ("国外主力素材市场", "{topic} {industry} stock footage site:shutterstock.com/video"),
        ("国外主力素材市场", "{topic} {industry} stock footage site:stock.adobe.com/video"),
        ("国外高端影像参考", "{topic} {industry} creative video site:gettyimages.com"),
        ("国外高端影像参考", "{topic} {industry} footage site:artgrid.io OR site:filmsupply.com OR site:dissolve.com"),
    ]
    search_queries = []
    for index, (purpose, template) in enumerate(query_templates, start=1):
        search_queries.append(
            {
                "query_id": f"query_{index:02d}",
                "purpose": purpose,
                "query": template.format(topic=topic, industry=industry, usages=usages).strip(),
                "expected_findings": [
                    "素材标题、标签、搜索关键词和相关关键词",
                    "可见购买量、热门排序、下载量或平台推荐信号",
                    "封面/预览图中的高频画面模块、构图、景别和主体",
                    "需要避免的品牌、文字、水印、同质化和廉价模板感画面",
                ],
            }
        )

    return {
        "topic_title": topic,
        "industry_name": industry,
        "target_usage": user_input.get("user_input_target_usage", []),
        "visual_style": visual_style,
        "seed_keywords": seed_keywords,
        "allowed_research_sources": ALLOWED_RESEARCH_SOURCES,
        "blocked_research_domains": BLOCKED_RESEARCH_DOMAINS,
        "search_queries": search_queries,
        "research_instructions": [
            "调研只能使用白名单素材交易/授权平台：光厂/VJShi、新片场素材、视觉中国 VCG、Pond5、Shutterstock Video、Adobe Stock Video、Getty Images Creative Video、iStock Footage、Artgrid、Filmsupply、Dissolve。",
            "光厂/VJShi、新片场素材、VCG、Pond5、Shutterstock、Adobe Stock、Getty/iStock 是方向判断主来源；Artgrid、Filmsupply、Dissolve 只作高端镜头语言补充。",
            "禁止使用白名单外网页做方向调研；摄图网、包图网、千图网、图虫创意、135editor、公众号排版站、教程站、SEO聚合页、Storyblocks、Motion Array、Envato/Envato Elements 不得进入 source_notes、market_signal_map 或 visual_demand_matrix。",
            "优先记录可见购买量、热门排序、下载量、标题、标签、详情页相关关键词、封面/预览图 URL 和可借鉴画面模块。",
            "只提取画面类型、构图规律、技术场景和素材需求，不复制具体图片或品牌设计。",
            "如果主题很新或资料少，只能在白名单平台内扩大到相邻行业和相邻用途，并标记为推断。",
        ],
    }


def build_research_brief_markdown(research_plan: Dict[str, Any]) -> str:
    lines = [
        f"# {research_plan['topic_title']} 前期调研计划",
        "",
        f"- 行业：{research_plan['industry_name']}",
        f"- 用途：{', '.join(research_plan['target_usage'])}",
        f"- 视觉风格：{research_plan['visual_style']}",
        f"- 种子关键词：{', '.join(research_plan['seed_keywords'])}",
        "",
        "## 调研要求",
        "",
    ]
    lines.extend(f"- {item}" for item in research_plan["research_instructions"])
    lines.extend(["", "## 允许调研来源", ""])
    for source in research_plan["allowed_research_sources"]:
        lines.append(f"- {source['name']}：{', '.join(source['domains'])}（{source['tier']}）")
    lines.extend(["", "## 禁止来源", ""])
    lines.append(f"- {', '.join(research_plan['blocked_research_domains'])}")
    lines.extend(["", "## 建议搜索词", ""])
    for query in research_plan["search_queries"]:
        lines.append(f"- [{query['purpose']}] {query['query']}")
    return "\n".join(lines) + "\n"


def normalize_source_notes(raw_notes: Any) -> List[Dict[str, Any]]:
    """把外部调研笔记整理成稳定列表。"""

    if not raw_notes:
        return []
    if isinstance(raw_notes, dict):
        notes = raw_notes.get("source_notes") or raw_notes.get("sources") or raw_notes.get("notes") or []
    else:
        notes = raw_notes
    normalized = []
    if not isinstance(notes, list):
        return normalized
    for index, note in enumerate(notes, start=1):
        if not isinstance(note, dict):
            continue
        url = note.get("url", "")
        source_match = _allowed_source_for_url(url)
        if not source_match:
            continue
        normalized_note = {
            "source_id": note.get("source_id", f"source_{index:02d}"),
            "source_type": note.get("source_type", "未分类资料"),
            "source_quality": source_match["tier"],
            "source_platform": source_match["name"],
            "url": url,
            "title": note.get("title", ""),
            "summary": note.get("summary", ""),
            "representative_visuals": note.get("representative_visuals", []),
            "keywords": note.get("keywords", []),
            "avoid_notes": note.get("avoid_notes", []),
        }
        for optional_key in [
            "search_result_count",
            "purchase_count",
            "download_count",
            "related_keywords",
            "high_purchase_examples",
            "market_signal",
        ]:
            if optional_key in note:
                normalized_note[optional_key] = note[optional_key]
        normalized.append(normalized_note)
    return normalized


def _allowed_source_for_url(url: str) -> Dict[str, str] | None:
    domain = _domain_from_url(url)
    if not domain:
        return None
    if any(_domain_matches(domain, blocked) for blocked in BLOCKED_RESEARCH_DOMAINS):
        return None
    for source in ALLOWED_RESEARCH_SOURCES:
        if any(_domain_matches(domain, allowed) for allowed in source["domains"]):
            return {"name": source["name"], "tier": source["tier"]}
    return None


def _domain_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url if "://" in url else f"https://{url}")
    return parsed.netloc.lower().removeprefix("www.")


def _domain_matches(domain: str, rule: str) -> bool:
    normalized_rule = rule.lower().removeprefix("www.")
    return domain == normalized_rule or domain.endswith(f".{normalized_rule}")


def _topic_keywords(topic: str, industry: str, visual_style: str) -> List[str]:
    base_keywords = [industry, topic]
    keyword_bank = [
        "智能工厂",
        "工业4.0",
        "机械臂",
        "自动化产线",
        "数字孪生",
        "工业大脑",
        "AGV",
        "质检",
        "工程师",
        "控制室",
        "展会大屏",
        "商业视频素材",
    ]
    joined = f"{topic} {industry} {visual_style}"
    for keyword in keyword_bank:
        if keyword in joined or len(base_keywords) < 12:
            base_keywords.append(keyword)
    return list(dict.fromkeys(base_keywords))
