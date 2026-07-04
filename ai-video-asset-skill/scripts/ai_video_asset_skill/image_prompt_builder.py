"""根据分镜生成中文生图提示词 JSON。"""

from __future__ import annotations

from typing import Any, Dict, List

from .production_text import clean_visual_phrase, clean_visual_terms


def build_image_prompt(shot: Dict[str, Any], style_bible: Dict[str, Any], aspect_ratio: str) -> Dict[str, Any]:
    negative_constraints = _unique_list(
        list(shot.get("negative_constraints", [])) + list(style_bible.get("negative_constraints", []))
    )
    prompt = _build_compact_prompt(shot, style_bible, aspect_ratio, negative_constraints)
    return {
        "shot_id": shot["shot_id"],
        "aspect_ratio": aspect_ratio,
        "prompt": prompt.strip(),
        "negative_prompt": ", ".join(negative_constraints),
        "prompt_version": "compact_commercial_still_v3",
        "prompt_detail_level": "compact",
        "prompt_supporting_metadata": {
            "detailed_script": shot.get("detailed_script", ""),
            "research_basis": shot.get("research_basis", {}),
            "generation_risk_notes": shot.get("generation_risk_notes", []),
            "continuity_lock": shot.get("continuity_lock", {}),
            "reference_summary": _format_reference_plan(shot.get("reference_dependency") or shot.get("reference_image_plan")),
        },
        "copy_space": shot["copy_space"],
        "direct_use_composition": shot.get("direct_use_composition", shot.get("copy_space", "")),
        "video_motion_intent": shot.get("video_motion_intent", ""),
        "generation_risk_notes": shot.get("generation_risk_notes", []),
        "style_id": style_bible["style_id"],
        "image_output_dir": shot["image_output_dir"],
        "people_style": style_bible.get("people_style", ""),
        "cultural_context": style_bible.get("cultural_context", ""),
        "text_policy": style_bible.get("text_policy", {}),
        "reference_image_plan": shot.get("reference_image_plan", {}),
        "reference_dependency": shot.get("reference_dependency", {}),
        "reference_frame_ids": shot.get("reference_frame_ids", []),
        "reference_frame_paths": shot.get("reference_frame_paths", []),
        "reference_frame_usage_notes": shot.get("reference_frame_usage_notes", ""),
    }


def build_regeneration_prompt(
    shot: Dict[str, Any],
    prompt_data: Dict[str, Any],
    failure_reasons: List[str],
) -> Dict[str, Any]:
    reason_text = "；".join(failure_reasons) if failure_reasons else "人工要求重新生成当前分镜"
    fix_prompt = f"""请基于原分镜重新生成该画面，并重点修复以下问题：

失败原因：
{reason_text}

必须保留：
- 原分镜主题
- 主体元素
- 原提示词中的行业、节日或主题语境
- 原提示词中的人物地域设定、场景设定、色彩体系和广告质感
- 原提示词中的构图方向、景别、机位和直接使用构图
- 如果原镜头有参考图计划，继续使用同一个参考图保持一致性

重点优化：
- 画面更清晰
- 构图更稳
- 主体更准确
- 场景细节更丰富，但不要杂乱
- 光线更有层次，材质更真实
- 画面完整可直接使用，主体和环境信息都要充实
- 避免文字、logo、水印
- 如果文字确实必要，只保留贴合场景的大号清晰中文，避免小字和乱码
- 避免主体、道具、建筑、食品、机械或人物结构畸形
- 避免人物手部、五官和表情异常

重新生成一张更适合商业视频素材销售的版本。

原始提示词摘要：
{_limit_text(prompt_data['prompt'], 700)}
"""
    return {
        "shot_id": shot["shot_id"],
        "prompt": fix_prompt.strip(),
        "negative_prompt": prompt_data.get("negative_prompt", ""),
        "regeneration_reasons": failure_reasons,
        "reference_image_plan": prompt_data.get("reference_image_plan", shot.get("reference_image_plan", {})),
        "reference_dependency": prompt_data.get("reference_dependency", shot.get("reference_dependency", {})),
        "reference_frame_ids": prompt_data.get("reference_frame_ids", shot.get("reference_frame_ids", [])),
        "reference_frame_paths": prompt_data.get("reference_frame_paths", shot.get("reference_frame_paths", [])),
        "reference_frame_usage_notes": prompt_data.get("reference_frame_usage_notes", shot.get("reference_frame_usage_notes", "")),
    }


def build_variation_prompt(
    anchor_shot_id: str,
    target_shot_size: str,
    target_camera_angle: str,
    target_composition: str,
    target_action_variation: str,
) -> Dict[str, Any]:
    prompt = f"""请基于锚点画面生成同一场景下的连贯分镜画面。

锚点画面核心保持不变：
- 同一主题、同一场景语境、同一色彩体系、同一光线气质和同一商业广告质感
- 同一类人物地域特征、服饰气质、道具材质、空间关系和美术风格
- 同样干净、真实、高级，适合剪辑进同一条 AI 视频
- 同样无logo、无水印；如果画面必须出现文字，只允许少量贴合场景的大号清晰中文，禁止小字、密集文字和乱码

本次只调整：
- 景别：{target_shot_size}
- 机位：{target_camera_angle}
- 构图：{target_composition}
- 动作变化：{target_action_variation}

目标：
生成一张与锚点画面风格连续、空间连续、光线连续、主体连续，可剪辑在一起的视频素材画面。画面细节要足够丰富，但不要改变锚点图的核心设定。"""
    return {
        "anchor_shot_id": anchor_shot_id,
        "prompt": prompt,
        "target_shot_size": target_shot_size,
        "target_camera_angle": target_camera_angle,
        "target_composition": target_composition,
        "target_action_variation": target_action_variation,
        "negative_prompt": "商标标志，品牌名称，水印，随机文字，变形机械结构，低清晰度",
    }


def _unique_list(values: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _build_compact_prompt(
    shot: Dict[str, Any],
    style_bible: Dict[str, Any],
    aspect_ratio: str,
    negative_constraints: List[str],
) -> str:
    action = _clean_action_description(shot)
    subject = clean_visual_phrase(shot.get("subject_main", ""))
    secondary = clean_visual_terms(shot.get("subject_secondary", []))
    scene_context = clean_visual_phrase(shot.get("scene_context", ""))
    people_context = _compact_join(
        [
            clean_visual_phrase(style_bible.get("people_style", "")),
            clean_visual_phrase(style_bible.get("cultural_context", "")),
        ],
        max_chars=150,
    )
    text_policy = "无可读文字、无Logo、无水印、无品牌名"
    if not style_bible.get("commercial_rules", {}).get("no_text", True):
        text_policy = "避免小字、乱码、品牌名和水印；只有语义必要时才允许少量大号清晰文字"
    lines = [
        f"生成 {aspect_ratio} 单张真实摄影商业视频静帧，画面完整，可直接用于剪辑，不要拼贴、多宫格或海报。",
        f"核心画面：{action}",
        f"主体：{subject}。辅助元素：{_format_list(secondary)}。",
        f"场景：{scene_context}",
        (
            f"镜头：{shot.get('shot_size', '')}，{shot.get('camera_angle', '')}，"
            f"{shot.get('camera_movement', '')}。{shot.get('composition_notes', '')}"
        ),
        (
            f"风格光线：{shot.get('visual_style', '')}；{shot.get('lighting_style', '')}；"
            f"{shot.get('mood_tone', '')}；色彩 {shot.get('color_palette', '')}。"
        ),
    ]
    if people_context:
        lines.append(f"人物语境：{people_context}")
    lines.extend(
        [
            f"硬性要求：{text_policy}；主体清楚，前中后景有层次，材质真实，手部和五官自然，空间透视正确。",
            "只表现一个明确工作瞬间，避免把多个场景或复杂时间线塞进同一张图。",
            f"避免：{', '.join(_compact_negative_constraints(negative_constraints))}。",
        ]
    )
    reference_hint = _compact_reference_hint(shot.get("reference_dependency") or shot.get("reference_image_plan"))
    if reference_hint:
        lines.append(reference_hint)
    return "\n".join(_clean_prompt_line(line) for line in lines if _clean_prompt_line(line))


def _clean_action_description(shot: Dict[str, Any]) -> str:
    action = clean_visual_phrase(shot.get("action_description", ""))
    subject = clean_visual_phrase(shot.get("subject_main", ""))
    if not action:
        return subject
    if subject and (action.count(subject) > 1 or f"{subject}呈现{subject}" in action):
        return f"{subject}的真实商业素材画面，主体动作自然清楚，场景完整可剪辑"
    return action


def _compact_negative_constraints(values: List[str]) -> List[str]:
    important = [
        "商标标志",
        "品牌名称",
        "水印",
        "随机文字",
        "小字",
        "密集文字",
        "乱码文字",
        "畸形手部",
        "人物五官异常",
        "低清晰度",
        "卡通风格",
    ]
    selected = [value for value in important if value in values]
    for value in values:
        if len(selected) >= 14:
            break
        if value not in selected:
            selected.append(value)
    return selected


def _compact_join(values: List[Any], max_chars: int) -> str:
    text = "；".join(str(value).strip("；。 \n") for value in values if str(value).strip())
    return _limit_text(text, max_chars)


def _compact_reference_hint(reference_plan: Dict[str, Any] | None) -> str:
    if not reference_plan:
        return ""
    role = reference_plan.get("role", reference_plan.get("reference_role", ""))
    frame_ids = reference_plan.get("reference_frame_ids") or []
    if frame_ids:
        return (
            "参考图：仅参考所选参考帧的题材、构图、镜头语言、光线、动作或材质线索，"
            "不要复刻原图人物、文字、Logo、水印或版权画面。"
        )
    if role == "derived_view":
        anchor = reference_plan.get("anchor_shot_id", reference_plan.get("reference_shot_id"))
        return f"连续性：保持与锚点镜头 {anchor} 相同的空间、人物类型、光线和色彩，只改变本镜头的景别或动作。"
    return ""


def _clean_prompt_line(value: str) -> str:
    return " ".join(str(value).split()).strip()


def _limit_text(value: Any, max_chars: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _build_detail_brief(shot: Dict[str, Any], style_bible: Dict[str, Any], aspect_ratio: str) -> Dict[str, str]:
    topic_text = " ".join(
        [
            str(style_bible.get("style_id", "")),
            str(style_bible.get("industry", "")),
            str(style_bible.get("main_visual_style", "")),
            str(shot.get("scene_group", "")),
            str(shot.get("subject_main", "")),
            " ".join(str(item) for item in shot.get("subject_secondary", [])),
        ]
    )
    if any(keyword in topic_text for keyword in ["中秋", "月饼", "团圆", "赏月", "灯笼", "桂花", "mid_autumn"]):
        return _mid_autumn_detail_brief(shot, style_bible, aspect_ratio)
    if any(keyword in topic_text for keyword in ["制造", "工厂", "工业", "机械", "产线", "智能", "芯片"]):
        return _manufacturing_detail_brief(shot, style_bible, aspect_ratio)
    return _generic_detail_brief(shot, style_bible, aspect_ratio)


def _mid_autumn_detail_brief(shot: Dict[str, Any], style_bible: Dict[str, Any], aspect_ratio: str) -> Dict[str, str]:
    return {
        "scene_layers": _mid_autumn_scene_layers(shot, aspect_ratio),
        "people_direction": (
            f"- {style_bible.get('people_style', '')}\n"
            f"- {style_bible.get('cultural_context', '')}\n"
            "- 如出现人物，以自然的中国家庭、年轻中国人、父母孩子或三代同堂为主，表情温暖克制，不要夸张摆拍。\n"
            "- 服饰现代得体，可有少量中式节日细节；手部递月饼、提灯笼、倒茶、开礼盒等动作要自然准确。"
        ),
        "composition_direction": _mid_autumn_composition_direction(shot),
        "material_direction": _mid_autumn_material_direction(shot),
        "detail_density": _mid_autumn_detail_density(shot),
    }


def _mid_autumn_scene_layers(shot: Dict[str, Any], aspect_ratio: str) -> str:
    text = _shot_text(shot)
    if _contains_any(text, ["月饼", "礼盒", "茶席", "茶具"]):
        return (
            "- 前景：可加入月饼切面、礼盒边缘、茶盏蒸汽、桂花细粒或木质桌面纹理，形成浅景深。\n"
            "- 中景：月饼、礼盒或茶席必须是绝对主体，摆放端正，高级、有产品广告质感。\n"
            "- 背景：用窗边月光、暖色灯笼散景、深蓝夜色或柔和家居背景衬托，不要出现品牌包装和密集小字。\n"
            f"- 画面比例按 {aspect_ratio} 组织，保留适合后期加节日祝福语的干净区域。"
        )
    if _contains_any(text, ["家庭", "团圆", "孩子", "母亲", "父母", "三代", "祖孙", "家人", "同行", "返家", "家门", "回家"]):
        return (
            "- 前景：可加入月饼盘、茶杯、礼盒提手、灯笼边缘或窗框虚化，形成温暖景深。\n"
            "- 中景：家庭成员之间的动作关系要清楚，如分享月饼、递灯笼、提礼盒回家、家人同行或窗边赏月。\n"
            "- 背景：保留中国家庭餐厅、阳台、城市住宅窗光、中式街巷、院落门口或满月夜色，空间干净温暖，不要杂乱堆物。\n"
            f"- 画面比例按 {aspect_ratio} 组织，人物和环境层次不能互相挤压。"
        )
    if _contains_any(text, ["灯笼", "街巷", "公园", "院落"]):
        return (
            "- 前景：可加入红灯笼边缘、纸灯笼暖光、树叶或石板路虚化，形成节日夜景景深。\n"
            "- 中景：灯笼、街巷行走人物或院落空间为主体，线条清楚，节日氛围一眼可读。\n"
            "- 背景：保留中式街巷、传统院落、城市公园或冷月光，不要景区商标、霓虹招牌和拥挤人群。\n"
            f"- 画面比例按 {aspect_ratio} 组织，灯笼光斑不能过曝成一团。"
        )
    if _contains_any(text, ["玉兔", "月宫", "丝绸", "国风", "云雾"]):
        return (
            "- 前景：可加入丝绸飘带、桂花枝、轻薄云雾或剪影边缘，增强东方意象。\n"
            "- 中景：玉兔剪影、月宫意象或圆月构图必须写实高级，不要卡通化，不要低幼插画。\n"
            "- 背景：用深蓝夜色、暖金月光、云层层次和干净完整构图建立国风广告画面。\n"
            f"- 画面比例按 {aspect_ratio} 组织，创意意象要高级克制，不要仙侠特效堆砌。"
        )
    return (
        "- 前景：可加入江南屋檐剪影、桂花枝叶、窗框、灯笼散景或树影虚化，形成真实景深。\n"
        "- 中景：圆月、城市天际线、庭院或屋檐关系要清楚，主体轮廓明确。\n"
        "- 背景：保留深蓝夜色、中国城市灯火、柔和月晕和节日暖光，背景有层次但不能喧宾夺主。\n"
        f"- 画面比例按 {aspect_ratio} 组织，留出适合后期加节日祝福语的干净区域。"
    )


def _mid_autumn_composition_direction(shot: Dict[str, Any]) -> str:
    text = _shot_text(shot)
    if _contains_any(text, ["月饼", "礼盒", "茶席", "茶具"]):
        return (
            "- 产品镜头要像高端食品TVC：主体端正，桌面线条稳定，浅景深突出月饼纹理和礼盒材质。\n"
            "- 月饼、茶具、桂花和环境层次之间要有清楚关系，避免道具平均铺满。\n"
            "- 如果是俯拍，器物间距要讲究；如果是特写，切面和纹样必须清楚。"
        )
    if _contains_any(text, ["家庭", "团圆", "孩子", "母亲", "父母", "三代", "祖孙", "家人", "同行", "返家", "家门", "回家"]):
        return (
            "- 家庭镜头要先读到人物关系，再读到节日元素；视线、手势、餐桌、窗框、院门或街巷纵深形成自然引导线。\n"
            "- 人物不要挤满画面，保留自然呼吸感和环境层次。\n"
            "- 情绪要温暖真实，有返家和相伴的团圆感，不要像摆拍全家福。"
        )
    if _contains_any(text, ["灯笼", "街巷", "公园", "院落"]):
        return (
            "- 灯笼和街巷线条要形成纵深，前景灯笼可虚化，中景主体必须清楚。\n"
            "- 红灯笼暖光和冷月光形成冷暖对比，不要把整张图染成单一红色。\n"
            "- 人群要少而自然，避免拥挤杂乱。"
        )
    if _contains_any(text, ["玉兔", "月宫", "丝绸", "国风", "云雾"]):
        return (
            "- 国风意象要有高级广告构图，圆月、剪影、云雾和丝绸形成简洁主画面。\n"
            "- 创意元素要写实、克制、可商用，不要出现版权角色或卡通人物。\n"
            "- 画面中心和环境层次要清楚分离。"
        )
    return (
        "- 建立镜头要有宽幅空间感，月亮、屋檐、桂花枝和城市天际线形成稳定构图。\n"
        "- 主体月亮不能像贴图，要有真实月晕和空气透视。\n"
        "- 画面构图干净完整，适合直接作为中秋祝福段落素材。"
    )


def _mid_autumn_material_direction(shot: Dict[str, Any]) -> str:
    text = _shot_text(shot)
    if _contains_any(text, ["月饼", "礼盒", "茶席", "茶具"]):
        return (
            "- 月饼表皮要有烘焙纹理、细腻油润光泽和清楚纹样，不能糊成乱码。\n"
            "- 礼盒应有高级纸张、丝绸或哑光烫金质感，但不要品牌字和小字。\n"
            "- 茶具、木桌、桂花和蒸汽要有真实反光和柔和阴影。"
        )
    if _contains_any(text, ["家庭", "团圆", "孩子", "母亲", "父母", "三代", "祖孙", "家人", "同行", "返家", "家门", "回家"]):
        return (
            "- 室内暖光、窗外月光和人物肤色要自然融合，肤色健康真实。\n"
            "- 餐桌、茶杯、月饼、灯笼、礼盒、院门、石板路和家居材质要真实，不要塑料感。\n"
            "- 深蓝夜色、暖金室内光、灯笼暖光和月光形成高级冷暖对比。"
        )
    if _contains_any(text, ["灯笼", "街巷", "公园", "院落"]):
        return (
            "- 灯笼纸面要有细腻透光感，红色饱和但不过曝。\n"
            "- 石板路、院墙、树叶和夜色要有真实质感与湿润空气层次。\n"
            "- 冷月光和暖灯光要分层，避免廉价霓虹。"
        )
    if _contains_any(text, ["玉兔", "月宫", "丝绸", "国风", "云雾"]):
        return (
            "- 丝绸、云雾、月光和剪影边缘要细腻真实，不能像平面贴纸。\n"
            "- 暖金月光与深蓝夜色形成高端东方广告色调。\n"
            "- 国风元素要写实高级，不要低幼、仙侠或网游质感。"
        )
    return (
        "- 强调暖金月光、深蓝夜色、城市灯火、桂花枝叶和屋檐材质的真实层次。\n"
        "- 月亮要有自然月晕和空气感，城市灯火不要过曝。\n"
        "- 色彩可以饱和，但不要变成廉价红金堆砌；整体保持高端节日TVC质感。"
    )


def _mid_autumn_detail_density(shot: Dict[str, Any]) -> str:
    text = _shot_text(shot)
    if _contains_any(text, ["月饼", "礼盒", "茶席", "茶具"]):
        return (
            "- 需要丰富但克制的产品细节：月饼纹样、切面层次、礼盒纸纹、茶雾、桂花、桌面纹理。\n"
            "- 不要加入杂牌包装、密集小字、过多餐具或无关甜点。\n"
            "- 纹样和蒸汽要适合后续生视频，避免太密导致闪烁。"
        )
    if _contains_any(text, ["家庭", "团圆", "孩子", "母亲", "父母", "三代", "祖孙", "家人", "同行", "返家", "家门", "回家"]):
        return (
            "- 需要真实生活细节：餐桌食物边缘、窗边月光、礼盒、灯笼、茶杯、院落门口、街巷石板路、家庭互动手势。\n"
            "- 细节要服务团圆情绪，不要餐桌杂乱，不要人物数量过多。\n"
            "- 手部、眼神、表情和身体姿态必须自然。"
        )
    if _contains_any(text, ["灯笼", "街巷", "公园", "院落"]):
        return (
            "- 需要夜景细节：灯笼纸纹、暖光散景、石板路、树影、院墙、月光层次。\n"
            "- 不要让灯笼文字过小可读，不要出现商铺招牌和景区品牌。\n"
            "- 光斑可以丰富，但主体轮廓必须清楚。"
        )
    if _contains_any(text, ["玉兔", "月宫", "丝绸", "国风", "云雾"]):
        return (
            "- 需要高级意象细节：云雾层次、丝绸纹理、月光边缘、桂花剪影。\n"
            "- 不要加入卡通嫦娥、版权角色、复杂符号或过多金色粒子。\n"
            "- 画面要能作为TVC创意静帧，不要像廉价节日海报。"
        )
    return (
        "- 需要丰富但干净的建立镜头细节：桂花枝、屋檐轮廓、城市灯火、月晕、薄云和夜色空气感。\n"
        "- 不要加入无关餐具、杂牌包装、可读小字或拥挤人群。\n"
        "- 画面要适合后续生视频，避免太密的小物件、太细的线条和容易闪烁的复杂纹样。"
    )


def _manufacturing_detail_brief(shot: Dict[str, Any], style_bible: Dict[str, Any], aspect_ratio: str) -> Dict[str, str]:
    return {
        "scene_layers": (
            "- 前景：可加入设备边缘、金属反光、控制台局部、传送带或工程师手部作为景深层次。\n"
            "- 中景：清楚呈现主体设备、产线动作、工程师协作或数据中控画面。\n"
            "- 背景：保留高挑厂房、自动化产线纵深、洁净地面和克制科技光效，背景要整洁有秩序。\n"
            f"- 画面比例按 {aspect_ratio} 组织，主体、产线和环境信息完整，避免做成标题背景模板。\n"
            "- 天空、墙面、地面、玻璃幕墙或单色区域不要占据过大比例；画面上方、边缘和远景也要有真实环境层次、工业建筑或设备信息。"
        ),
        "people_direction": (
            f"- {style_bible.get('people_style', '')}\n"
            f"- {style_bible.get('cultural_context', '')}\n"
            "- 如出现工程师，动作要专业自然，不要摆拍；安全帽、工装、无尘服或商务工装要贴合具体场景。"
        ),
        "composition_direction": (
            "- 用产线纵深、机械臂阵列、地面反光或屏幕光线形成明确引导线。\n"
            "- 设备结构要真实可信，机械臂、夹具、传送带、晶圆或电池模组比例准确，不要出现多余关节和畸形零件。\n"
            "- 科技数据层必须克制，优先抽象图形，不要可读真实文字或密集UI。"
        ),
        "material_direction": (
            "- 强调金属、玻璃、洁净地面、工业灯带、冷白光和少量蓝色科技光的真实反射。\n"
            "- 材质要高级，避免塑料玩具感、脏污车间感和过度科幻霓虹。"
        ),
        "detail_density": (
            "- 需要足够工业细节：传感器、夹具、线缆收纳、设备边框、地面标线、抽象数据光层等。\n"
            "- 细节要有秩序，不能让画面拥挤；避免重复机械臂糊成一片或背景设备结构混乱。"
        ),
    }


def _generic_detail_brief(shot: Dict[str, Any], style_bible: Dict[str, Any], aspect_ratio: str) -> Dict[str, str]:
    return {
        "scene_layers": (
            "- 前景：加入与主题相关的局部元素或虚化边缘，形成真实摄影景深。\n"
            "- 中景：主体和关键动作必须最清楚。\n"
            "- 背景：交代环境和行业语境，保持干净、真实、有空间层次。\n"
            f"- 画面比例按 {aspect_ratio} 组织，主体、环境和动作信息完整，避免做成标题背景模板。"
        ),
        "people_direction": (
            f"- {style_bible.get('people_style', '')}\n"
            f"- {style_bible.get('cultural_context', '')}\n"
            "- 如出现人物，动作、表情、服饰和姿态要自然可信，手部和五官不能畸形。"
        ),
        "composition_direction": (
            "- 画面主次明确，主体、环境和动作之间关系稳定。\n"
            "- 使用真实摄影构图，不要海报式堆字，不要把主体放得过小或被背景淹没。"
        ),
        "material_direction": (
            "- 强调真实材质、合理反光、自然阴影、清晰边缘和专业灯光层次。\n"
            "- 色彩遵循风格圣经，不要廉价滤镜或单一颜色铺满。"
        ),
        "detail_density": (
            "- 细节要比普通描述更充分，包含道具、材质、背景层次和光影细节。\n"
            "- 细节必须服务主题，避免无关装饰、杂乱背景、小字和不可控复杂纹样。"
        ),
    }


def _format_list(values: List[Any]) -> str:
    cleaned = [str(value) for value in values if str(value).strip()]
    return "、".join(cleaned) if cleaned else "无"


def _shot_text(shot: Dict[str, Any]) -> str:
    return " ".join(
        [
            str(shot.get("scene_group", "")),
            str(shot.get("shot_title", "")),
            str(shot.get("subject_main", "")),
            str(shot.get("action_description", "")),
            str(shot.get("scene_context", "")),
            " ".join(str(item) for item in shot.get("subject_secondary", [])),
        ]
    )


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _format_continuity_lock(continuity_lock: Dict[str, Any] | None) -> str:
    if not continuity_lock:
        return "- 按 style_bible 保持整体视觉统一。"
    lines = []
    if continuity_lock.get("style_id"):
        lines.append(f"- style_id：{continuity_lock['style_id']}")
    if continuity_lock.get("environment_style"):
        lines.append(f"- 环境风格：{continuity_lock['environment_style']}")
    if continuity_lock.get("people_style"):
        lines.append(f"- 人物风格：{continuity_lock['people_style']}")
    if continuity_lock.get("equipment_style"):
        lines.append(f"- 道具/设备风格：{continuity_lock['equipment_style']}")
    return "\n".join(lines) if lines else "- 按 style_bible 保持整体视觉统一。"


def _format_reference_plan(reference_plan: Dict[str, Any] | None) -> str:
    if not reference_plan:
        return "无参考图要求，按 style_bible 保持统一风格。"
    market_refs = reference_plan.get("market_reference_asset_paths") or []
    reference_frame_ids = reference_plan.get("reference_frame_ids") or []
    reference_frame_paths = reference_plan.get("reference_frame_paths") or []
    reference_frame_usage = reference_plan.get("reference_frame_usage") or ""
    reference_frame_text = ""
    if reference_frame_ids:
        reference_frame_text = (
            f"\n- 精选参考帧：{', '.join(str(item) for item in reference_frame_ids[:3])}。"
            f"原文件：{', '.join(str(item) for item in reference_frame_paths[:3])}。"
            "仅参考题材、构图、镜头语言、光线、色彩和商业质感；允许相似参考，但最终生成图与任一来源帧相似度目标不得超过 90%。"
            f"{reference_frame_usage}"
        )
    market_text = ""
    if market_refs:
        scores = reference_plan.get("market_reference_scores") or []
        categories = reference_plan.get("market_reference_categories") or []
        score_text = ""
        if scores:
            score_text = f"参考评分：{', '.join(str(score) for score in scores[:2])}；"
        category_text = ""
        if categories:
            flattened = []
            for category in categories[:2]:
                if isinstance(category, list):
                    flattened.extend(str(item) for item in category)
                elif category:
                    flattened.append(str(category))
            if flattened:
                category_text = f"分类：{', '.join(dict.fromkeys(flattened))}；"
        market_text = (
            f"\n- 可参考高分市场调研图 {', '.join(market_refs[:2])} 的题材方向、景别组织、色彩气质和画面模块；"
            f"{score_text}{category_text}"
            "只借鉴方向，不复刻原图、人物、包装、文字、Logo、水印或可识别版权画面。"
        )
    role = reference_plan.get("role", reference_plan.get("reference_role", ""))
    if role == "anchor":
        return (
            "本镜头作为同场景锚点图生成。通过后保存为 当前图.png，"
            "后续同组多景别、多角度镜头优先以此图作为参考图。"
            f"{market_text}"
            f"{reference_frame_text}"
        )
    if role in {"", "standalone"}:
        return f"本镜头独立生成，按 style_bible 保持统一风格；参考素材只作为可选构图、光线、动作或材质依据。{market_text}{reference_frame_text}"
    return (
        f"本镜头需要参考锚点镜头 {reference_plan.get('anchor_shot_id', reference_plan.get('reference_shot_id'))} 的画面一致性。"
        "保持同一场景、人物类型、设备外观、光线、色彩和空间关系，只调整本镜头要求的景别、机位或动作。"
        f"{market_text}"
        f"{reference_frame_text}"
    )
