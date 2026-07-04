"""Default configuration for the AI video asset MVP."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .production_text import clean_visual_phrase

SKILL_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = str(SKILL_ROOT / "output")

DEFAULT_SKILL_INPUT: Dict[str, Any] = {
    "user_input_topic_title": "制造业智能工厂AI视频素材",
    "user_input_industry_name": "制造业",
    "user_input_total_shots": 80,
    "user_input_duration_seconds": 0,
    "user_input_target_usage": ["宣传片", "展会", "活动视频", "TVC", "预告片"],
    "user_input_visual_style": "高端科技工业风，真实摄影质感，现代智能工厂，蓝银色调，干净整洁，企业宣传片级别",
    "user_input_aspect_ratio": "16:9",
    "user_input_needs_voiceover": False,
    "user_input_needs_subtitles": False,
    "user_input_output_root_dir": DEFAULT_OUTPUT_ROOT,
    "user_input_generate_images": True,
    "user_input_max_retry": 3,
    "user_input_copy_space_required": False,
    "user_input_need_no_text": True,
    "user_input_need_no_logo": True,
    "user_input_people_region_priority": "中国人、中国工程师、中国企业场景",
    "user_input_allow_contextual_large_chinese_text": True,
    "user_input_image_provider": "codex_image2",
    "user_input_market_reference_assets_path": "",
    "user_input_market_mining_summary_path": "",
}

DEFAULT_STYLE_BIBLE: Dict[str, Any] = {
    "style_id": "smart_factory_premium_001",
    "industry": "制造业",
    "main_visual_style": "真实摄影质感，高端科技工业风，现代智能工厂，蓝银色调，干净整洁，企业宣传片级别",
    "color_palette": ["深蓝", "银灰", "冷白", "金属灰"],
    "lighting_style": "明亮干净的工业灯光，柔和体积光，局部蓝色科技光效",
    "camera_language": "电影感构图，稳定运镜，宽幅画面，适合企业宣传片和展会大屏",
    "factory_environment": "现代化智能工厂，高挑空间，整洁地面，机械臂，自动化产线，AGV小车，工业数据大屏",
    "people_style": "以中国人、中国工程师、中国企业员工为主，专业工装或商务工装，干净利落，真实自然，不夸张摆拍",
    "cultural_context": "中国制造业、中国智能工厂、中国企业宣传片语境，人物面孔、工作服、空间气质和场景细节优先贴合中国市场。",
    "equipment_style": "高端自动化设备，机械臂，精密检测设备，数字化控制台，智能传感器",
    "text_policy": {
        "default_no_text": True,
        "allow_contextual_large_chinese_text_when_necessary": True,
        "allowed_text_examples": ["车间安全标识", "设备区域标识", "展会大屏标题", "控制室区域提示"],
        "text_requirements": "默认不要文字；只有画面语义必要时才允许出现少量贴合场景的大号清晰中文；文字必须边缘清晰、不要太小，避免后续生视频时模糊、乱码或畸形。",
        "forbidden_text": ["小字", "密集文字", "乱码", "品牌名", "Logo文字", "水印", "无意义中英文", "屏幕上可读的真实数据"],
    },
    "commercial_rules": {
        "no_logo": True,
        "no_brand_name": True,
        "no_text": True,
        "no_watermark": True,
        "copy_space_required": False,
        "avoid_messy_background": True,
        "avoid_low_quality_machinery": True,
    },
    "negative_constraints": [
        "商标标志",
        "品牌名称",
        "水印",
        "随机文字",
        "小字",
        "密集文字",
        "乱码文字",
        "不贴合场景的文字",
        "过小的中文",
        "过小的英文",
        "脏乱车间",
        "肮脏工厂",
        "畸形手部",
        "变形机械结构",
        "卡通风格",
        "低清晰度",
        "廉价塑料质感",
    ],
}

DEFAULT_SHOT_GROUPS: List[Tuple[str, int]] = [
    ("片头与制造强国氛围", 6),
    ("智能工厂全景与车间秩序", 8),
    ("自动化生产线与机械臂", 12),
    ("AI质检与质量追溯", 8),
    ("工业大脑数字孪生与中控室", 8),
    ("精密制造电子车间与半导体", 8),
    ("新能源汽车与高端装备", 7),
    ("AGV仓储物流与柔性供应链", 6),
    ("工程师研发与人机协同", 8),
    ("绿色制造储能与低碳工厂", 4),
    ("未来制造收尾与完整背景", 5),
]

DIRECT_USE_COMPOSITION_SEQUENCE = [
    "画面完整充实，主体和环境都可直接用于剪辑",
    "主体居中稳定，前中后景完整，边缘细节自然",
    "宽幅构图饱满，空间纵深清楚，背景服务主体不空泛",
    "画面边缘有真实环境细节，整体信息完整",
    "主体、动作、设备和场景信息完整，适合直接作为视频素材使用",
    "上下左右都有真实环境层次和工业信息，画面不是单纯标题背景",
]

SHOT_SIZE_SEQUENCE = [
    "全景",
    "中远景",
    "中景",
    "特写",
    "微距特写",
    "低机位全景",
    "俯拍视角",
    "侧面视角",
]

CAMERA_MOVEMENT_SEQUENCE = [
    "缓慢推进的运镜感",
    "稳定横移跟拍的运镜感",
    "轻微下降的升降镜头感",
    "静态高级产品镜头感",
    "缓慢推近的镜头感",
    "轻微环绕的镜头感",
]

VALID_STATUSES = {
    "pending",
    "prompt_created",
    "generating",
    "generated",
    "reviewing",
    "approved",
    "needs_regeneration",
    "manual_review",
    "failed",
}


def merge_input(user_input: Dict[str, Any] | None) -> Dict[str, Any]:
    """合并用户输入和默认配置，不修改调用方对象。"""

    merged = deepcopy(DEFAULT_SKILL_INPUT)
    supplied = user_input or {}
    if user_input:
        for key, value in user_input.items():
            if value is not None:
                merged[key] = value
    if "user_input_duration_seconds" in supplied and "user_input_total_shots" not in supplied:
        duration = _positive_int(supplied.get("user_input_duration_seconds"))
        if duration:
            merged["user_input_total_shots"] = derive_shot_count_from_duration(duration)
    return merged


def derive_shot_count_from_duration(duration_seconds: int | float) -> int:
    """Estimate a sellable stock-video shot count from duration when the user does not specify one."""

    seconds = max(1, float(duration_seconds))
    return max(6, min(120, int((seconds + 2.49) // 2.5)))


def _positive_int(value: Any) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


def build_style_bible(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """根据当前选题创建风格圣经。"""

    style_bible = deepcopy(DEFAULT_STYLE_BIBLE)
    topic_text = (
        f"{user_input.get('user_input_topic_title', '')} "
        f"{user_input.get('user_input_industry_name', '')} "
        f"{user_input.get('user_input_visual_style', '')}"
    )
    style_bible["industry"] = user_input["user_input_industry_name"]
    style_bible["main_visual_style"] = user_input["user_input_visual_style"]
    if any(keyword in topic_text for keyword in ["中秋", "月饼", "团圆", "赏月", "灯笼", "桂花"]):
        style_bible.update(
            {
                "style_id": "mid_autumn_tvc_premium_001",
                "color_palette": ["暖金", "月白", "深蓝夜色", "桂花橙", "中国红点缀"],
                "lighting_style": "TVC广告级电影布光，暖金月光，柔和室内暖光，灯笼散景，高级饱和色彩但不过曝",
                "camera_language": "高级商业广告镜头语言，稳定运镜，浅景深产品特写，宽幅节日建立镜头，适合TVC和品牌节日短片",
                "factory_environment": "中国中秋节日场景，现代中国家庭、城市夜景、江南屋檐、庭院桂花、月饼茶席、灯笼街巷和高端礼盒静物",
                "environment_style": "中国中秋节日场景，现代中国家庭、城市夜景、江南屋檐、庭院桂花、月饼茶席、灯笼街巷和高端礼盒静物",
                "equipment_style": "高端月饼礼盒、中国茶具、纸灯笼、桂花枝、木质桌面、窗边月光、节日餐桌和东方美学道具",
                "cultural_context": "中国中秋节、中国家庭团圆、中国城市生活和中国品牌节日广告语境，人物面孔、服饰、空间和节日细节优先贴合中国市场。",
                "negative_constraints": [
                    "商标标志",
                    "品牌名称",
                    "水印",
                    "随机文字",
                    "小字",
                    "密集文字",
                    "乱码文字",
                    "不贴合场景的文字",
                    "过小的中文",
                    "过小的英文",
                    "廉价大月亮贴图",
                    "过度卡通",
                    "低幼插画",
                    "过度仙侠",
                    "廉价红金堆砌",
                    "过曝灯笼",
                    "拥挤杂乱人群",
                    "餐桌脏乱",
                    "畸形手部",
                    "人物五官异常",
                    "月饼纹样乱码",
                    "包装小字",
                    "品牌包装",
                    "低清晰度",
                    "廉价塑料质感",
                ],
            }
        )
    elif any(keyword in topic_text for keyword in ["实验室", "科研", "新材料", "研发团队", "科研人员", "材料实验"]):
        style_bible.update(
            {
                "style_id": "research_lab_premium_001",
                "color_palette": ["冷白", "浅灰", "银灰", "少量蓝色科技光"],
                "lighting_style": "明亮干净的实验室灯光，柔和冷白光，少量蓝色科技辅助光，真实克制",
                "camera_language": "真实商业摄影镜头语言，稳定运镜，干净实验室空间，适合科研宣传片和商业素材剪辑",
                "factory_environment": "现代高校或企业联合实验室，实验台、精密仪器、材料样品、显微镜、试管和干净玻璃隔断",
                "environment_style": "现代高校或企业联合实验室，实验台、精密仪器、材料样品、显微镜、试管和干净玻璃隔断",
                "equipment_style": "材料测试仪器、显微镜、实验台、样品盒、夹具、试管、无品牌电脑和科研记录板",
                "cultural_context": "中国科研团队、中国高校实验室和中国新材料企业研发语境，人物、空间和设备细节贴合本次调研方向。",
                "negative_constraints": [
                    "商标标志",
                    "品牌名称",
                    "水印",
                    "随机文字",
                    "小字",
                    "密集文字",
                    "乱码文字",
                    "真实机构标识",
                    "实验室门牌",
                    "可读屏幕文字",
                    "真实姓名工牌",
                    "医疗广告感",
                    "脏乱实验台",
                    "危险化学符号",
                    "畸形手部",
                    "人物五官异常",
                    "低清晰度",
                    "卡通风格",
                    "廉价塑料质感",
                ],
            }
        )
    elif not _is_manufacturing_topic(topic_text):
        topic = clean_visual_phrase(user_input.get("user_input_topic_title", "当前主题"), fallback="当前主题")
        industry = user_input.get("user_input_industry_name", "当前行业")
        style_bible.update(
            {
                "style_id": "market_derived_premium_001",
                "color_palette": ["中性白", "冷灰", "自然色", "少量主题色"],
                "lighting_style": "真实商业摄影灯光，干净自然，专业克制，有空间层次",
                "camera_language": "真实商业视频素材镜头语言，稳定运镜，画面完整，适合宣传片和商业剪辑",
                "factory_environment": f"{industry}相关真实商业场景，围绕{topic}组织空间、人物、道具和环境细节",
                "environment_style": f"{industry}相关真实商业场景，围绕{topic}组织空间、人物、道具和环境细节",
                "equipment_style": f"与{topic}直接相关的真实道具、设备、材料和环境元素",
                "cultural_context": f"中国市场商业素材语境，人物、空间和场景细节贴合{industry}和{topic}。",
                "negative_constraints": [
                    "商标标志",
                    "品牌名称",
                    "水印",
                    "随机文字",
                    "小字",
                    "密集文字",
                    "乱码文字",
                    "不贴合场景的文字",
                    "真实机构标识",
                    "真实姓名工牌",
                    "畸形手部",
                    "人物五官异常",
                    "卡通风格",
                    "低清晰度",
                    "廉价塑料质感",
                ],
            }
        )
    style_bible["commercial_rules"]["copy_space_required"] = bool(
        user_input.get("user_input_copy_space_required", False)
    )
    style_bible["commercial_rules"]["no_text"] = bool(user_input.get("user_input_need_no_text", True))
    style_bible["commercial_rules"]["no_logo"] = bool(user_input.get("user_input_need_no_logo", True))
    people_priority = str(
        user_input.get("user_input_people_region_priority", DEFAULT_SKILL_INPUT["user_input_people_region_priority"])
    )
    if any(keyword in topic_text for keyword in ["中秋", "月饼", "团圆", "赏月", "灯笼", "桂花"]):
        style_bible["people_style"] = people_priority + "，自然温暖，真实细腻，服饰现代得体，可带少量中式节日细节，不夸张摆拍"
    else:
        style_bible["people_style"] = people_priority + "，专业工装或商务工装，干净利落，真实自然，不夸张摆拍"
    style_bible["text_policy"]["allow_contextual_large_chinese_text_when_necessary"] = bool(
        user_input.get("user_input_allow_contextual_large_chinese_text", True)
    )
    return style_bible


def _is_manufacturing_topic(topic_text: str) -> bool:
    return any(
        keyword in topic_text
        for keyword in [
            "制造",
            "工厂",
            "车间",
            "产线",
            "机械臂",
            "工业",
            "半导体",
            "芯片",
            "新能源汽车",
            "仓储",
            "AGV",
            "CNC",
            "智能制造",
        ]
    )
