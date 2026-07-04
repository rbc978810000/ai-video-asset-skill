# AI 视频素材分镜 + 生图 Skill PRD v1.1 调研增强补充

## 1. 调整目标

v1.1 在 v1.0 的“选题 -> 分镜 -> 生图”前增加前期调研分析层。

核心目标：

- 先理解主题有哪些代表性画面。
- 再判断商业素材用户真正需要哪些画面。
- 同时提炼创意扩展角度，避免只生成通用科技感图片。
- 最后用调研结果驱动 `style_bible.json`、`shot_group_plan.json`、分镜和 image2 生图提示词。

## 2. 新增流程

```text
用户选题
-> 主题关键词拆解
-> 只在高价值素材交易/授权平台白名单内调研
-> 采集公开封面/预览图到本地并评分归类
-> 提取代表性画面
-> 建立 visual_taxonomy
-> 建立 market_signal_map
-> 建立 visual_demand_matrix
-> 生成 creative_angles
-> 生成 shot_group_plan
-> 生成 reference_image_plan
-> 生成 style_bible
-> 生成生产型分镜
-> 生成 image2 中文生图提示词
-> 调用 Codex image2 生图
-> 登记 current.png、质检、重生、扩展
```

## 3. 新增目录

```text
00_research/
  search_queries.json
  research_brief.md
  source_notes.json
  representative_visuals.json
  visual_taxonomy.json
  creative_angles.json
  shot_group_plan.json
  reference_image_plan.json
```

## 4. 调研原则

- 只能调研高价值素材交易/授权平台白名单，不使用白名单外网页、公众号排版站、教程站或 SEO 聚合页做方向依据。
- 国内主力：光厂/VJShi（`vjshi.com`）、新片场素材（`stock.xinpianchang.com`）、视觉中国 VCG（`vcg.com`）。
- 国外主力：Pond5（`pond5.com`）、Shutterstock Video（`shutterstock.com`）、Adobe Stock Video（`stock.adobe.com`）、Getty Images Creative Video（`gettyimages.com`）、iStock Footage（`istockphoto.com`）。
- 国外高端镜头语言参考：Artgrid（`artgrid.io`）、Filmsupply（`filmsupply.com`）、Dissolve（`dissolve.com`）。
- 摄图网、包图网、千图网、图虫创意、135editor、公众号排版站、教程站、SEO 聚合页、Storyblocks、Motion Array、Envato/Envato Elements 不得进入 `source_notes.json`、`market_signal_map.json` 或 `visual_demand_matrix.json`。
- 只提取画面类型、构图规律、技术场景、素材需求和避坑点。
- 不复刻具体图片、品牌工厂、设备 Logo、真实 UI、厂牌文字或可识别产品外观。
- 每张本地市场参考图都必须生成 `reference_score`、`score_breakdown`、`category_tags` 和 `reference_decision`。
- 高分低风险图可作为 image2 图生图方向参考，但必须原创化重构，不得以复刻原图为目标。
- 调研结论要能转成镜头分组和分镜字段，而不是停留在泛泛描述。

## 5. 输出标准

每个项目必须额外产出：

- `search_queries.json`：用于后续联网调研的搜索词。
- `source_notes.json`：资料摘要和代表画面记录。
- `representative_visuals.json`：主题代表画面清单。
- `visual_taxonomy.json`：画面类型、核心元素、商业价值、避坑点。
- `market_signal_map.json`：市场信号映射，记录命中的来源、关键词、购买/下载/搜索信号、高价值画面、用途和避坑点。
- `visual_demand_matrix.json`：视觉需求矩阵，用市场需求、AI 可生成性、视频动作潜力、商业复用价值和风险分推导镜头推荐权重。
- `market_reference_assets.json`：本地市场参考图清单，包含评分、归类、参考决策和本地路径。
- `creative_angles.json`：差异化创意角度。
- `shot_group_plan.json`：镜头分组和数量分配，数量必须能追溯到 `visual_demand_matrix.json`。
- `reference_image_plan.json`：同场景参考图计划，确定 anchor 图和后续多景别参考关系。

分镜中的每条 shot 需要新增：

- `scene_group`
- `research_basis`

`research_basis` 用于记录该镜头来自哪个代表画面、核心元素、创意角度和避坑约束。

## 6. 中国人物、场景文字和参考图一致性

- 画面人物主要以中国人、中国工程师、中国企业员工为主。
- 工装、空间、设备质感和企业语境应贴合中国制造业、中国智能工厂和中国商业视频素材市场。
- 默认不要文字。
- 如果画面语义确实需要文字，只允许少量贴合场景的大号清晰中文，例如安全区域标识、展会大屏标题、控制室区域提示。
- 禁止小字、密集字、乱码、品牌名、Logo 字、水印和无意义中英文，因为后续生视频容易出现模糊、畸形、闪烁和不可控变形。
- 同一场景需要多个景别或多个角度时，先规划锚点图；锚点图通过后，后续同组镜头以锚点 `current.png` 作为参考图，保持人物、设备、空间、光线、色彩和场景连续性。

## 7. 成本和副作用

- 联网调研由 Codex 搜索完成，不由 Python 脚本长期轮询或批量抓取网页。
- image2 生图按 `shot_id` 明确调用，避免重复生成。
- 离线测试继续使用 `mock_placeholder`，正式生产使用 `codex_image2`。
