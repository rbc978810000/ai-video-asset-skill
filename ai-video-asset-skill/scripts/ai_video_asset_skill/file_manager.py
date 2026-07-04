"""Filesystem helpers for project creation and artifact persistence."""

from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


WINDOWS_FORBIDDEN_CHARS = r'<>:"/\|?*'

INPUT_DIR_NAME = "00_输入"
RESEARCH_DIR_NAME = "00_调研"
STORYBOARD_DIR_NAME = "01_分镜"
PROMPT_DIR_NAME = "02_生图提示词"
IMAGE_DIR_NAME = "03_图片"
VARIATION_DIR_NAME = "04_扩展角度"
REVIEW_DIR_NAME = "05_审核"
EXPORT_DIR_NAME = "06_导出"

PROJECT_MANIFEST_FILE = "项目清单.json"
TOPIC_BRIEF_FILE = "选题简报.md"
STYLE_BIBLE_FILE = "风格设定.json"

MARKET_MINING_DIR_NAME = "市场反挖"
REFERENCE_ASSETS_DIR_NAME = "参考图"
VIDEO_REFERENCE_DIR_NAME = "视频参考帧"
SELECTED_REFERENCE_DIR_NAME = "精选参考帧"

CURRENT_IMAGE_FILE = "当前图.png"
REVIEW_FILE = "审核记录.json"


def artifact_id(value: str) -> str:
    if value.startswith("shot_"):
        return f"镜头_{value.removeprefix('shot_')}"
    if value.startswith("scene_"):
        return f"场景_{value.removeprefix('scene_')}"
    return slug_text(value, max_length=72)


def shot_json_file(shot_id: str) -> str:
    return f"{artifact_id(shot_id)}.json"


def prompt_json_file(shot_id: str) -> str:
    return f"{artifact_id(shot_id)}_生图提示词.json"


def slug_text(value: str, max_length: int = 72) -> str:
    """Return a filename-safe slug while preserving readable Chinese text."""

    cleaned = "".join("_" if char in WINDOWS_FORBIDDEN_CHARS else char for char in value)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned[:max_length].strip("._") or "untitled"


def ensure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_json(path: str | Path, data: Any) -> Path:
    output_path = Path(path)
    ensure_dir(output_path.parent)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text(path: str | Path, content: str) -> Path:
    output_path = Path(path)
    ensure_dir(output_path.parent)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def write_csv(path: str | Path, rows: Iterable[Dict[str, Any]], fieldnames: List[str]) -> Path:
    output_path = Path(path)
    ensure_dir(output_path.parent)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
    return output_path


def copy_file(source: str | Path, destination: str | Path) -> Path:
    source_path = Path(source)
    destination_path = Path(destination)
    ensure_dir(destination_path.parent)
    shutil.copy2(source_path, destination_path)
    return destination_path


def relative_path(path: str | Path, base_dir: str | Path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(base_dir).resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def find_existing_project_dir(
    output_root: str | Path,
    topic: str,
    created_at: datetime | None = None,
    industry: str | None = None,
) -> Path | None:
    timestamp = created_at or datetime.now()
    date_part = timestamp.strftime("%Y-%m-%d")
    topic_slug = slug_text(str(topic), max_length=48)
    industry_slug = slug_text(str(industry or ""), max_length=24) if industry else ""
    root = Path(output_root)
    if not root.exists():
        return None

    candidates: List[Path] = []
    for child in root.iterdir():
        if not child.is_dir() or not child.name.startswith(date_part):
            continue
        name_matches_topic = bool(topic_slug and topic_slug in child.name)
        name_matches_industry = not industry_slug or industry_slug in child.name
        if name_matches_topic and name_matches_industry:
            candidates.append(child)
            continue

        manifest_path = child / PROJECT_MANIFEST_FILE
        if not manifest_path.exists():
            continue
        try:
            manifest = read_json(manifest_path)
        except (OSError, json.JSONDecodeError):
            continue
        manifest_topic = slug_text(
            str(manifest.get("topic") or manifest.get("project_title") or ""),
            max_length=48,
        )
        manifest_industry = slug_text(str(manifest.get("industry_name") or ""), max_length=24)
        if manifest_topic == topic_slug and (not industry_slug or not manifest_industry or manifest_industry == industry_slug):
            candidates.append(child)

    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def create_project_dirs(user_input: Dict[str, Any], created_at: datetime | None = None) -> Dict[str, Path]:
    timestamp = created_at or datetime.now()
    date_part = timestamp.strftime("%Y-%m-%d")
    industry = slug_text(str(user_input["user_input_industry_name"]), max_length=24)
    topic = slug_text(str(user_input["user_input_topic_title"]), max_length=48)
    output_root = ensure_dir(user_input["user_input_output_root_dir"])
    base_name = f"{date_part}_{industry}_{topic}"

    project_dir = find_existing_project_dir(
        output_root,
        str(user_input["user_input_topic_title"]),
        created_at=timestamp,
        industry=str(user_input["user_input_industry_name"]),
    )
    if not project_dir:
        project_dir = output_root / base_name

    dirs = {
        "project_dir": project_dir,
        "input_dir": project_dir / INPUT_DIR_NAME,
        "research_dir": project_dir / RESEARCH_DIR_NAME,
        "storyboard_dir": project_dir / STORYBOARD_DIR_NAME,
        "prompt_dir": project_dir / PROMPT_DIR_NAME,
        "image_dir": project_dir / IMAGE_DIR_NAME,
        "variation_dir": project_dir / VARIATION_DIR_NAME,
        "review_dir": project_dir / REVIEW_DIR_NAME,
        "export_dir": project_dir / EXPORT_DIR_NAME,
    }
    for directory in dirs.values():
        ensure_dir(directory)
    return dirs


def init_review_files(review_dir: str | Path) -> None:
    review_path = Path(review_dir)
    write_json(review_path / "失败队列.json", [])
    write_json(review_path / "重试记录.json", [])
    write_json(review_path / "通过清单.json", [])
    write_json(review_path / "替换记录.json", [])


def append_json_list(path: str | Path, item: Dict[str, Any]) -> List[Dict[str, Any]]:
    file_path = Path(path)
    current = read_json(file_path) if file_path.exists() else []
    current.append(item)
    write_json(file_path, current)
    return current


def next_image_version_path(shot_image_dir: str | Path) -> Path:
    directory = ensure_dir(shot_image_dir)
    version = 1
    while (directory / f"版本{version}.png").exists():
        version += 1
    return directory / f"版本{version}.png"
