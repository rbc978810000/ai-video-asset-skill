# AI 视频素材工作流契约

## 输入字段

必填或可默认字段：

- `user_input_topic_title`：选题名称。
- `user_input_industry_name`：行业名称。
- `user_input_total_shots`：分镜数量。
- `user_input_target_usage`：用途列表，例如宣传片、展会、活动视频、TVC、预告片。
- `user_input_visual_style`：视觉风格锁定描述。
- `user_input_aspect_ratio`：画幅，默认 `16:9`。
- `user_input_output_root_dir`：输出根目录，默认 skill 根目录下的 `output/`。
- `user_input_generate_images`：是否创建生图任务或测试图片。
- `user_input_image_provider`：正式生产使用 `codex_image2`，离线测试使用 `mock_placeholder`。
- `user_input_research_notes_path`：可选，外部联网调研笔记 JSON 路径。
- `user_input_market_reference_assets_path`：可选，`市场参考图清单.json` 路径；用于让分镜参考图计划自动匹配本地市场参考封面图。
- `user_input_video_reference_assets_path`：可选，`视频参考帧清单.json` 路径；用于让后续调研和分镜规划引用公开视频小样抽取的去水印关键帧。
- `user_input_market_mining_summary_path`：可选，`市场反挖摘要.json` 路径；用于让 `source_notes`、`visual_demand_matrix` 和 `shot_group_plan` 继承光厂两轮反挖结果。
- `user_input_people_region_priority`：人物和地域优先级，默认中国人、中国工程师、中国企业场景。
- `user_input_allow_contextual_large_chinese_text`：是否允许必要场景大号中文，默认允许。
- `user_input_max_retry`：最大重试次数。
- `user_input_copy_space_required`、`user_input_need_no_text`、`user_input_need_no_logo`：商业素材约束。

## 项目目录

同一选题/工程只创建或复用一个目录。`mine-market`、`run`、参考图采集、视频拆帧、参考帧筛选、生图准备和导出都必须写入同一个项目目录；如果未显式传 `--project-dir`，先按同日同主题复用已有目录，找不到时才创建新的中文可读目录。项目目录名必须面向人工识别，优先使用日期、中文行业或“素材调研”、中文选题，不得使用英文内部任务名生成新工程目录。

```text
output/<日期>_<中文行业或素材调研>_<中文选题>/
  项目清单.json
  选题简报.md
  风格设定.json
  00_输入/
    生效输入.json
    原始输入.json
    原始调研笔记.json
    原始调研报告.md
    原始市场参考图清单.json
    原始市场反挖摘要.json
  00_调研/
    搜索词.json
    调研说明.md
    来源笔记.json
    市场反挖/
      种子关键词.json
      光厂第一轮搜索结果.jsonl
      光厂第一轮作品详情.jsonl
      关键词分析.json
      商业AI方向.json
      买家搜索提示词.json
      光厂第二轮搜索结果.jsonl
      光厂第二轮作品详情.jsonl
      市场反挖摘要.json
      人工审核.json
      后续动作确认.json
    市场参考图清单.json
    市场参考图说明.md
    市场参考图总览.jpg
    参考图/
    视频参考帧/
      视频参考帧清单.json
      视频参考帧说明.md
      视频参考帧索引.jsonl
      视频镜头索引.jsonl
      视频参考帧总览.jpg
      来源/
        <来源编号>/
          来源信息.json
          原视频/
          镜头/
            镜头_0001/
              镜头信息.json
              帧图片/
              缩略图/
    代表画面.json
    视觉分类.json
    市场信号映射.json
    视觉需求矩阵.json
    创意角度.json
    镜头组规划.json
    参考图规划.json
  01_分镜/
    分镜总表.json
    分镜总表.csv
    镜头_001.json
  02_生图提示词/
    镜头_001_生图提示词.json
  03_图片/
    镜头_001/
      生图请求.json
      版本1.png
      当前图.png
      审核记录.json
  04_扩展角度/
  05_审核/
    失败队列.json
    重试记录.json
    通过清单.json
    替换记录.json
  06_导出/
    交付索引.csv
    通过清单汇总.json
    JiaoZistudio专用脚本.json
```

`06_导出/JiaoZistudio专用脚本.json` 是给 JiaoziStudio 画布导入的首选单文件脚本，已经合并分镜、参考依赖、风格和提示词；不再生成压缩包。项目目录本身仍是主产物和可继续编辑的源数据。

## 输入归档文件

- `00_输入/生效输入.json`：本次运行最终生效的完整输入配置，包含默认值、命令行覆盖项和用户配置合并后的结果。
- `00_输入/原始输入.json`：如果运行时传入 `--input-json`，自动归档原始输入配置。
- `00_输入/原始调研笔记.json`：如果运行时传入 `--research-json`，自动归档原始外部调研笔记。
- `00_输入/原始调研报告.md`：如果配置了 `user_input_research_report_path`，自动归档原始调研报告。
- `00_输入/原始市场参考图清单.json`：如果传入市场参考图 manifest，自动归档原始参考图清单。
- `00_输入/原始市场反挖摘要.json`：如果传入 `--market-mining-summary`，自动归档光厂两轮反挖摘要。
- `docs/` 只放通用 PRD、方法论和说明文档；不要把某个具体视频需求的输入、调研 notes、脚本或 prompt 长期放在 `docs/`。

## 前期调研文件

- `市场反挖/种子关键词.json`：主题种子词，通常 3-5 个。
- `市场反挖/光厂第一轮搜索结果.jsonl`：第一轮光厂搜索页结果。每行包含 `search_keyword`、`rank`、`title`、`work_url`、`cover_url`、`purchase_count`、`resolution`、`duration`、`aigc_flag`。
- `市场反挖/光厂第一轮作品详情.jsonl`：第一轮详情页提取。每行包含 `detail_keywords`、`material_income`、`upload_time`、`preview_images`、`preview_video_url`、`author`、`category`、`related_work_urls`、`risk_flags`。
- `市场反挖/关键词分析.json`：全量关键词统计、共现关系、销量/收入加权和四类词：题材词、画面词、镜头词、商业用途词。
- `市场反挖/商业AI方向.json`：主题商业化 AI 素材方向。每条包含 `direction_name`、`buyer_search_prompts`、`evidence_work_ids`、`market_signal_score`、`ai_generation_feasibility`、`video_motion_potential`、`commercial_reuse_value`、`risk_score`、`recommended_shot_count`、`prompt_guidance_for_image_generation`。
- `市场反挖/买家搜索提示词.json`：第二轮搜索用买家搜索提示词，不是最终 image2 长 prompt。每条必须包含证据作品、市场信号、商业用途、AI 可生成性和风险提示。
- `市场反挖/光厂第二轮搜索结果.jsonl`：第二轮光厂搜索结果。搜索词必须来自 `买家搜索提示词.json`，每条提示词取前 10 个作品。
- `市场反挖/光厂第二轮作品详情.jsonl`：第二轮详情页提取，用于修正商业方向、镜头比例和参考图优先级。
- `市场反挖/市场反挖摘要.json`：喂给 `source_notes`、`visual_demand_matrix`、`shot_group_plan` 的摘要，包含 `source_notes`、`visual_demand_matrix_inputs` 和 `shot_group_plan_seed`。
- `市场反挖/人工审核.json`：Electron 或人工审核标记，允许标记高价值、只作证据、排除、可图生图参考、需要复查。
- `市场反挖/后续动作确认.json`：调研完成后的待确认动作。必须记录是否建议继续采集高价值作品的公开预览视频、去水印拆帧、进入 Electron 参考帧挑选；用户未确认前不得自动运行 `prepare-high-value-video-frame-queue` 或 `collect-high-value-video-frames`。
- `搜索词.json`：建议搜索词，只覆盖调研白名单内的素材交易/授权平台、商业素材和避坑参考。
- `调研说明.md`：给 Codex 的调研说明，强调只能使用白名单素材平台，只提取画面类型，不复制具体图片。
- `来源笔记.json`：联网调研后的资料笔记，只允许来自调研白名单的平台。每条建议包含 `source_type`、`source_platform`、`source_quality`、`url`、`summary`、`representative_visuals`、`keywords`、`avoid_notes`；如果来自市场页，可额外包含 `search_result_count`、`purchase_count`、`download_count`、`related_keywords`、`high_purchase_examples`、`market_signal`。
- `市场参考图清单.json`：从市场页公开封面、搜索页缩略图和详情页预览图采集的本地参考图清单。每条包含 `asset_id`、`title`、`page_url`、`image_url`、`local_path`、`purchase_count`、`keywords`、`visual_tags`、`category_tags`、`reference_score`、`score_breakdown`、`can_be_image_reference`、`reference_decision`、`reference_risk_flags`、`usage_notes`。
- `市场参考图说明.md`：市场参考图索引和预览说明。
- `市场参考图总览.jpg`：可选参考图总览拼图；环境没有 Pillow 时可省略。
- `参考图/`：公开封面/预览图本地保存目录。仅用于调研和参考图规划，不作为最终交付素材。
- `视频参考帧/视频参考帧清单.json`：公开视频小样/光厂预览视频抽取后的去水印参考帧聚合清单。每条帧记录包含 `frame_id`、`source_id`、`shot_id`、`path`、`thumb_path`、`timestamp_seconds`、`quality_score`、`sha256`、`watermark_removed`、`watermark_backend_used`。
- `视频参考帧/视频参考帧索引.jsonl` 和 `视频参考帧/视频镜头索引.jsonl`：供 agent 快速检索的帧级和镜头组级索引；不要让 agent 每次遍历图片目录。
- 使用 `collect-scene-frames` 生成时，`shot_id` 会使用 `scene_0001` 这类场景编号，并在记录中补充 `scene_start_seconds`、`scene_end_seconds`、`scene_midpoint_seconds`；该模式保证每个 TransNetV2 场景只对应一张代表图。
- `视频参考帧/来源/<来源编号>/`：单个公开视频小样的归档目录，包含 `来源信息.json`、`原视频/` 原视频、`镜头/<镜头编号>/帧图片/` 去水印帧和 `缩略图/` 缩略图。
- `代表画面.json`：代表性画面清单，用于判断主题画面是否准确。
- `视觉分类.json`：画面类型分类、核心元素、商业价值、创意角度、避坑点。
- `市场信号映射.json`：市场信号映射。每个画面类型必须记录命中的调研来源、市场关键词、高价值画面、购买/下载/搜索信号、用户用途和避坑点，用于回答“市场为什么需要这类画面”。
- `视觉需求矩阵.json`：视觉需求矩阵。每个画面类型必须记录 `market_demand_score`、`ai_generation_feasibility`、`video_motion_potential`、`commercial_reuse_value`、`risk_score`、`recommended_weight` 和 anchor 策略，用于回答“这类画面值得生成多少条”。
- `创意角度.json`：差异化创意角度，避免生成大量同质画面。
- `镜头组规划.json`：镜头分配计划，分镜生成必须优先遵循；镜头数量必须能追溯到 `视觉需求矩阵.json` 的推荐权重和风险判断。
- `参考图规划.json`：同场景参考图计划，标记哪些镜头是 anchor，哪些镜头应参考 anchor 当前图.png。

## 市场参考图评分

采集回来的公开封面/预览图必须本地保存并评分。评分目标不是判断“能不能照搬”，而是判断“是否适合做 image2 的方向参考图”。默认评分维度：

- `market_signal_score`：购买量、热门排序、下载量、详情页相关性等市场信号。
- `preview_quality_score`：预览图尺寸、文件大小、清晰度可用性。
- `metadata_relevance_score`：标题、关键词、视觉标签、分类标签和当前选题的相关度。
- `reference_safety_score`：文字、Logo、水印、真实品牌包装、可识别人像、模板感等风险扣分。
- `platform_score`：平台优先级，主力素材平台高于纯镜头语言补充平台。

`reference_score >= 70` 且 `reference_safety_score >= 65` 的图可自动进入 `参考图规划.json`，作为 image2 图生图方向参考；低分或高风险图只保留为市场证据和关键词分析，不自动传入生图请求。进入图生图参考的市场图只能提供题材、构图、色彩、景别和画面模块方向，正式生图必须原创化重构，禁止复刻原图、Logo、水印、真实品牌包装或可识别版权画面。

## Electron 协作壳

`electron-viewer/` 只作为本地观察和人工审核界面，不建立第二套数据库，不直接调用 image2，不下载付费原片，不覆盖分镜主产物，不保存账号密钥或 Cookie。

允许读取：

- `00_调研/市场反挖/*.json`
- `00_调研/市场反挖/*.jsonl`
- `00_调研/市场参考图清单.json`

允许写入：

- `00_调研/市场反挖/人工审核.json`

人工标记建议枚举：`high_value`、`evidence_only`、`excluded`、`image2_reference`、`needs_recheck`。

## 调研来源白名单

方向调研只能使用以下素材交易/授权平台：

- 国内主力：光厂/VJShi（`vjshi.com`）、新片场素材（`stock.xinpianchang.com`）、视觉中国 VCG（`vcg.com`）。
- 国外主力：Pond5（`pond5.com`）、Shutterstock Video（`shutterstock.com`）、Adobe Stock Video（`stock.adobe.com`）、Getty Images Creative Video（`gettyimages.com`）、iStock Footage（`istockphoto.com`）。
- 国外高端镜头语言参考：Artgrid（`artgrid.io`）、Filmsupply（`filmsupply.com`）、Dissolve（`dissolve.com`）。

白名单外来源不得进入 `来源笔记.json`、`市场信号映射.json` 或 `视觉需求矩阵.json`。摄图网、包图网、千图网、图虫创意、135editor、公众号排版站、教程站、SEO 聚合页、Storyblocks、Motion Array、Envato/Envato Elements 必须排除；这类来源最多作为“不要参考”的低质量来源备注，不参与镜头权重、市场需求分或参考图计划。

## 市场反挖验证要求

- 光厂搜索页解析必须覆盖购买量、标题、作品地址、封面地址。
- 光厂详情页解析必须覆盖关键词、收入、上传时间、预览图、预览视频地址。
- 关键词分析必须区分题材词、画面词、镜头词、商业用途词。
- 买家搜索提示词必须能追溯到作品证据，第二轮搜索必须使用 `买家搜索提示词.json`，不能使用原始种子词。
- 带角标、水印、多宫格、可读文字、品牌包装风险的图片不能自动进入图生图参考，只能作为市场证据或等待人工审核。
- `镜头组规划.json` 的镜头比例如果来自市场反挖，必须能追溯到 `市场反挖摘要.json` / `商业AI方向.json`。
- Electron 只能写 `人工审核.json`，不得调用 image2、付费下载、覆盖分镜或保存密钥。

## 单条分镜字段

每条分镜 JSON 必须包含：

- `shot_id`、`shot_title`、`scene_goal`
- `scene_group`、`research_basis`
- `reference_image_plan`
- `reference_dependency`
- `subject_main`、`subject_secondary`、`action_description`、`scene_context`
- `camera_angle`、`camera_movement`、`shot_size`、`composition_notes`
- `visual_style`、`lighting_style`、`mood_tone`、`color_palette`
- `copy_space`、`continuity_lock`、`negative_constraints`
- `image_prompt_path`、`image_output_dir`
- `generate_status`、`approved_version`、`retry_count`

`reference_dependency` 是给可视化画布和批量生图队列使用的显式依赖契约，不能省略。结构如下：

```json
{
  "role": "anchor | derived_view | standalone",
  "anchor_shot_id": "shot_001 或 null",
  "reference_image_path": "../03_图片/镜头_001/当前图.png 或 null",
  "market_reference_asset_ids": [],
  "market_reference_asset_paths": [],
  "market_reference_scores": [],
  "market_reference_categories": [],
  "market_reference_decisions": [],
  "reference_reason": "为什么引用该锚点或外部参考图",
  "market_reference_usage": "仅用于题材/构图/色彩方向参考，不能复刻"
}
```

同一个 `scene_group` 中，第一条用于建立空间、人物、设备或风格一致性的镜头通常是 `anchor`；后续多景别、多角度镜头使用 `derived_view` 并通过 `anchor_shot_id` 指向锚点。即使后续工具会自动连线，`reference_dependency` 仍必须写入单条分镜、`分镜总表.json` 和 `详细脚本.json`，连线只是可视化辅助，不是唯一依赖来源。

## 状态机

合法状态流：

```text
pending -> prompt_created -> generating -> generated -> reviewing
reviewing -> approved | needs_regeneration | manual_review | failed
```

当脚本创建了 `生图请求.json`、但还没有实际图片时，使用 `manual_review`，含义是“等待 Codex 调用 image2 并登记结果”。

## 中文生图提示词模板

根据分镜和 `风格设定.json` 组装详细美术 brief。提示词不能只罗列字段，必须让 image2 明确知道主体、前中后景、人物语境、镜头语言、光线材质、细节密度、文字策略和参考图一致性。

```text
请生成一张可直接用于 AI 视频生成和商业剪辑的高质量静帧素材。

【输出定位】
- 用途：企业宣传片、节日/活动视频、展会大屏、TVC广告、预告片和商业素材销售。
- 画幅：{aspect_ratio}，单张真实摄影风格画面，不要拼贴、不要多宫格、不要插画海报。
- 质感目标：TVC广告级摄影，高级、干净、真实、有电影感，色彩饱和但专业克制，细节清晰。

【核心画面一句话】
{action_description}

【主体设定】
- 主体：{subject_main}
- 辅助元素：{subject_secondary}
- 主体必须清楚可识别，占据画面视觉重点，不要被背景、文字或装饰元素抢走注意力。
- 只表现一个明确瞬间，避免把多个事件、多个场景或复杂时间线塞进同一张图。

【场景与空间层次】
- 场景环境：{scene_context}
- 前景：写清楚可用于景深和质感的主题相关元素。
- 中景：写清楚主体、动作、人物关系或产品展示重点。
- 背景：写清楚环境、空间纵深、地域语境和需要避免的干扰物。
- 画面比例按 {aspect_ratio} 组织，保留后期文案空间。

【人物与中国语境】
- {people_style}
- {cultural_context}
- 如果出现人物，人物面孔、服饰、姿态、动作和场景细节必须贴合中国市场；动作自然，不夸张摆拍。

【镜头语言】
- 景别：{shot_size}
- 机位：{camera_angle}
- 运镜感：{camera_movement}；虽然输出是静帧，但画面要有视频镜头中的运动预期和剪辑衔接感。
- 构图：{composition_notes}
- 明确主体、前景、中景、背景和留白之间的主次关系。

【光线、色彩与材质】
- 视觉风格：{visual_style}
- 光线风格：{lighting_style}
- 情绪氛围：{mood_tone}
- 色彩体系：{color_palette}
- 写清材质、反光、阴影、散景、真实纹理和专业灯光层次。

【画面细节密度】
- 细节要足够丰富，包含道具、材质、背景层次和光影细节。
- 细节必须服务主体和主题情绪，不能杂乱，不能引入无关装饰。
- 避免小字、太密纹样、无关小物件和后续生视频容易闪烁变形的复杂细节。

【文字与后期空间】
- 文案留白：{copy_space}
- 文字策略：默认不要生成任何可读文字、品牌名、Logo或水印；如果画面语义确实需要文字，只能出现少量大号、清晰、贴合场景的中文，文字必须足够大。

【参考图一致性计划】
如果本镜头是同场景 anchor，先生成并登记 当前图.png；如果本镜头是同场景衍生镜头，必须参考 anchor 当前图.png，仅调整景别、机位、构图或动作。

【统一风格锁定】
{continuity_lock}

【商业素材硬性要求】
- 画面真实摄影，不要卡通、不要廉价合成、不要过度锐化、不要过曝、不要脏乱背景。
- 主体边缘清晰，材质真实，空间透视正确，人物手部和五官自然，食品、器物、建筑、道具或主体结构不能畸形。
- 画面要像专业广告摄影师、灯光师和美术指导共同完成的成片级素材。

【禁止出现】
{negative_constraints}
```

## Codex image2 接入规则

- 正式生图 provider 使用 `codex_image2`。
- Python 脚本只负责生成 `生图请求.json`，其中包含 prompt、negative prompt、画幅和目标输出路径。
- `生图请求.json` 必须包含 `reference_image_plan` 和从分镜继承的 `reference_dependency`；如果已有可用参考图，同时包含 `reference_image_path`。
- 如果分镜匹配到高分市场参考图，`生图请求.json` 同时包含 `market_reference_asset_paths`、`market_reference_asset_ids`、`market_reference_scores`、`market_reference_categories`、`market_reference_decisions` 和 `market_reference_usage`。
- 高分市场参考图可以作为 image2 图生图方向参考；正式生图必须原创化重构，禁止复刻参考图、Logo、水印、真实品牌包装和可识别版权画面。
- 执行 Skill 的 Codex 必须读取请求，调用内置 image2 生图能力，再用 `register-image` 登记图片。
- 如果 image2 返回的图片无法直接落盘，先取得本地图片路径，再登记；不要把 base64 或真实凭据写入项目文件。
- 每次重生只针对一个明确 `shot_id`，并受最大重试次数限制。

## 成本与副作用规则

- `codex_image2` 生图会消耗真实生成额度时，必须按需调用，不要空跑、轮询或重复请求。
- 对同一 `project_id + shot_id + version` 使用明确版本号，避免重复覆盖。
- 外部接口超时或结果不确定时，先确认状态，不能盲目创建第二次付费生图。
- 密钥、令牌、Cookie、私钥不得写入项目目录、日志、提示词或最终回复。
- 离线测试只能使用 `mock_placeholder`，它写入占位 PNG，不代表正式素材质量。
