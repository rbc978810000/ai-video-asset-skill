"""生成适合商业 AI 视频素材生产的中文分镜。"""

from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    CAMERA_MOVEMENT_SEQUENCE,
    DIRECT_USE_COMPOSITION_SEQUENCE,
    DEFAULT_SHOT_GROUPS,
    SHOT_SIZE_SEQUENCE,
)
from .file_manager import IMAGE_DIR_NAME, PROMPT_DIR_NAME, artifact_id, prompt_json_file
from .production_text import clean_visual_phrase, clean_visual_terms


GROUP_SCENE_BANK: Dict[str, List[Dict[str, Any]]] = {
    "片头与制造强国氛围": [
        {
            "subject": "现代制造产业园清晨外景",
            "secondary": ["厂区道路", "玻璃幕墙", "远处车间"],
            "action": "晨光照亮整洁的产业园主轴道路",
            "context": "高端制造产业园区，建筑线条简洁，天空通透",
        },
        {
            "subject": "智能工厂入口形象画面",
            "secondary": ["无品牌标识建筑", "工程车辆", "绿化带"],
            "action": "镜头呈现现代工厂入口的秩序感",
            "context": "干净大气的工业园入口区域，没有任何可识别品牌文字",
        },
    ],
    "智能工厂全景": [
        {
            "subject": "现代智能工厂车间全景",
            "secondary": ["机械臂", "自动化生产线", "AGV小车", "工程师"],
            "action": "机械臂在产线上同步作业，AGV小车平稳穿梭",
            "context": "宽敞明亮的高端制造车间，地面干净反光，远处有工业数据大屏",
        },
        {
            "subject": "高挑空间自动化装配车间",
            "secondary": ["输送线", "检测设备", "工程师背影"],
            "action": "自动化输送线稳定运行，工程师在安全通道旁观察",
            "context": "蓝银色调智能车间，结构清晰，画面留有干净背景",
        },
    ],
    "AI工业大脑与数字孪生": [
        {
            "subject": "工业数据中控大屏",
            "secondary": ["数字孪生界面", "工程师侧影", "控制台"],
            "action": "工程师站在控制台前查看实时生产数据",
            "context": "智能工厂中控室，屏幕为抽象数据图形，避免真实文字",
        },
        {
            "subject": "数字孪生工厂可视化画面",
            "secondary": ["透明数据层", "产线模型", "冷白光"],
            "action": "虚拟工厂模型悬浮在控制台上方",
            "context": "真实摄影结合克制科技可视化，背景干净高级",
        },
    ],
    "自动化生产线与机械臂": [
        {
            "subject": "机械臂精准装配工件",
            "secondary": ["夹具", "传送带", "金属零件"],
            "action": "机械臂末端夹具对准金属零件完成一次精准定位",
            "context": "整洁自动化生产线，设备材质高级，空间有纵深",
        },
        {
            "subject": "自动化检测设备工作画面",
            "secondary": ["传感器", "机械滑轨", "冷白灯带"],
            "action": "检测头悬停在产品上方进行扫描",
            "context": "高端检测工位，背景简洁，突出设备精密感",
        },
    ],
    "芯片半导体与精密制造": [
        {
            "subject": "晶圆检测设备微距特写",
            "secondary": ["晶圆反光", "精密探针", "无尘环境"],
            "action": "精密探针靠近晶圆表面进行检测",
            "context": "洁净室局部画面，冷白光，细节清晰",
        },
        {
            "subject": "半导体洁净室工程师",
            "secondary": ["无尘服", "晶圆盒", "精密设备"],
            "action": "工程师双手托住晶圆盒准备放入设备",
            "context": "高洁净度实验空间，避免任何品牌或文字",
        },
    ],
    "新能源汽车与高端装备": [
        {
            "subject": "新能源汽车电池包装配工位",
            "secondary": ["电池模组", "机械臂", "检测灯"],
            "action": "机械臂将电池模组精准放入装配夹具",
            "context": "高端新能源汽车制造车间，画面干净有秩序",
        },
        {
            "subject": "高端装备金属部件检测",
            "secondary": ["大型金属结构", "激光检测头", "工程师"],
            "action": "检测设备沿金属部件边缘缓慢扫描",
            "context": "现代装备制造空间，突出精密与规模感",
        },
    ],
    "研发实验室与工程师": [
        {
            "subject": "研发实验室工程师观察样机",
            "secondary": ["实验台", "传感器模块", "柔和冷光"],
            "action": "工程师俯身查看无品牌样机的运行状态",
            "context": "现代研发实验室，桌面整洁，背景完整不空泛",
        },
        {
            "subject": "工程师团队讨论工业模型",
            "secondary": ["透明模型", "控制台", "蓝色环境光"],
            "action": "两名工程师围绕设备模型进行协同讨论",
            "context": "真实商务研发空间，人物自然，不摆拍",
        },
    ],
    "数字化转型与管理协同": [
        {
            "subject": "管理人员查看生产数据看板",
            "secondary": ["会议桌", "无文字图表", "玻璃墙"],
            "action": "管理人员站在会议室前方观察抽象数据看板",
            "context": "现代企业指挥会议室，主体信息完整，画面可直接剪辑使用",
        },
        {
            "subject": "工厂移动终端巡检画面",
            "secondary": ["平板设备", "设备背景", "工程师手部"],
            "action": "工程师在设备旁用平板确认抽象状态图形",
            "context": "智能车间局部，终端屏幕避免可读文字",
        },
    ],
    "绿色制造与新型储能": [
        {
            "subject": "绿色智能工厂屋顶光伏",
            "secondary": ["光伏板", "现代厂房", "清朗天空"],
            "action": "阳光照射在整齐排列的屋顶光伏板上",
            "context": "绿色制造园区，明亮、干净、低碳科技感",
        },
        {
            "subject": "储能设备整齐排列画面",
            "secondary": ["电池柜", "冷白灯", "维护工程师"],
            "action": "工程师在储能设备通道内进行巡视",
            "context": "新型储能设备间，秩序感强，无品牌文字",
        },
    ],
    "产业升级与未来制造收尾": [
        {
            "subject": "未来制造产线纵深收尾画面",
            "secondary": ["机械臂阵列", "蓝银光线", "远处工程师"],
            "action": "自动化产线向远处延伸，形成高级科技纵深",
            "context": "现代智能制造车间，适合作为视频结尾背景",
        },
        {
            "subject": "产业升级抽象科技工厂画面",
            "secondary": ["真实工厂", "克制数据光层", "完整工业背景"],
            "action": "真实工厂空间中出现轻量数字化光层",
            "context": "企业宣传片级别的未来制造视觉，不夸张不廉价",
        },
    ],
}

GROUP_SCENE_BANK.update(
    {
        "智能工厂全景与车间秩序": [
            {
                "subject": "高挑智能工厂车间全景",
                "secondary": ["机械臂阵列", "自动化产线", "AGV小车", "中国工程师"],
                "action": "多条自动化产线在整洁车间内同步运行，AGV小车沿地面导引线穿行",
                "context": "现代中国智能工厂内部，高挑空间、冷白工业灯带、金属设备和干净反光地面",
            },
            {
                "subject": "无人化自动化装配车间",
                "secondary": ["传送带", "检测工位", "安全围栏", "远处中控屏"],
                "action": "无人化装配线保持稳定节奏，设备状态灯形成有序层次",
                "context": "企业宣传片级智能制造车间，空间真实、设备高级、没有可识别厂牌",
            },
            {
                "subject": "智能工厂主通道纵深",
                "secondary": ["两侧产线", "地面导引线", "工程师背影", "远处机械臂"],
                "action": "主通道向远处延伸，工程师沿安全通道巡视产线",
                "context": "宽幅车间纵深画面，生产秩序清楚，适合作为制造业视频主体背景",
            },
            {
                "subject": "数字化车间俯拍秩序画面",
                "secondary": ["机械臂", "输送线", "工位模块", "AGV动线"],
                "action": "从高处俯看产线模块、物流动线和工位分区形成清晰工业秩序",
                "context": "大型智能制造车间，俯拍视角强调规模、秩序和数字化管理能力",
            },
        ],
        "AI质检与质量追溯": [
            {
                "subject": "AI视觉检测设备扫描工件",
                "secondary": ["工业相机", "环形光源", "金属零件", "抽象检测界面"],
                "action": "视觉检测头在传送带上方扫描金属零件表面",
                "context": "干净检测工位，屏幕只有抽象图形和色块，不出现真实可读文字",
            },
            {
                "subject": "自动化质检机械臂分拣零件",
                "secondary": ["机械夹爪", "合格品托盘", "传感器", "冷白灯"],
                "action": "机械夹爪把检测后的零件准确放入分类托盘",
                "context": "智能质检工位，主体动作清楚，设备结构真实可信",
            },
            {
                "subject": "质量追溯中控界面前的工程师",
                "secondary": ["抽象质量曲线", "控制台", "侧影工程师", "玻璃墙"],
                "action": "工程师在控制台前观察抽象质量追溯图形",
                "context": "工业质量管理中控室，数据层克制，避免任何真实数字和品牌UI",
            },
            {
                "subject": "精密产品表面缺陷检测特写",
                "secondary": ["激光扫描线", "金属表面", "微小反光", "检测支架"],
                "action": "细窄检测光线扫过精密零件表面，突出工业AI质检能力",
                "context": "近距离工业检测画面，材质真实，避免科幻化过度",
            },
        ],
        "工业大脑数字孪生与中控室": [
            {
                "subject": "智能工厂工业大脑中控室",
                "secondary": ["大型数据墙", "抽象工厂模型", "控制台", "中国工程师"],
                "action": "工程师团队在中控室查看抽象化生产状态和工厂模型",
                "context": "真实中控室空间，屏幕为不可读抽象图形，体现工业互联网和数字化管理",
            },
            {
                "subject": "数字孪生工厂三维模型",
                "secondary": ["真实控制台", "透明产线模型", "蓝银光线", "工程师手势"],
                "action": "克制的数字孪生模型悬浮在控制台上方，与真实车间数据呼应",
                "context": "真实摄影结合轻量数据可视化，不做廉价全息屏",
            },
            {
                "subject": "生产计划排程指挥画面",
                "secondary": ["无文字图表", "会议桌", "玻璃墙", "管理人员"],
                "action": "管理人员围绕抽象生产排程图协同决策",
                "context": "现代制造企业调度会议室，体现数字化转型和智能经营决策",
            },
            {
                "subject": "车间数据与真实产线叠加",
                "secondary": ["机械臂背景", "透明数据光层", "传送带", "状态灯"],
                "action": "真实产线画面上叠加克制的数据状态层，呈现生产过程可视化",
                "context": "工业4.0风格，但数据层不遮挡主体，不出现可读文字",
            },
        ],
        "精密制造电子车间与半导体": [
            {
                "subject": "电子车间SMT贴片生产线",
                "secondary": ["贴片设备", "电路板", "冷白灯带", "防静电工装"],
                "action": "电子贴片设备在封闭产线中高速精准作业",
                "context": "高端电子制造车间，设备干净，细节密度高但不杂乱",
            },
            {
                "subject": "半导体洁净室工程师操作设备",
                "secondary": ["无尘服", "晶圆盒", "精密设备", "玻璃隔断"],
                "action": "无尘服工程师把晶圆盒平稳放入精密设备舱口",
                "context": "洁净室环境真实高级，避免医疗感和品牌仪器文字",
            },
            {
                "subject": "晶圆检测微距特写",
                "secondary": ["晶圆彩色反光", "探针", "洁净台", "浅景深"],
                "action": "精密探针靠近晶圆表面完成一次检测动作",
                "context": "半导体精密制造特写，光线细腻，材料反射真实",
            },
            {
                "subject": "数控精密加工中心",
                "secondary": ["CNC设备", "金属切削液", "夹具", "防护玻璃"],
                "action": "数控加工设备对金属部件进行精密加工",
                "context": "先进制造加工工位，金属质感清晰，设备无品牌标识",
            },
        ],
        "AGV仓储物流与柔性供应链": [
            {
                "subject": "AGV小车穿梭智能仓储通道",
                "secondary": ["货架", "托盘", "地面导引线", "状态灯"],
                "action": "AGV小车载着标准化料箱沿仓储通道平稳行驶",
                "context": "智能制造配套仓储空间，货架整齐，没有物流品牌和可读标签",
            },
            {
                "subject": "机械物流分拣系统",
                "secondary": ["滚筒输送线", "分拣机械臂", "料箱", "传感器"],
                "action": "分拣机械臂从输送线上抓取料箱并放入指定通道",
                "context": "自动化物流工位，突出制造协同和柔性供应链",
            },
            {
                "subject": "车间物料配送交接",
                "secondary": ["AGV", "工程师", "料架", "产线入口"],
                "action": "AGV在产线入口停靠，工程师确认物料交接状态",
                "context": "真实智能工厂车间物流节点，人物动作自然专业",
            },
        ],
        "工程师研发与人机协同": [
            {
                "subject": "中国工程师调试机械臂",
                "secondary": ["示教器", "机械臂", "安全围栏", "控制柜"],
                "action": "工程师在安全围栏外使用示教器调试机械臂动作",
                "context": "智能制造调试现场，人物专业自然，工牌和屏幕不可读",
            },
            {
                "subject": "研发团队围绕工业样机讨论",
                "secondary": ["实验台", "样机", "传感器模块", "图纸平板"],
                "action": "三名工程师围绕无品牌工业样机进行技术讨论",
                "context": "现代研发实验室，桌面整洁，人物关系真实可信",
            },
            {
                "subject": "工程师巡检数字化产线",
                "secondary": ["平板设备", "产线背景", "设备状态灯", "安全通道"],
                "action": "工程师手持平板在产线旁巡检设备状态",
                "context": "车间巡检画面，平板仅显示抽象状态图，不出现真实文字",
            },
            {
                "subject": "人机协作装配工位",
                "secondary": ["协作机器人", "工程师手部", "小型零件", "工作台"],
                "action": "协作机器人与工程师在同一工位完成零件定位",
                "context": "人机协同场景，手部动作准确，机器人结构真实",
            },
        ],
        "绿色制造储能与低碳工厂": [
            {
                "subject": "智能工厂屋顶光伏阵列",
                "secondary": ["现代厂房", "光伏板", "清朗天空", "能源管理设备"],
                "action": "阳光照射在厂房屋顶整齐排列的光伏板上",
                "context": "绿色制造园区，真实航拍感，避免过度绿色滤镜",
            },
            {
                "subject": "储能设备通道巡检",
                "secondary": ["储能柜", "维护工程师", "冷白灯", "通道纵深"],
                "action": "维护工程师沿储能设备通道检查设备状态",
                "context": "新型储能设备间，设备整齐，无品牌标识",
            },
            {
                "subject": "低碳工厂能源管理画面",
                "secondary": ["抽象能源图形", "控制台", "厂区模型", "工程师"],
                "action": "工程师查看低碳能源管理的抽象数据图形",
                "context": "绿色制造数字化管理空间，数据克制，真实环境支撑",
            },
        ],
        "未来制造收尾与完整背景": [
            {
                "subject": "未来制造产线纵深收尾",
                "secondary": ["机械臂阵列", "远处工程师", "蓝银灯光", "洁净地面"],
                "action": "自动化产线向远处延伸，工程师剪影站在安全通道尽头",
                "context": "现代智能制造车间，画面完整，可直接作为企业宣传片结尾素材",
            },
            {
                "subject": "产业升级真实工厂愿景画面",
                "secondary": ["真实厂房", "克制数据光层", "设备轮廓", "暖冷对比光"],
                "action": "真实工厂空间中出现轻量数据光层，呈现先进制造未来感",
                "context": "不做空泛科幻城市，保持制造业主体和真实工业空间",
            },
            {
                "subject": "智能制造夜间车间完整背景",
                "secondary": ["产线灯带", "机械臂轮廓", "远处控制室", "地面反光"],
                "action": "夜间智能车间保持安静运行，设备状态灯形成高级工业氛围",
                "context": "适合作为视频收尾或转场的完整工业背景，画面信息完整",
            },
        ],
    }
)


def build_storyboard_planner_prompt(
    user_input: Dict[str, Any],
    shot_group_plan: List[Dict[str, Any]] | None = None,
) -> str:
    plan_text = ""
    if shot_group_plan:
        plan_lines = [
            f"- {item['group_name']}：{item['shot_count']} 条；依据：{item.get('reason', '')}"
            for item in shot_group_plan
        ]
        plan_text = "\n\n前期调研后的镜头分组计划：\n" + "\n".join(plan_lines)
    return f"""你是一名AI视频素材分镜策划专家，目标是为“{user_input['user_input_topic_title']}”生成可直接用于批量生图和后续生视频的生产型分镜表。

项目行业：
{user_input['user_input_industry_name']}

目标用途：
{user_input['user_input_target_usage']}

视觉风格：
{user_input['user_input_visual_style']}

分镜数量：
{user_input['user_input_total_shots']}

请严格遵守：
1. 一镜一场，商业素材可售，画面必须完整可直接剪辑使用，素材应像已完成的成片级画面。
2. 人物主要以中国人、中国工程师、中国企业员工为主，场景优先贴合中国制造业语境。
3. 默认不要文字；如果画面语义确实需要文字，只允许少量贴合场景的大号清晰中文，禁止小字、密集字、乱码、品牌字和水印。
4. 同组多景别、多角度画面可以复用高价值参考素材，但每条镜头默认独立生成，不能自动用上一张生成图做锚点派生。
5. 每条分镜 JSON 必须带 `reference_dependency`，字段包含 `role`、`anchor_shot_id`、`reference_image_path`、`market_reference_asset_ids`、`market_reference_asset_paths`、`reference_reason`、`market_reference_usage`；默认 `role` 使用 `standalone`，只有旧项目兼容或用户明确要求连续扩展时才使用 `anchor/derived_view`。
6. 无品牌/logo/水印/版权角色，同组风格统一。{plan_text}"""


def generate_mock_storyboard(
    user_input: Dict[str, Any],
    style_bible: Dict[str, Any],
    shot_group_plan: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """生成满足生产字段要求的确定性中文分镜。"""

    total_shots = int(user_input["user_input_total_shots"])
    storyboard: List[Dict[str, Any]] = []
    shot_number = 1
    group_plan = _normalize_group_plan(total_shots, shot_group_plan)

    for group in group_plan:
        group_name = group["group_name"]
        group_count = int(group["shot_count"])
        scene_bank = _scene_bank_for_group(group)
        for group_index in range(group_count):
            if shot_number > total_shots:
                break
            scene = scene_bank[group_index % len(scene_bank)]
            shot_id = f"shot_{shot_number:03d}"
            shot_size = SHOT_SIZE_SEQUENCE[(shot_number - 1) % len(SHOT_SIZE_SEQUENCE)]
            direct_use_composition = DIRECT_USE_COMPOSITION_SEQUENCE[
                (shot_number - 1) % len(DIRECT_USE_COMPOSITION_SEQUENCE)
            ]
            movement = CAMERA_MOVEMENT_SEQUENCE[(shot_number - 1) % len(CAMERA_MOVEMENT_SEQUENCE)]
            creative_angle = _pick(group.get("creative_angles", []), group_index)
            avoid_patterns = group.get("avoid_patterns", [])
            shot = {
                "shot_id": shot_id,
                "shot_title": f"{group_name} - {scene['subject']}",
                "scene_group": group_name,
                "scene_goal": f"为{user_input['user_input_topic_title']}建立{group_name}相关的商业素材画面",
                "research_basis": {
                    "representative_scene": scene["subject"],
                    "core_elements": group.get("core_elements", []),
                    "creative_angle": creative_angle,
                    "avoid_patterns": avoid_patterns,
                    "evidence_keywords": group.get("evidence_keywords", []),
                    "market_basis": group.get("market_basis", ""),
                    "buyer_use_cases": group.get("buyer_use_cases", []),
                    "market_demand_score": group.get("market_demand_score"),
                    "risk_score": group.get("risk_score"),
                },
                "subject_main": scene["subject"],
                "subject_secondary": scene["secondary"],
                "action_description": scene["action"],
                "scene_context": scene["context"],
                "camera_angle": _camera_angle_for(shot_size),
                "camera_movement": movement,
                "shot_size": shot_size,
                "composition_notes": (
                    f"{direct_use_composition}；主体位于画面视觉重心，前景、中景、背景层次明确，"
                    "画面信息完整，整体像已完成的成片级素材。"
                ),
                "visual_style": user_input["user_input_visual_style"],
                "lighting_style": style_bible["lighting_style"],
                "mood_tone": _mood_tone_for(style_bible),
                "color_palette": ", ".join(style_bible["color_palette"]),
                "copy_space": direct_use_composition,
                "direct_use_composition": direct_use_composition,
                "video_motion_intent": _video_motion_intent_for(scene, shot_size, movement),
                "generation_risk_notes": _generation_risk_notes_for(group_name, scene, avoid_patterns),
                "continuity_lock": {
                    "style_id": style_bible["style_id"],
                    "environment_style": style_bible.get("environment_style", style_bible["factory_environment"]),
                    "people_style": style_bible["people_style"],
                    "equipment_style": style_bible["equipment_style"],
                },
                "negative_constraints": list(style_bible["negative_constraints"]),
                "image_prompt_path": f"../{PROMPT_DIR_NAME}/{prompt_json_file(shot_id)}",
                "image_output_dir": f"../{IMAGE_DIR_NAME}/{artifact_id(shot_id)}",
                "generate_status": "pending",
                "approved_version": None,
                "retry_count": 0,
                "reference_dependency": {
                    "role": "standalone",
                    "anchor_shot_id": None,
                    "reference_image_path": None,
                    "market_reference_asset_ids": [],
                    "market_reference_asset_paths": [],
                    "reference_reason": "",
                    "market_reference_usage": "",
                },
            }
            shot["detailed_script"] = _build_detailed_script(shot)
            storyboard.append(
                shot
            )
            shot_number += 1
    return storyboard[:total_shots]


def storyboard_csv_rows(storyboard: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for shot in storyboard:
        rows.append(
            {
                "shot_id": shot["shot_id"],
                "shot_title": shot["shot_title"],
                "scene_group": shot.get("scene_group", ""),
                "subject_main": shot["subject_main"],
                "shot_size": shot["shot_size"],
                "camera_angle": shot["camera_angle"],
                "direct_use_composition": shot.get("direct_use_composition", shot.get("copy_space", "")),
                "video_motion_intent": shot.get("video_motion_intent", ""),
                "generate_status": shot["generate_status"],
                "approved_version": shot.get("approved_version") or "",
            }
        )
    return rows


def storyboard_csv_fields() -> List[str]:
    return [
        "shot_id",
        "shot_title",
        "scene_group",
        "subject_main",
        "shot_size",
        "camera_angle",
        "direct_use_composition",
        "video_motion_intent",
        "generate_status",
        "approved_version",
    ]


def _normalize_group_plan(
    total_shots: int,
    shot_group_plan: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    if shot_group_plan:
        normalized = []
        remaining = total_shots
        for index, item in enumerate(shot_group_plan):
            if remaining <= 0:
                break
            group_name = item.get("group_name") or item.get("category_name") or f"调研画面组{index + 1}"
            count = int(item.get("shot_count", 1))
            if index == len(shot_group_plan) - 1:
                count = remaining
            else:
                count = max(1, min(count, remaining - (len(shot_group_plan) - index - 1)))
            remaining -= count
            normalized.append({**item, "group_name": group_name, "shot_count": count})
        if remaining > 0 and normalized:
            normalized[-1]["shot_count"] += remaining
        return normalized

    if total_shots <= sum(count for _, count in DEFAULT_SHOT_GROUPS):
        result: List[Dict[str, Any]] = []
        remaining = total_shots
        for group_name, count in DEFAULT_SHOT_GROUPS:
            use_count = min(count, remaining)
            if use_count:
                result.append({"group_name": group_name, "shot_count": use_count})
            remaining -= use_count
            if remaining <= 0:
                break
        return result

    result = [{"group_name": group_name, "shot_count": count} for group_name, count in DEFAULT_SHOT_GROUPS]
    remaining = total_shots - sum(count for _, count in DEFAULT_SHOT_GROUPS)
    index = 0
    while remaining > 0:
        result[index % len(result)]["shot_count"] += 1
        remaining -= 1
        index += 1
    return result


def _scene_bank_for_group(group: Dict[str, Any]) -> List[Dict[str, Any]]:
    group_name = group["group_name"]
    if group_name in GROUP_SCENE_BANK:
        return GROUP_SCENE_BANK[group_name]
    clean_group_name = clean_visual_phrase(group_name, fallback="商业场景")
    scenes = clean_visual_terms(group.get("representative_scenes") or [clean_group_name]) or [clean_group_name]
    core_elements = clean_visual_terms(group.get("core_elements") or ["主体", "场景", "专业设备"])
    creative_angles = clean_visual_terms(group.get("creative_angles") or ["稳定构图"])
    return [
        {
            "subject": clean_visual_phrase(scene, fallback=clean_group_name),
            "secondary": core_elements[:4],
            "action": _market_scene_action(clean_visual_phrase(scene, fallback=clean_group_name), _pick(creative_angles, index)),
            "context": f"{clean_group_name}相关场景，画面干净、真实、高级，完整可直接剪辑使用",
        }
        for index, scene in enumerate(scenes)
    ]


def _market_scene_action(subject: str, creative_angle: str) -> str:
    angle = clean_visual_phrase(creative_angle)
    if not angle or angle == subject or angle in subject:
        return f"{subject}的关键瞬间，主体动作自然清楚，突出主题识别和商业价值"
    return f"{subject}呈现{angle}，主体动作自然清楚，突出主题识别和商业价值"


def _pick(values: List[str], index: int) -> str:
    if not values:
        return ""
    return values[index % len(values)]


def _build_detailed_script(shot: Dict[str, Any]) -> str:
    secondary = "、".join(str(item) for item in shot.get("subject_secondary", []))
    risks = "；".join(str(item) for item in shot.get("generation_risk_notes", []))
    buyer_use_cases = "、".join(str(item) for item in shot.get("research_basis", {}).get("buyer_use_cases", []))
    market_basis = shot.get("research_basis", {}).get("market_basis", "")
    return (
        f"{shot['shot_title']}。\n"
        f"市场用途：{buyer_use_cases or '企业宣传片、展会大屏、商业视频素材'}。{market_basis}\n"
        f"画面主体是{shot['subject_main']}，辅助元素包括{secondary}。"
        f"{shot['action_description']}。\n"
        f"场景设定：{shot['scene_context']}。"
        f"画面采用{shot['shot_size']}、{shot['camera_angle']}，{shot['camera_movement']}。"
        f"构图要求：{_strip_sentence_end(shot['composition_notes'])}。\n"
        f"光线与质感：{shot['lighting_style']}；色彩体系为{shot['color_palette']}；整体情绪{shot['mood_tone']}。\n"
        f"后续生视频运动意图：{_strip_sentence_end(shot['video_motion_intent'])}。\n"
        f"生成风险与避坑：{risks or '无品牌、无水印、无可读文字，主体结构真实可信。'}"
    )


def _strip_sentence_end(value: Any) -> str:
    return str(value).rstrip("。.!！ ")


def _video_motion_intent_for(scene: Dict[str, Any], shot_size: str, movement: str) -> str:
    text = " ".join([scene.get("subject", ""), scene.get("action", ""), scene.get("context", ""), shot_size])
    if any(keyword in text for keyword in ["机械臂", "机械手", "协作机器人"]):
        return f"{movement}，机械臂完成一次明确的抓取、装配、焊接、扫描或放置动作，动作节奏稳定。"
    if any(keyword in text for keyword in ["AGV", "物流", "仓储", "小车"]):
        return f"{movement}，AGV或物流设备沿既定动线平稳移动，保持工业空间连续。"
    if any(keyword in text for keyword in ["质检", "检测", "扫描", "追溯"]):
        return f"{movement}，检测光线或工业相机完成一次扫描，画面强调精准和可信。"
    if any(keyword in text for keyword in ["工程师", "团队", "巡检", "调试"]):
        return f"{movement}，人物做一个自然专业的小动作，如观察、确认、调试、交接或讨论。"
    if any(keyword in text for keyword in ["中控", "数字孪生", "工业大脑", "数据"]):
        return f"{movement}，真实空间保持稳定，抽象数据层轻微流动但不遮挡主体。"
    if any(keyword in text for keyword in ["全景", "园区", "厂房", "收尾"]):
        return f"{movement}，镜头展示空间纵深和产业规模，主体环境完整可直接剪辑。"
    return f"{movement}，只表现一个清楚动作瞬间，避免多事件串联。"


def _generation_risk_notes_for(group_name: str, scene: Dict[str, Any], avoid_patterns: List[str]) -> List[str]:
    text = " ".join([group_name, scene.get("subject", ""), scene.get("action", ""), scene.get("context", "")])
    risks = list(avoid_patterns)
    if any(keyword in text for keyword in ["机械臂", "机械手", "机器人"]):
        risks.extend(["机械臂关节数量和末端夹具要真实", "避免多余机械手指和变形结构"])
    if any(keyword in text for keyword in ["工程师", "人物", "团队"]):
        risks.extend(["人物手部、五官、工牌和制服细节需要重点质检", "不要出现可识别真实姓名或工牌文字"])
    if any(keyword in text for keyword in ["屏", "数据", "中控", "数字孪生", "平板"]):
        risks.extend(["屏幕只能有抽象图形和色块", "避免真实UI、可读数字、小字和企业系统界面"])
    if any(keyword in text for keyword in ["汽车", "新能源", "电池"]):
        risks.extend(["不要出现车标、具体车型和品牌电池外观"])
    if any(keyword in text for keyword in ["半导体", "芯片", "晶圆", "电子"]):
        risks.extend(["不要出现真实芯片品牌和设备铭牌", "洁净室要真实，避免医疗场景误读"])
    risks.extend(["无Logo", "无水印", "无品牌名", "画面信息完整", "画面完整可直接作为素材使用"])
    return _unique_values(risks)


def _unique_values(values: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _mood_tone_for(style_bible: Dict[str, Any]) -> str:
    if style_bible.get("style_id") == "mid_autumn_tvc_premium_001":
        return "高级、温暖、团圆、克制、东方美学、电影感"
    return "高级、专业、高效、干净、电影感"


def _camera_angle_for(shot_size: str) -> str:
    if "俯拍" in shot_size:
        return "俯拍机位"
    if "低机位" in shot_size:
        return "低机位电影感机位"
    if "特写" in shot_size or "微距" in shot_size:
        return "浅景深近距离机位"
    if "侧面" in shot_size:
        return "侧面机位"
    return "宽幅建立镜头机位"
