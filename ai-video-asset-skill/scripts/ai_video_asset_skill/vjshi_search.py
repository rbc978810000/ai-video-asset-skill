"""VJShi keyword/search-result collection helpers."""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List

from .file_manager import write_json
from .market_mining import _fetch_url, _now, parse_vjshi_search_results


def build_vjshi_keyword_search_url(keyword: str, video_material_only: bool = True) -> str:
    params = {"wd": keyword}
    if video_material_only:
        params.update({"categoryIdForSoftware": "230", "st": "y"})
    return f"https://www.vjshi.com/so?{urllib.parse.urlencode(params)}"


def fetch_vjshi_search_results(
    keyword: str = "",
    search_url: str = "",
    limit: int = 80,
    output_jsonl: str | Path | None = None,
    output_json: str | Path | None = None,
    video_material_only: bool = True,
) -> Dict[str, Any]:
    """Fetch one VJShi search page and return normalized work-result rows."""

    if not keyword and not search_url:
        raise ValueError("keyword or search_url is required")
    source_url = search_url or build_vjshi_keyword_search_url(keyword, video_material_only=video_material_only)
    search_keyword = keyword or _keyword_from_url(source_url)
    html_source = _fetch_url(source_url)
    rows = parse_vjshi_search_results(
        html_source,
        search_keyword,
        source_url,
        pass_name="search_results",
        sort_mode="platform_default",
        limit=limit,
    )
    payload = {
        "schema_version": "vjshi-search-results/v1",
        "source_platform": "vjshi",
        "search_keyword": search_keyword,
        "source_search_url": source_url,
        "video_material_only": video_material_only,
        "result_count": len(rows),
        "generated_at": _now(),
        "results": rows,
        "work_urls": [row["work_url"] for row in rows if row.get("work_url")],
    }
    if output_jsonl:
        _write_jsonl(Path(output_jsonl), rows)
    if output_json:
        write_json(Path(output_json), payload)
    return payload


def _keyword_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    for key in ["wd", "fwd", "keyword", "q"]:
        if query.get(key):
            return query[key][0]
    return ""


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
