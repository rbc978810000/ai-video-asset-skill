"""把调研资料转成代表画面、视觉分类和镜头比例。"""

from __future__ import annotations

from typing import Any, Dict, List

from .production_text import clean_visual_phrase


DEFAULT_MANUFACTURING_TAXONOMY: List[Dict[str, Any]] = [
    {
        "category_name": "片头与制造强国氛围",
        "weight": 6,
        "representative_scenes": ["现代制造产业园清晨外景", "无品牌智能工厂入口", "工业园区道路与高端厂房"],
        "core_elements": ["现代厂房", "道路", "晨光", "宽幅工业环境"],
        "creative_angles": ["低机位建筑纵深", "清晨逆光轮廓", "展会大屏宽幅建立镜头"],
        "commercial_value": "适合片头、品牌形象和宏观叙事开场。",
        "avoid_patterns": ["真实企业标识", "厂牌文字", "杂乱园区"],
        "evidence_keywords": ["智能制造园区", "企业宣传片", "建立镜头"],
    },
    {
        "category_name": "智能工厂全景",
        "weight": 10,
        "representative_scenes": ["现代智能工厂车间全景", "高挑自动化装配车间", "机械臂阵列和产线纵深"],
        "core_elements": ["机械臂", "自动化产线", "AGV小车", "工程师"],
        "creative_angles": ["俯拍产线秩序", "宽幅车间全景", "远景工程师比例尺"],
        "commercial_value": "最能直接说明智能制造主题，适合宣传片和展会大屏。",
        "avoid_patterns": ["脏乱车间", "廉价塑料设备", "过多重复机械臂角度"],
        "evidence_keywords": ["smart factory", "industry 4.0", "robotic arm"],
    },
    {
        "category_name": "AI工业大脑与数字孪生",
        "weight": 10,
        "representative_scenes": ["工业数据中控大屏", "数字孪生工厂可视化", "生产线虚实叠加画面"],
        "core_elements": ["控制台", "抽象数据图形", "虚拟工厂模型", "工程师侧影"],
        "creative_angles": ["真实工厂叠加克制数据层", "中控室侧逆光", "数字孪生模型悬浮构图"],
        "commercial_value": "体现 AI、数字化和未来感，适合技术卖点段落。",
        "avoid_patterns": ["可读文字", "廉价全息屏", "过度蓝色科幻光效"],
        "evidence_keywords": ["数字孪生", "工业大脑", "IoT传感器"],
    },
    {
        "category_name": "自动化生产线与机械臂",
        "weight": 10,
        "representative_scenes": ["机械臂精准装配工件", "自动化检测设备扫描", "多机械臂协同作业"],
        "core_elements": ["机械臂", "夹具", "传送带", "金属零件", "传感器"],
        "creative_angles": ["末端夹具微距", "侧面产线节奏", "机械臂阵列俯拍"],
        "commercial_value": "工业素材最强识别点，适合通用商业素材销售。",
        "avoid_patterns": ["机械结构畸形", "手部异常", "设备比例错误"],
        "evidence_keywords": ["机械臂", "自动化", "生产线"],
    },
    {
        "category_name": "芯片半导体与精密制造",
        "weight": 8,
        "representative_scenes": ["晶圆检测设备微距特写", "洁净室工程师托举晶圆盒", "芯片检测工位冷白光特写"],
        "core_elements": ["晶圆", "无尘服", "精密探针", "洁净室"],
        "creative_angles": ["晶圆反光微距", "浅景深探针检测", "洁净室玻璃反射"],
        "commercial_value": "提高素材高端感和技术含量，适合科技制造主题。",
        "avoid_patterns": ["真实芯片品牌", "乱码文字", "过度科幻电路图"],
        "evidence_keywords": ["半导体", "晶圆", "精密制造"],
    },
    {
        "category_name": "新能源汽车与高端装备",
        "weight": 8,
        "representative_scenes": ["新能源汽车电池包装配", "高端装备金属部件检测", "大型装备数字化检测"],
        "core_elements": ["电池模组", "大型金属结构", "激光检测头", "工程师"],
        "creative_angles": ["电池模组俯拍", "大型装备低机位", "检测光线扫过金属表面"],
        "commercial_value": "覆盖高需求行业素材，提升素材包市场宽度。",
        "avoid_patterns": ["车标", "具体车型", "品牌电池外观"],
        "evidence_keywords": ["新能源汽车", "高端装备", "电池模组"],
    },
    {
        "category_name": "研发实验室与工程师",
        "weight": 8,
        "representative_scenes": ["研发实验室工程师观察样机", "工程师团队讨论工业模型", "实验台精密传感器调试"],
        "core_elements": ["工程师", "实验台", "样机", "控制台"],
        "creative_angles": ["人物侧影与设备层次", "手部操作特写", "团队协同中景"],
        "commercial_value": "补足人物与可信度，适合企业宣传和招聘科技感段落。",
        "avoid_patterns": ["摆拍过度", "白大褂医疗感", "可读屏幕文字"],
        "evidence_keywords": ["工程师", "研发实验室", "协同"],
    },
    {
        "category_name": "数字化转型与管理协同",
        "weight": 8,
        "representative_scenes": ["管理人员查看生产数据看板", "工厂移动终端巡检", "会议室生产调度协同"],
        "core_elements": ["会议室", "抽象图表", "平板设备", "管理人员"],
        "creative_angles": ["玻璃墙反射", "平板前景虚化", "多人协同背影"],
        "commercial_value": "适合讲企业管理、降本增效、数字化转型。",
        "avoid_patterns": ["真实 UI", "可读数字文字", "办公室普通化"],
        "evidence_keywords": ["数字化转型", "管理协同", "数据看板"],
    },
    {
        "category_name": "绿色制造与新型储能",
        "weight": 6,
        "representative_scenes": ["绿色智能工厂屋顶光伏", "储能设备整齐排列", "低碳工厂能源管理画面"],
        "core_elements": ["光伏板", "储能柜", "清朗天空", "维护工程师"],
        "creative_angles": ["屋顶光伏航拍感", "储能通道纵深", "绿色低碳完整画面"],
        "commercial_value": "覆盖 ESG、绿色制造、新能源活动视频需求。",
        "avoid_patterns": ["具体品牌能源柜", "过度绿色滤镜", "不真实自然环境"],
        "evidence_keywords": ["绿色制造", "储能", "光伏"],
    },
    {
        "category_name": "产业升级与未来制造收尾",
        "weight": 6,
        "representative_scenes": ["未来制造产线纵深收尾", "真实工厂叠加克制数字光层", "自动化设备与远处工程师剪影"],
        "core_elements": ["产线纵深", "蓝银光线", "工程师剪影", "完整工业背景"],
        "creative_angles": ["慢推收尾感", "远景人物剪影", "抽象数字光层"],
        "commercial_value": "适合结尾、愿景和预告片氛围。",
        "avoid_patterns": ["空洞科幻城市", "太多粒子光效", "脱离制造业主体"],
        "evidence_keywords": ["未来制造", "产业升级", "收尾镜头"],
    },
]


DEFAULT_MID_AUTUMN_TAXONOMY: List[Dict[str, Any]] = [
    {
        "category_name": "月圆节日建立镜头",
        "weight": 4,
        "representative_scenes": ["金色满月悬在中国城市天际线上方", "江南屋檐与圆月同框", "庭院桂花树下的中秋夜色"],
        "core_elements": ["满月", "中国城市", "屋檐", "桂花", "暖金夜色"],
        "creative_angles": ["宽幅月圆建立镜头", "屋檐前景虚化", "桂花枝叶框住满月"],
        "commercial_value": "快速建立中秋节日识别，适合 TVC 开场和片头。",
        "avoid_patterns": ["廉价大月亮贴图", "过度卡通", "不真实星空", "品牌楼宇标识"],
        "evidence_keywords": ["满月", "赏月", "中秋夜景"],
    },
    {
        "category_name": "月饼产品与礼盒质感",
        "weight": 5,
        "representative_scenes": ["高端月饼礼盒打开的产品特写", "月饼切面与流心内馅微距", "月饼与中国茶具的暖光静物"],
        "core_elements": ["月饼", "礼盒", "茶具", "木质桌面", "暖金光"],
        "creative_angles": ["浅景深产品特写", "礼盒开合动作瞬间", "月饼纹样微距"],
        "commercial_value": "适合食品、礼盒、节日促销和 TVC 产品段落。",
        "avoid_patterns": ["品牌包装", "过小包装文字", "过度油腻", "月饼纹样乱码"],
        "evidence_keywords": ["月饼", "礼盒", "茶"],
    },
    {
        "category_name": "中国家庭团圆",
        "weight": 5,
        "representative_scenes": ["中国三代家庭围坐餐桌分享月饼", "母亲给孩子递灯笼的温暖瞬间", "一家人在阳台赏月的背影"],
        "core_elements": ["中国家庭", "老人", "父母", "孩子", "餐桌", "月饼"],
        "creative_angles": ["桌面食物前景虚化", "窗边月光逆光", "家庭背影与环境层次"],
        "commercial_value": "中秋最核心的情绪资产，适合团圆主题广告。",
        "avoid_patterns": ["人物表情夸张", "西式家庭场景", "不自然摆拍", "餐桌杂乱"],
        "evidence_keywords": ["团圆", "家庭", "mooncake family"],
    },
    {
        "category_name": "灯笼夜景与节日街巷",
        "weight": 4,
        "representative_scenes": ["一家人提着灯笼走在中式街巷回家", "祖孙在院落门口递纸灯笼", "灯笼街巷尽头窗内透出团圆暖光"],
        "core_elements": ["灯笼", "家人同行", "返家", "街巷", "院落", "暖光", "团圆情绪"],
        "creative_angles": ["灯笼前景散景包住家人背影", "低机位跟随祖孙递灯笼", "红灯笼暖光与窗内团圆光对比"],
        "commercial_value": "把灯笼夜景转化为有团圆关系的节日情绪画面，适合中秋TVC情绪段落。",
        "avoid_patterns": ["只有灯笼没有人物关系", "灯笼文字过小", "景区商标", "廉价霓虹", "拥挤杂乱人群"],
        "evidence_keywords": ["灯笼", "夜景", "节日街巷", "团圆", "返家"],
    },
    {
        "category_name": "桂花茶席与东方生活美学",
        "weight": 3,
        "representative_scenes": ["桂花落在茶盏旁的静物特写", "中式茶席上月饼与热茶蒸汽", "窗边桂花枝影映在桌面"],
        "core_elements": ["桂花", "茶盏", "热茶", "月饼", "东方生活美学"],
        "creative_angles": ["桂花微距", "热茶蒸汽逆光", "窗影与桌面层次"],
        "commercial_value": "提供高级、安静、有质感的中秋素材，用于品牌情绪段落。",
        "avoid_patterns": ["过度古风滤镜", "茶具品牌字", "小字标签", "桌面脏乱"],
        "evidence_keywords": ["桂花", "茶", "东方美学"],
    },
    {
        "category_name": "国风意象与玉兔月宫",
        "weight": 3,
        "representative_scenes": ["写实国风玉兔剪影与圆月", "月宫云雾意象的高级广告画面", "丝绸飘带与满月形成东方构图"],
        "core_elements": ["玉兔", "圆月", "云雾", "丝绸", "国风"],
        "creative_angles": ["剪影构图", "月光云雾层次", "高级写实国风静帧"],
        "commercial_value": "提供创意和记忆点，适合预告片和品牌视觉段落。",
        "avoid_patterns": ["卡通嫦娥", "版权角色", "低幼插画", "过度仙侠"],
        "evidence_keywords": ["玉兔", "嫦娥", "月宫", "国风"],
    },
    {
        "category_name": "现代城市团聚与返家",
        "weight": 3,
        "representative_scenes": ["年轻中国人提着礼盒回家入门", "城市高层窗边一家人看月亮", "夜晚小区窗户透出温暖灯光"],
        "core_elements": ["城市住宅", "礼盒", "家门", "窗边", "暖光"],
        "creative_angles": ["门口递礼盒手部特写", "窗内暖光与窗外满月", "城市万家灯火宽幅"],
        "commercial_value": "连接传统节日和现代生活，适合年轻消费品牌 TVC。",
        "avoid_patterns": ["外国城市感", "楼宇广告牌", "可读门牌小字", "冷漠商业办公楼"],
        "evidence_keywords": ["返家", "团聚", "城市中秋"],
    },
    {
        "category_name": "祝福收尾与完整画面",
        "weight": 2,
        "representative_scenes": ["月饼茶席旁形成完整东方生活画面", "满月与桂花枝形成收尾构图", "家庭背影看月亮的温暖收尾"],
        "core_elements": ["满月", "桂花", "茶席", "家庭背影", "完整节日氛围"],
        "creative_angles": ["干净完整构图", "温暖逆光收尾", "TVC 片尾构图"],
        "commercial_value": "适合广告片尾、祝福语上字和海报延展。",
        "avoid_patterns": ["画面过满", "小字预生成", "Logo占位", "低清晰度背景"],
        "evidence_keywords": ["祝福", "片尾", "完整画面"],
    },
]


def build_visual_research_outputs(
    user_input: Dict[str, Any],
    source_notes: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    source_notes = source_notes or []
    taxonomy = _taxonomy_for_topic(user_input, source_notes)
    total_shots = int(user_input["user_input_total_shots"])
    market_signal_map = _build_market_signal_map(user_input, taxonomy, source_notes)
    visual_demand_matrix = _build_visual_demand_matrix(taxonomy, market_signal_map, user_input)
    shot_group_plan = _custom_shot_group_plan(user_input) or _allocate_shot_counts(visual_demand_matrix, total_shots)
    representative_visuals = _representative_visuals(taxonomy, source_notes)
    creative_angles = _creative_angles(taxonomy)
    return {
        "source_notes": source_notes,
        "visual_taxonomy": taxonomy,
        "market_signal_map": market_signal_map,
        "visual_demand_matrix": visual_demand_matrix,
        "representative_visuals": representative_visuals,
        "creative_angles": creative_angles,
        "shot_group_plan": shot_group_plan,
    }


def _custom_shot_group_plan(user_input: Dict[str, Any]) -> List[Dict[str, Any]] | None:
    custom_plan = user_input.get("user_input_shot_group_plan")
    if not isinstance(custom_plan, list) or not custom_plan:
        return None
    normalized = []
    for index, item in enumerate(custom_plan, start=1):
        if not isinstance(item, dict):
            continue
        group_name = item.get("group_name") or item.get("category_name") or f"自定义镜头组{index}"
        shot_count = int(item.get("shot_count", 1))
        normalized.append(
            {
                "group_name": group_name,
                "shot_count": max(1, shot_count),
                "reason": item.get("reason", "用户指定镜头组配比。"),
                "market_demand_score": item.get("market_demand_score"),
                "ai_generation_feasibility": item.get("ai_generation_feasibility"),
                "video_motion_potential": item.get("video_motion_potential"),
                "commercial_reuse_value": item.get("commercial_reuse_value"),
                "risk_score": item.get("risk_score"),
                "recommended_anchor_strategy": item.get("recommended_anchor_strategy", ""),
                "market_basis": item.get("market_basis", ""),
                "buyer_use_cases": item.get("buyer_use_cases", []),
                "representative_scenes": item.get("representative_scenes", []),
                "core_elements": item.get("core_elements", []),
                "creative_angles": item.get("creative_angles", []),
                "avoid_patterns": item.get("avoid_patterns", []),
                "evidence_keywords": item.get("evidence_keywords", []),
            }
        )
    return normalized or None


def _taxonomy_for_topic(user_input: Dict[str, Any], source_notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    topic_text = f"{user_input['user_input_topic_title']} {user_input['user_input_industry_name']} {user_input.get('user_input_visual_style', '')}"
    if any(keyword in topic_text for keyword in ["中秋", "月饼", "团圆", "赏月", "灯笼", "桂花"]):
        taxonomy = [dict(item) for item in DEFAULT_MID_AUTUMN_TAXONOMY]
    elif any(keyword in topic_text for keyword in ["制造", "工厂", "工业", "机械臂", "智能"]):
        taxonomy = [dict(item) for item in DEFAULT_MANUFACTURING_TAXONOMY]
    else:
        taxonomy = _generic_taxonomy(user_input)

    _boost_taxonomy_from_notes(taxonomy, source_notes)
    return taxonomy


def _generic_taxonomy(user_input: Dict[str, Any]) -> List[Dict[str, Any]]:
    topic = clean_visual_phrase(user_input["user_input_topic_title"], fallback=user_input["user_input_topic_title"])
    industry = user_input["user_input_industry_name"]
    return [
        {
            "category_name": "主题建立镜头",
            "weight": 8,
            "representative_scenes": [f"{industry}相关空间或场景全景", f"{topic}核心环境建立镜头"],
            "core_elements": [industry, "环境", "空间层次", "完整背景"],
            "creative_angles": ["宽幅建立镜头", "低机位纵深", "干净完整构图"],
            "commercial_value": "建立主题识别和视频开场氛围。",
            "avoid_patterns": ["品牌标识", "杂乱背景", "不清楚主题"],
            "evidence_keywords": [industry, topic],
        },
        {
            "category_name": "核心流程与动作",
            "weight": 12,
            "representative_scenes": [f"{topic}核心工作流程", f"{industry}关键动作瞬间"],
            "core_elements": ["主体动作", "工具设备", "流程节点"],
            "creative_angles": ["中景动作画面", "侧面跟拍感", "关键动作特写"],
            "commercial_value": "让素材可用于解释业务和产品能力。",
            "avoid_patterns": ["多事件串联", "动作含混", "主体不明确"],
            "evidence_keywords": ["流程", "动作", "工作流"],
        },
        {
            "category_name": "人物与协同",
            "weight": 8,
            "representative_scenes": [f"{industry}专业人员工作画面", "团队协同讨论画面"],
            "core_elements": ["专业人员", "自然协作", "工作空间"],
            "creative_angles": ["人物侧影", "手部操作", "团队中景"],
            "commercial_value": "增加真实感和企业宣传片适用性。",
            "avoid_patterns": ["过度摆拍", "夸张表情", "可读文字"],
            "evidence_keywords": ["人物", "团队", "协同"],
        },
        {
            "category_name": "技术与数据可视化",
            "weight": 8,
            "representative_scenes": ["抽象数据界面", "技术系统可视化", "无文字数据图形"],
            "core_elements": ["数据层", "屏幕", "控制界面"],
            "creative_angles": ["克制科技叠加", "屏幕前景虚化", "抽象图表层次"],
            "commercial_value": "体现科技感和信息化价值。",
            "avoid_patterns": ["乱码文字", "廉价全息屏", "过度蓝光"],
            "evidence_keywords": ["数据", "可视化", "技术"],
        },
        {
            "category_name": "细节特写与质感",
            "weight": 8,
            "representative_scenes": ["核心设备或产品细节", "材质和工艺特写"],
            "core_elements": ["细节", "材质", "浅景深"],
            "creative_angles": ["微距特写", "反光材质", "手部与工具局部"],
            "commercial_value": "提升素材高级感和剪辑节奏。",
            "avoid_patterns": ["主体变形", "噪点", "廉价材质"],
            "evidence_keywords": ["细节", "特写", "质感"],
        },
        {
            "category_name": "价值结果与收尾",
            "weight": 6,
            "representative_scenes": ["成果展示画面", "未来感收尾画面"],
            "core_elements": ["成果", "空间纵深", "愿景氛围"],
            "creative_angles": ["远景收尾", "干净背景", "情绪光线"],
            "commercial_value": "适合视频结尾、价值总结和预告片段落。",
            "avoid_patterns": ["空泛抽象", "脱离主题", "过度装饰"],
            "evidence_keywords": ["成果", "价值", "未来"],
        },
    ]


def _boost_taxonomy_from_notes(taxonomy: List[Dict[str, Any]], source_notes: List[Dict[str, Any]]) -> None:
    if not source_notes:
        return
    note_text = " ".join(
        " ".join(str(value) for value in note.values())
        for note in source_notes
        if isinstance(note, dict)
    )
    for item in taxonomy:
        hit_count = sum(1 for keyword in item.get("evidence_keywords", []) if keyword and keyword in note_text)
        if hit_count:
            item["weight"] = int(item["weight"]) + min(hit_count, 3)
            item.setdefault("research_note", "该分类在外部调研笔记中出现，镜头比例略微提高。")


def _build_market_signal_map(
    user_input: Dict[str, Any],
    taxonomy: List[Dict[str, Any]],
    source_notes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """把调研来源转成可用于镜头决策的市场信号。"""

    target_usage = user_input.get("user_input_target_usage", [])
    signal_map: List[Dict[str, Any]] = []
    for item in taxonomy:
        matched_sources = _matched_sources_for_taxonomy(item, source_notes)
        matched_visuals = _unique_values(
            visual
            for note in matched_sources
            for visual in note.get("representative_visuals", [])
        )
        matched_keywords = _unique_values(
            keyword
            for note in matched_sources
            for keyword in _as_list(note.get("keywords", [])) + _as_list(note.get("related_keywords", []))
        )
        high_purchase_examples = _unique_values(
            example
            for note in matched_sources
            for example in _as_list(note.get("high_purchase_examples", []))
        )
        source_titles = _unique_values(
            note.get("title") or note.get("source_type", "")
            for note in matched_sources
            if note.get("title") or note.get("source_type")
        )
        source_hit_count = len(matched_sources)
        visual_hit_count = len(matched_visuals)
        base_weight = max(1, int(item.get("weight", 1)))
        numeric_signal = sum(_numeric_market_signal(note) for note in matched_sources)
        market_demand_score = min(
            10,
            max(1, round(base_weight / 2 + source_hit_count * 0.8 + visual_hit_count * 0.25 + numeric_signal)),
        )
        signal_map.append(
            {
                "visual_type": item["category_name"],
                "market_demand_score": market_demand_score,
                "target_usage": target_usage,
                "matched_source_count": source_hit_count,
                "matched_sources": [
                    {
                        "source_id": note.get("source_id", ""),
                        "source_type": note.get("source_type", ""),
                        "title": note.get("title", ""),
                        "url": note.get("url", ""),
                        "summary": note.get("summary", ""),
                    }
                    for note in matched_sources
                ],
                "market_keywords": _unique_values(
                    list(item.get("evidence_keywords", [])) + matched_keywords
                ),
                "high_purchase_examples": high_purchase_examples,
                "high_value_visual_patterns": high_purchase_examples or matched_visuals or item.get("representative_scenes", []),
                "buyer_use_cases": _buyer_use_cases_for(item["category_name"], target_usage),
                "avoid_notes": _unique_values(
                    list(item.get("avoid_patterns", []))
                    + [
                        avoid_note
                        for note in matched_sources
                        for avoid_note in note.get("avoid_notes", [])
                    ]
                ),
                "evidence_summary": _market_evidence_summary(item, source_hit_count, source_titles),
            }
        )
    return signal_map


def _build_visual_demand_matrix(
    taxonomy: List[Dict[str, Any]],
    market_signal_map: List[Dict[str, Any]],
    user_input: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """把市场信号、AI可生成性和视频适配性转成镜头分配权重。"""

    signal_by_type = {item["visual_type"]: item for item in market_signal_map}
    matrix: List[Dict[str, Any]] = []
    for item in taxonomy:
        visual_type = item["category_name"]
        signal = signal_by_type.get(visual_type, {})
        avoid_notes = signal.get("avoid_notes", item.get("avoid_patterns", []))
        market_demand_score = int(signal.get("market_demand_score", max(1, int(item.get("weight", 1)))))
        risk_score = _risk_score_for(item, avoid_notes)
        ai_generation_feasibility = max(1, 11 - risk_score)
        video_motion_potential = _video_motion_score_for(item)
        commercial_reuse_value = _commercial_reuse_score_for(item, signal, user_input)
        recommended_weight = round(
            market_demand_score * 0.38
            + ai_generation_feasibility * 0.18
            + video_motion_potential * 0.2
            + commercial_reuse_value * 0.2
            - risk_score * 0.12,
            2,
        )
        recommended_weight = max(1.0, recommended_weight)
        matrix.append(
            {
                "visual_type": visual_type,
                "market_demand_score": market_demand_score,
                "ai_generation_feasibility": ai_generation_feasibility,
                "video_motion_potential": video_motion_potential,
                "commercial_reuse_value": commercial_reuse_value,
                "risk_score": risk_score,
                "recommended_weight": recommended_weight,
                "recommended_anchor_strategy": _anchor_strategy_for(item, risk_score),
                "market_basis": signal.get("evidence_summary", ""),
                "buyer_use_cases": signal.get("buyer_use_cases", []),
                "high_value_visual_patterns": signal.get("high_value_visual_patterns", []),
                "risk_notes": avoid_notes,
                "decision_reason": _decision_reason(
                    visual_type,
                    market_demand_score,
                    ai_generation_feasibility,
                    video_motion_potential,
                    commercial_reuse_value,
                    risk_score,
                ),
                "taxonomy": item,
            }
        )
    return matrix


def _allocate_shot_counts(visual_demand_matrix: List[Dict[str, Any]], total_shots: int) -> List[Dict[str, Any]]:
    total_weight = sum(max(1.0, float(item.get("recommended_weight", 1))) for item in visual_demand_matrix)
    allocations = []
    remaining = total_shots
    for index, item in enumerate(visual_demand_matrix):
        taxonomy_item = item.get("taxonomy", {})
        if index == len(visual_demand_matrix) - 1:
            count = remaining
        else:
            raw = total_shots * max(1.0, float(item.get("recommended_weight", 1))) / total_weight
            count = max(1, int(round(raw)))
            count = min(count, remaining - (len(visual_demand_matrix) - index - 1))
        remaining -= count
        allocations.append(
            {
                "group_name": item["visual_type"],
                "shot_count": count,
                "reason": item.get("decision_reason") or taxonomy_item.get("commercial_value", ""),
                "market_demand_score": item.get("market_demand_score"),
                "ai_generation_feasibility": item.get("ai_generation_feasibility"),
                "video_motion_potential": item.get("video_motion_potential"),
                "commercial_reuse_value": item.get("commercial_reuse_value"),
                "risk_score": item.get("risk_score"),
                "recommended_anchor_strategy": item.get("recommended_anchor_strategy", ""),
                "market_basis": item.get("market_basis", ""),
                "buyer_use_cases": item.get("buyer_use_cases", []),
                "representative_scenes": taxonomy_item.get("representative_scenes", []),
                "core_elements": taxonomy_item.get("core_elements", []),
                "creative_angles": taxonomy_item.get("creative_angles", []),
                "avoid_patterns": taxonomy_item.get("avoid_patterns", []),
                "evidence_keywords": taxonomy_item.get("evidence_keywords", []),
            }
        )
    return allocations


def _matched_sources_for_taxonomy(
    taxonomy_item: Dict[str, Any],
    source_notes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    keywords = _unique_values(
        list(taxonomy_item.get("evidence_keywords", []))
        + list(taxonomy_item.get("core_elements", []))
        + [taxonomy_item.get("category_name", "")]
    )
    matched = []
    for note in source_notes:
        note_text = " ".join(str(value) for value in note.values())
        hit_count = sum(1 for keyword in keywords if keyword and keyword in note_text)
        has_strong_hit = any(keyword and len(keyword) >= 4 and keyword in note_text for keyword in keywords)
        if hit_count >= 2 or has_strong_hit:
            matched.append(note)
    return matched


def _numeric_market_signal(note: Dict[str, Any]) -> float:
    score = 0.0
    for key in ["purchase_count", "download_count"]:
        value = note.get(key)
        if isinstance(value, (int, float)):
            score += min(2.5, float(value) / 200)
    result_count = note.get("search_result_count")
    if isinstance(result_count, (int, float)):
        score += min(1.5, float(result_count) / 5000)
    return score


def _buyer_use_cases_for(category_name: str, target_usage: List[str]) -> List[str]:
    base_usage = target_usage[:3]
    if any(keyword in category_name for keyword in ["建立", "片头", "月圆", "全景"]):
        return _unique_values(base_usage + ["开场建立镜头", "转场空镜", "展会大屏背景"])
    if any(keyword in category_name for keyword in ["产品", "月饼", "芯片", "装备", "细节"]):
        return _unique_values(base_usage + ["产品卖点段落", "电商活动视频", "商业素材销售"])
    if any(keyword in category_name for keyword in ["家庭", "人物", "工程师", "团圆", "返家"]):
        return _unique_values(base_usage + ["人物情绪段落", "品牌故事", "社媒短片"])
    if any(keyword in category_name for keyword in ["收尾", "祝福", "未来"]):
        return _unique_values(base_usage + ["片尾收束", "祝福段落", "预告片收束"])
    return _unique_values(base_usage + ["主体说明段落", "剪辑补充镜头"])


def _market_evidence_summary(
    taxonomy_item: Dict[str, Any],
    source_hit_count: int,
    source_titles: List[str],
) -> str:
    if source_hit_count:
        titles = "、".join(source_titles[:3]) if source_titles else "外部调研来源"
        return f"命中 {source_hit_count} 个调研来源：{titles}；该组用于{taxonomy_item.get('commercial_value', '')}"
    return f"未命中外部调研来源，使用内置主题 taxonomy 作为冷启动依据：{taxonomy_item.get('commercial_value', '')}"


def _risk_score_for(taxonomy_item: Dict[str, Any], avoid_notes: List[str]) -> int:
    text = " ".join(
        [taxonomy_item.get("category_name", "")]
        + taxonomy_item.get("representative_scenes", [])
        + taxonomy_item.get("core_elements", [])
        + avoid_notes
    )
    risk = 2
    high_risk_keywords = ["品牌", "Logo", "logo", "文字", "小字", "乱码", "真实UI", "可读"]
    anatomy_keywords = ["人物", "家庭", "手部", "五官", "孩子", "工程师", "祖孙"]
    complexity_keywords = ["拥挤", "人群", "密集", "复杂", "机械结构", "月饼纹样", "包装"]
    if any(keyword in text for keyword in high_risk_keywords):
        risk += 2
    if any(keyword in text for keyword in anatomy_keywords):
        risk += 2
    if any(keyword in text for keyword in complexity_keywords):
        risk += 2
    if any(keyword in text for keyword in ["版权角色", "嫦娥", "玉兔", "厂牌", "车型"]):
        risk += 1
    return min(10, max(1, risk))


def _video_motion_score_for(taxonomy_item: Dict[str, Any]) -> int:
    text = " ".join(
        [taxonomy_item.get("category_name", "")]
        + taxonomy_item.get("representative_scenes", [])
        + taxonomy_item.get("creative_angles", [])
    )
    score = 5
    if any(keyword in text for keyword in ["行走", "递", "打开", "升起", "倒", "装配", "扫描", "巡视", "分享"]):
        score += 3
    if any(keyword in text for keyword in ["全景", "建立", "纵深", "空镜", "收尾"]):
        score += 1
    if any(keyword in text for keyword in ["静物", "特写", "微距"]):
        score += 1
    return min(10, score)


def _commercial_reuse_score_for(
    taxonomy_item: Dict[str, Any],
    market_signal: Dict[str, Any],
    user_input: Dict[str, Any],
) -> int:
    text = " ".join(
        [taxonomy_item.get("category_name", ""), taxonomy_item.get("commercial_value", "")]
        + taxonomy_item.get("representative_scenes", [])
        + market_signal.get("buyer_use_cases", [])
        + user_input.get("user_input_target_usage", [])
    )
    score = 5
    if any(keyword in text for keyword in ["TVC", "宣传片", "展会", "电商", "素材销售", "商业"]):
        score += 2
    if any(keyword in text for keyword in ["完整", "片头", "片尾", "产品", "情绪", "转场"]):
        score += 2
    if any(keyword in text for keyword in ["Logo", "品牌", "版权"]):
        score -= 1
    return min(10, max(1, score))


def _anchor_strategy_for(taxonomy_item: Dict[str, Any], risk_score: int) -> str:
    text = " ".join(
        [taxonomy_item.get("category_name", "")]
        + taxonomy_item.get("representative_scenes", [])
        + taxonomy_item.get("core_elements", [])
    )
    if any(keyword in text for keyword in ["家庭", "人物", "工程师", "礼盒", "工厂", "车间", "街巷", "茶席"]):
        return "必须先生成 anchor，通过后再扩展同场景多景别，控制人物、空间、产品或设备一致性。"
    if risk_score >= 7:
        return "建议先生成 1 张低风险 anchor 验证主体和风格，再决定是否扩展。"
    return "可按普通分镜生成；如后续需要连续剪辑，再追加 anchor 扩展。"


def _decision_reason(
    visual_type: str,
    market_demand_score: int,
    ai_generation_feasibility: int,
    video_motion_potential: int,
    commercial_reuse_value: int,
    risk_score: int,
) -> str:
    return (
        f"{visual_type}：市场需求 {market_demand_score}/10，AI可生成性 {ai_generation_feasibility}/10，"
        f"视频动作潜力 {video_motion_potential}/10，商业复用 {commercial_reuse_value}/10，"
        f"风险 {risk_score}/10；按综合分配镜头数量。"
    )


def _unique_values(values: Any) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _representative_visuals(taxonomy: List[Dict[str, Any]], source_notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    visuals = []
    visual_index = 1
    for item in taxonomy:
        for scene in item.get("representative_scenes", []):
            visuals.append(
                {
                    "visual_id": f"visual_{visual_index:03d}",
                    "category_name": item["category_name"],
                    "scene": scene,
                    "core_elements": item.get("core_elements", []),
                    "commercial_value": item.get("commercial_value", ""),
                    "avoid_patterns": item.get("avoid_patterns", []),
                }
            )
            visual_index += 1
    for note in source_notes:
        for scene in note.get("representative_visuals", []):
            visuals.append(
                {
                    "visual_id": f"visual_{visual_index:03d}",
                    "category_name": "外部调研补充画面",
                    "scene": scene,
                    "core_elements": note.get("keywords", []),
                    "commercial_value": note.get("summary", ""),
                    "avoid_patterns": note.get("avoid_notes", []),
                    "source_id": note.get("source_id", ""),
                    "url": note.get("url", ""),
                }
            )
            visual_index += 1
    return visuals


def _creative_angles(taxonomy: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    angles = []
    angle_index = 1
    for item in taxonomy:
        for angle in item.get("creative_angles", []):
            angles.append(
                {
                    "angle_id": f"angle_{angle_index:03d}",
                    "category_name": item["category_name"],
                    "creative_angle": angle,
                    "usage_hint": "用于生成同主题但不撞图的差异化镜头。",
                    "avoid_patterns": item.get("avoid_patterns", []),
                }
            )
            angle_index += 1
    return angles
