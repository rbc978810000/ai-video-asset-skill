《AI视频素材分镜+生图 Skill PRD v1.0》
1. 项目目标

我要构建一个用于 AI视频素材商业化生产 的 Skill 工作流。

主要用途是：
为宣传片、活动视频、展会视频、预告片、TVC、企业宣传片等场景，批量生成可售卖的 AI 视频素材前置资产。

当前阶段先做：

选题分镜生成
分镜对应生图
每个选题独立工程文件夹
每条分镜独立图片文件夹
支持失败重试
支持图片不满意时重新生成并替换当前图
支持基于一张满意图扩展更多角度、景别、连贯分镜画面

后续再接视频生成。

2. 核心设计原则
2.1 一镜一场

每条分镜只描述一个明确画面，不要把多个动作塞进同一条分镜。
例如不要写：
“工程师进入车间，看大屏，操作机器人，最后展示芯片。”

要拆成：

工程师走入智能工厂主通道
工程师查看工业数据大屏
机械臂在产线上精准装配
芯片检测设备微距特写

短视频生成官方最佳实践也建议短镜头聚焦单一场景，多个事件应拆成多个 clip。【turn113644view1†L1237-L1248】

2.2 每条分镜都必须适合生图和后续生视频

分镜不是普通文案，而是 生产型分镜。
每条分镜必须包含：

主体
动作
场景
景别
机位
运镜感
构图
光线
风格
留白位置
负面限制词

视频提示词里，主体、动作、机位、运镜、视觉风格、光线、氛围等都会明显影响生成结果。【turn879759view1†L1227-L1275】【turn879759view0†L1311-L1372】【turn879759view4†L1407-L1481】

2.3 风格统一

每个选题必须有自己的 style_bible.json。
这个文件用来锁定：

行业风格
色彩体系
光线风格
场景质感
人物风格
设备风格
禁止元素

如果某个工程师、工厂、设备需要连续出现，要复用固定描述。连续镜头要保持角色/主体一致时，官方建议反复使用固定描述，并尽量使用同一 seed。【turn113644view0†L1265-L1268】

2.4 商业素材可售性优先

生成的内容要满足商业视频素材需求：

画面清晰
构图高级
适合后期加字
不要 logo
不要品牌名
不要水印
不要明显文字
不要版权角色
不要太多重复角度
不要脏乱、畸形、廉价感

商业图库对素材的核心要求也是：质量高、构图好、曝光合适、不要 logo/商标/水印/文字、避免大量相似图。【turn432069view2†L70-L79】【turn432069view1†L96-L125】【turn432069view1†L159-L161】【turn432069view3†L390-L394】

3. Skill 总体架构

建议拆成 6 个模块。

ai_video_asset_skill/
  main_orchestrator.py
  storyboard_planner.py
  image_prompt_builder.py
  image_generator_adapter.py
  image_review_engine.py
  variation_expander.py
  file_manager.py
  config.py
  README.md
3.1 main_orchestrator.py

总控模块。

负责：

接收用户输入
创建选题工程文件夹
调用分镜规划模块
调用生图模块
调用质检模块
调用重生模块
更新 manifest
输出最终结果
3.2 storyboard_planner.py

分镜规划模块。

负责：

根据选题生成分镜表
每条分镜输出结构化 JSON
保存总分镜表
保存单条分镜文件
3.3 image_prompt_builder.py

生图提示词组装模块。

负责：

读取每条分镜 JSON
结合 style_bible.json
拼接成最终生图 prompt
同时生成负面提示词
3.4 image_generator_adapter.py

生图适配层。

负责：

对接 Codex 当前环境的内置生图能力
或者预留第三方模型接口
输入 prompt
返回图片路径或图片 URL
保存到对应分镜文件夹

注意：
这里不要把模型接口写死。要设计成 adapter，后面可以换成：

OpenAI image
Gemini image
即梦 / Seedream
MJ 中转
自己画布里的生图 API
3.5 image_review_engine.py

图片质检模块。

负责检查：

是否成功生成
是否文件存在
是否主体符合分镜
是否有 logo
是否有文字
是否有水印
是否明显畸形
是否画面高级
是否有留白
是否风格统一

输出：

{
  "review_status": "approved",
  "score": 92,
  "failure_reasons": [],
  "suggested_fix_prompt": ""
}
3.6 variation_expander.py

连贯扩展模块。

负责：

读取某张满意图作为锚点图
根据锚点图生成更多角度 / 景别 / 构图
保存到 /04_variations/
形成可剪辑的连续镜头组
4. 项目目录结构

每个选题都要建立独立工程文件夹。

/projects/
  /2026-06-23_制造业_智能工厂AI视频素材/
    project_manifest.json
    topic_brief.md
    style_bible.json

    /01_storyboard/
      storyboard_master.json
      storyboard_master.csv
      shot_001.json
      shot_002.json
      shot_003.json
      ...

    /02_image_prompts/
      shot_001_prompt.json
      shot_002_prompt.json
      shot_003_prompt.json
      ...

    /03_images/
      /shot_001/
        v1.png
        v2.png
        current.png
        review.json
      /shot_002/
        v1.png
        current.png
        review.json

    /04_variations/
      /shot_001/
        anchor.png
        closeup_v1.png
        wide_v1.png
        side_angle_v1.png
        top_view_v1.png
        variation_manifest.json

    /05_review/
      failed_queue.json
      retry_log.json
      approved_list.json
      replace_history.json

    /06_exports/
      contact_sheet.jpg
      delivery_index.csv
      approved_manifest.json
5. 输入参数设计
5.1 总控 Skill 输入
{
  "user_input_topic_title": "制造业智能工厂AI视频素材",
  "user_input_industry_name": "制造业",
  "user_input_total_shots": 80,
  "user_input_target_usage": ["宣传片", "展会", "活动", "TVC", "预告片"],
  "user_input_visual_style": "高端科技工业风，真实摄影质感，蓝银色调，现代智能工厂",
  "user_input_aspect_ratio": "16:9",
  "user_input_output_root_dir": "./projects",
  "user_input_generate_images": true,
  "user_input_max_retry": 3,
  "user_input_copy_space_required": true,
  "user_input_need_no_text": true,
  "user_input_need_no_logo": true
}
5.2 总控 Skill 输出
{
  "system_output_success": true,
  "system_output_project_dir": "./projects/2026-06-23_制造业_智能工厂AI视频素材",
  "system_output_storyboard_json": "./projects/.../01_storyboard/storyboard_master.json",
  "system_output_storyboard_csv": "./projects/.../01_storyboard/storyboard_master.csv",
  "system_output_generated_image_count": 80,
  "system_output_approved_image_count": 76,
  "system_output_failed_image_count": 4,
  "system_output_failed_queue": "./projects/.../05_review/failed_queue.json",
  "system_output_message": "项目已生成完成，部分图片需要人工复查或重生。"
}
6. project_manifest.json 设计
{
  "project_id": "manufacturing_smart_factory_20260623",
  "project_title": "制造业智能工厂AI视频素材",
  "industry_name": "制造业",
  "total_shots": 80,
  "aspect_ratio": "16:9",
  "target_usage": ["宣传片", "展会", "活动", "TVC", "预告片"],
  "created_at": "2026-06-23 00:00:00",
  "status": "in_progress",
  "style_bible_path": "./style_bible.json",
  "storyboard_master_path": "./01_storyboard/storyboard_master.json",
  "image_root_dir": "./03_images",
  "approved_count": 0,
  "failed_count": 0,
  "manual_review_count": 0
}
7. style_bible.json 设计

这个文件非常重要，用来保证整组选题统一。

{
  "style_id": "smart_factory_premium_001",
  "industry": "制造业",
  "main_visual_style": "真实摄影质感，高端科技工业风，现代智能工厂，蓝银色调，干净整洁，企业宣传片级别",
  "color_palette": ["深蓝", "银灰", "冷白", "金属灰"],
  "lighting_style": "明亮干净的工业灯光，柔和体积光，局部蓝色科技光效",
  "camera_language": "电影感构图，稳定运镜，宽幅画面，适合企业宣传片和展会大屏",
  "factory_environment": "现代化智能工厂，高挑空间，整洁地面，机械臂，自动化产线，AGV小车，工业数据大屏",
  "people_style": "中国工程师，专业工装或商务工装，干净利落，真实自然，不夸张摆拍",
  "equipment_style": "高端自动化设备，机械臂，精密检测设备，数字化控制台，智能传感器",
  "commercial_rules": {
    "no_logo": true,
    "no_brand_name": true,
    "no_text": true,
    "no_watermark": true,
    "copy_space_required": true,
    "avoid_messy_background": true,
    "avoid_low_quality_machinery": true
  },
  "negative_constraints": [
    "logo",
    "brand name",
    "watermark",
    "random text",
    "Chinese characters",
    "English letters",
    "messy workshop",
    "dirty factory",
    "distorted hands",
    "deformed machinery",
    "cartoon style",
    "low resolution",
    "cheap plastic look"
  ]
}
8. 单条分镜 shot_001.json 设计
{
  "shot_id": "shot_001",
  "shot_title": "智能工厂全景建立镜头",
  "scene_goal": "建立高端制造、智能工厂、科技工业的整体氛围",
  "subject_main": "现代智能工厂车间全景",
  "subject_secondary": ["机械臂", "自动化生产线", "AGV小车", "工程师"],
  "action_description": "机械臂在产线上同步作业，AGV小车平稳穿梭，工程师在远处巡视",
  "scene_context": "宽敞明亮的高端制造车间，地面干净反光，远处有工业数据大屏",
  "camera_angle": "wide establishing shot",
  "camera_movement": "slow dolly in feeling",
  "shot_size": "wide shot",
  "composition_notes": "主体偏右，左侧保留干净文案空间，适合宣传片片头",
  "visual_style": "photorealistic, cinematic, premium industrial technology style",
  "lighting_style": "clean cool white industrial lighting with soft blue highlights",
  "mood_tone": "advanced, professional, efficient, futuristic",
  "color_palette": "blue, silver, white, metallic gray",
  "copy_space": "left",
  "continuity_lock": {
    "style_id": "smart_factory_premium_001",
    "factory_environment": "same premium smart factory visual system"
  },
  "negative_constraints": [
    "logo",
    "brand name",
    "text",
    "watermark",
    "messy background",
    "distorted machines",
    "cartoon style"
  ],
  "image_prompt_path": "../02_image_prompts/shot_001_prompt.json",
  "image_output_dir": "../03_images/shot_001",
  "generate_status": "pending",
  "approved_version": null,
  "retry_count": 0
}
9. 状态机设计

每条分镜都有状态。

pending
  ↓
prompt_created
  ↓
generating
  ↓
generated
  ↓
reviewing
  ↓
approved / needs_regeneration / manual_review / failed
状态说明
状态	含义
pending	分镜已创建，未生成 prompt
prompt_created	生图 prompt 已生成
generating	正在生成图片
generated	图片已生成
reviewing	正在质检
approved	通过
needs_regeneration	需要重生
manual_review	需要人工判断
failed	多次重试仍失败
10. 生图 Prompt 组装模板

Codex 要把分镜字段拼成这种提示词：

生成一张高质量商业化视频素材画面，适合用于企业宣传片、活动视频、展会大屏、TVC和预告片。

画面主体：
{subject_main}

辅助元素：
{subject_secondary}

画面动作：
{action_description}

场景环境：
{scene_context}

景别：
{shot_size}

机位：
{camera_angle}

运镜感：
{camera_movement}

构图要求：
{composition_notes}

视觉风格：
{visual_style}

光线风格：
{lighting_style}

情绪氛围：
{mood_tone}

色彩体系：
{color_palette}

统一风格约束：
{continuity_lock}

商业素材要求：
画面真实，高级，干净，整洁，有电影感，适合企业宣传片使用，保留文案空间，不要过度夸张，不要廉价科技光效。

禁止出现：
{negative_constraints}
11. 图片质检规则

image_review_engine.py 要输出统一 JSON。

{
  "shot_id": "shot_001",
  "image_version": "v1.png",
  "review_status": "approved",
  "stock_readiness_score": 92,
  "checks": {
    "file_exists": true,
    "subject_match": true,
    "style_consistency": true,
    "copy_space_ok": true,
    "no_logo": true,
    "no_text": true,
    "no_watermark": true,
    "composition_ok": true,
    "lighting_ok": true,
    "machinery_ok": true,
    "people_anatomy_ok": true,
    "commercial_quality_ok": true
  },
  "failure_reasons": [],
  "suggested_fix_prompt": ""
}
12. 自动重生规则

如果 review_status = needs_regeneration，执行重生。

重生逻辑
不删除旧图
新图保存为 v2.png、v3.png
通过后复制为 current.png
写入 replace_history.json
重生 Prompt 模板
请基于原分镜重新生成该画面，并重点修复以下问题：

失败原因：
{failure_reasons}

必须保留：
- 原分镜主题
- 主体元素
- 行业属性
- 高端科技工业风
- 蓝银色调
- 企业宣传片质感

重点优化：
- 画面更清晰
- 构图更稳
- 主体更准确
- 保留文案空间
- 避免文字、logo、水印
- 避免机械结构畸形
- 避免人物手部异常

重新生成一张更适合商业视频素材销售的版本。
13. 替换记录 replace_history.json
[
  {
    "shot_id": "shot_001",
    "old_version": "v1.png",
    "new_version": "v2.png",
    "replace_reason": ["画面出现乱码文字", "机械臂结构畸形"],
    "replaced_at": "2026-06-23 00:00:00",
    "current_version": "current.png"
  }
]
14. 基于满意图扩展更多角度/景别
输入
{
  "user_input_project_dir": "./projects/2026-06-23_制造业_智能工厂AI视频素材",
  "user_input_anchor_shot_id": "shot_018",
  "user_input_anchor_image_path": "./03_images/shot_018/current.png",
  "user_input_expand_count": 6,
  "user_input_expand_types": [
    "wide shot",
    "medium shot",
    "close-up",
    "side angle",
    "top-down angle",
    "low angle"
  ]
}
输出目录
/04_variations/
  /shot_018/
    anchor.png
    wide_shot_v1.png
    medium_shot_v1.png
    closeup_v1.png
    side_angle_v1.png
    top_down_v1.png
    low_angle_v1.png
    variation_manifest.json
扩展 Prompt 模板
请基于锚点画面生成同一场景下的连贯分镜画面。

锚点画面核心保持不变：
- 同一座智能工厂
- 同一套蓝银色高端科技工业风
- 同一类设备与生产线
- 同样干净、真实、企业宣传片质感
- 同样无logo、无文字、无水印

本次只调整：
- 景别：{target_shot_size}
- 机位：{target_camera_angle}
- 构图：{target_composition}
- 动作变化：{target_action_variation}

目标：
生成一张与锚点画面风格连续、可剪辑在一起的视频素材画面。
15. 分镜 Skill 的内部提示词

这个直接给 Codex 写进 storyboard_planner.py。

你是一名AI视频素材分镜策划专家，目标是为“{user_input_topic_title}”生成可直接用于批量生图和后续生视频的生产型分镜表。

项目行业：
{user_input_industry_name}

目标用途：
{user_input_target_usage}

视觉风格：
{user_input_visual_style}

分镜数量：
{user_input_total_shots}

请严格遵守：
1. 每条分镜只描述一个明确画面瞬间，不要多个事件串联。
2. 所有分镜要适合商业视频素材销售。
3. 画面要高级、真实、干净、科技、现代、可用于宣传片、展会、TVC、活动视频。
4. 每条分镜必须考虑后期可上文字，合理保留文案空间。
5. 禁止出现品牌、logo、文字、水印、版权角色。
6. 同组选题要保持统一视觉风格。
7. 输出 JSON 数组，不要输出解释。

每条分镜必须包含：
- shot_id
- shot_title
- scene_goal
- subject_main
- subject_secondary
- action_description
- scene_context
- camera_angle
- camera_movement
- shot_size
- composition_notes
- visual_style
- lighting_style
- mood_tone
- color_palette
- copy_space
- continuity_lock
- negative_constraints
- generate_status
- retry_count
16. Codex 开发总提示词

你可以直接复制这段给 Codex。

请帮我开发一个 Python3 Skill 工程，名称为 ai_video_asset_skill。

这个 Skill 用于 AI 视频素材商业化生产，核心流程是：
选题输入 → 创建项目文件夹 → 生成结构化分镜 → 每条分镜生成生图提示词 → 调用内置生图能力批量生成图片 → 自动质检 → 失败重试 → 当前图片替换 → 基于满意图片扩展更多角度和景别。

请严格按以下模块拆分：
1. main_orchestrator.py
2. storyboard_planner.py
3. image_prompt_builder.py
4. image_generator_adapter.py
5. image_review_engine.py
6. variation_expander.py
7. file_manager.py
8. config.py
9. README.md

开发要求：
- 使用 Python3
- 所有入口函数返回 JSON 对象
- 输入输出字段命名清晰，例如：
  user_input_topic_title
  user_input_total_shots
  user_input_visual_style
  system_output_project_dir
  system_output_storyboard_json
  system_output_generated_image_paths
- 不要把所有逻辑写在一个文件
- 每个选题建立独立工程文件夹
- 每条分镜建立独立图片文件夹
- 所有图片保留版本，例如 v1.png、v2.png、v3.png
- 当前通过版本统一复制为 current.png
- 不满意重生时不要删除旧版本
- 写入 replace_history.json
- 支持 retry，最多重试 user_input_max_retry 次
- 支持基于某张 current.png 扩展更多角度、景别、构图
- 支持导出 storyboard_master.json、storyboard_master.csv、delivery_index.csv
- README 里写清楚如何运行

请先实现最小可用版本：
1. 能创建项目目录
2. 能生成 mock 分镜 JSON
3. 能根据分镜生成 prompt 文件
4. 能调用 image_generator_adapter 的占位函数生成 mock 图片路径
5. 能写入 review.json
6. 能更新 project_manifest.json

注意：
image_generator_adapter.py 先写成适配层，不要写死具体模型。先提供 generate_image(prompt, output_path, options) 函数，后续我会把 Codex 内置生图能力或第三方生图 API 接进去。
17. 第一版不要贪多，先做 MVP

第一版只要完成这 6 个能力就够了：

新建项目目录
生成 20 条分镜
每条分镜生成 prompt
每条分镜建立图片文件夹
生图结果保存为 v1.png 和 current.png
生成总清单 delivery_index.csv

第二版再加：

自动质检
失败重试
替换历史
基于满意图扩展

第三版再加：

联系表 contact sheet
批量生视频 prompt
视频生成接口
成套素材导出包
18. 你这个制造业素材 Skill 的默认选题配置

先内置一个默认配置，方便你直接跑。

{
  "default_topic_title": "制造业智能工厂AI视频素材",
  "default_industry_name": "制造业",
  "default_total_shots": 80,
  "default_target_usage": ["宣传片", "展会", "活动视频", "TVC", "预告片"],
  "default_visual_style": "高端科技工业风，真实摄影质感，现代智能工厂，蓝银色调，干净整洁，企业宣传片级别",
  "default_aspect_ratio": "16:9",
  "default_copy_space_required": true,
  "default_no_logo": true,
  "default_no_text": true,
  "default_max_retry": 3
}
19. 你后面做 80 个制造业分镜时，建议分组
01_片头与制造强国氛围：6条
02_智能工厂全景：10条
03_AI工业大脑与数字孪生：10条
04_自动化生产线与机械臂：10条
05_芯片半导体与精密制造：8条
06_新能源汽车与高端装备：8条
07_研发实验室与工程师：8条
08_数字化转型与管理协同：8条
09_绿色制造与新型储能：6条
10_产业升级与未来制造收尾：6条

合计 80 条。

20. 最终验收标准

Codex 做完后，至少要能做到：

输入一个选题：
制造业智能工厂AI视频素材

系统自动生成：
- 一个项目文件夹
- 一个 style_bible.json
- 一个 storyboard_master.json
- 一个 storyboard_master.csv
- 80 个 shot_xxx.json
- 80 个 shot_xxx_prompt.json
- 80 个图片文件夹
- 每条分镜至少一张 current.png
- 一个 approved_manifest.json
- 一个 delivery_index.csv

并且支持：

重新生成 shot_018
扩展 shot_018 的 6 个角度
替换 shot_018 当前图
查看失败队列
导出全部已通过素材清单