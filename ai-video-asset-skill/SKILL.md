---
name: ai-video-asset-skill
description: 构建 AI 视频商业素材生产工作流：根据选题生成中文生产型分镜、中文生图提示词、项目目录、版本化图片、质检记录、失败队列、替换记录、扩展角度和交付清单；采集公开视频小样/光厂预览视频参考帧并去水印、索引化为调研参考素材。用于用户要求 AI 视频素材、分镜、生图、Codex image2 生图、批量 当前图.png、交付索引.csv、通过清单汇总.json、视频小样拆帧、去水印参考图或 Python MVP 自动化时。
---

# AI 视频素材分镜生图 Skill

## 工作流

使用本 Skill 时，把用户的选题变成一个可交付的 AI 视频素材项目：

1. 按 `references/workflow-contract.md` 规范化用户输入。
2. 每个视频需求只使用一个工程目录：调研、分镜、生图请求、参考帧、人工审核和导出都必须写入同一个 `project_dir`。如果未显式传 `--project-dir`，先复用同日同主题的已有目录；找不到时才创建新的中文可读目录，例如 `2026-06-27_素材调研_商务人士_签约成功_合作握手`，不得因为 `mine-market`、`run` 或英文内部任务名另起第二个工程目录。运行后把原始输入、外部调研 notes 和最终生效配置归档到该项目的 `00_输入/`；`docs/` 只放通用 PRD/方法论，不放具体项目生产资料。
3. 先做主题前期调研：拆解关键词，只在高价值素材交易/授权平台白名单内搜索，不使用白名单外网页、公众号排版站、教程站或 SEO 聚合页做方向依据。
4. 光厂/VJShi 是国内主市场依据。先运行 `mine-market`：主题种子词 -> 光厂默认排序搜索页采集 -> 作品详情提取 -> 第一轮纯语义关键词分析 -> 买家搜索提示词 -> 第二轮光厂搜索 -> 第二轮详情市场信号优先级。第二轮必须使用 `买家搜索提示词.json`，不能直接复用原始种子词。
5. 第一轮搜索 3-5 个主题关键词，必须先进入光厂“视频素材”筛选后再保留平台默认排序；搜索 URL 必须带 `categoryIdForSoftware=230&st=y`，记录搜索关键词、排名、标题、作品地址、封面地址、AIGC 标记、视频素材筛选状态等搜索页可见线索；打开作品详情页后记录详情关键词、素材收入、上传时间、素材类型/srcFileType、预览画面、公开小样/预览视频地址、作者、分类和相关作品。除非用户明确要求混合素材，不采集 AE/PR/片头包装/工程文件/PPT/模板类结果。
6. 第一轮详情提取后必须做纯语义关键词分析，只分析标题、详情关键词和来源搜索词，区分题材词、画面词、镜头词、商业用途词，并输出主题相关关键词与 `买家搜索提示词.json`。第一轮不得用购买量、点击量、上传时间、素材收入、文件大小等市场字段影响关键词发现或提示词排序。
7. 第二轮按 `买家搜索提示词.json` 再搜光厂，每条提示词保留平台默认排序并取前 10 个作品，再次提取详情；第二轮详情完成后，才结合购买量、销售额/素材收入、点击量等市场信号修正商业方向、镜头比例、参考图优先级和后续生图提示词权重。
8. 只采集公开可见的封面图、搜索页缩略图和详情页预览图，保存到 `00_调研/参考图/`，生成 `市场参考图清单.json`、`市场参考图说明.md` 和可选总览拼图；不要下载付费素材原片。
9. 如需从公开视频小样提炼镜头语言，运行 `collect-video-frames`：优先使用公开小样下载地址；没有公开小样时才退回详情页 `contentUrl` 预览视频，并在来源清单里记录小样解析状态和实际下载时长。默认只抽关键帧、按镜头组保存、用光厂水印预设去水印，并写入 `00_调研/视频参考帧/`；确需密集拆帧时才显式使用 `--mode every-frame`。如需标准场景分割，每个场景只取一张代表图，运行 `collect-scene-frames`。
10. 第二轮详情完成后，必须先向用户提问：是否继续采集高价值作品的公开预览视频并去水印拆帧，供 Electron 参考帧视图挑选；未确认前不要自动下载、拆帧或去水印。
11. 如用户选择拆分高价值作品画面，先运行 `prepare-high-value-video-frame-queue` 按素材收入/购买量/点击量/市场分准备最多 30 个可拆帧视频。队列必须二次过滤：只保留已确认属于光厂视频素材筛选或详情为 `视频素材/srcFileType=VIDEO` 的作品；排除标题、关键词、类型里含模板、AE 模板、PR 模板、片头模板、工程文件、包装工程、PPT 等非视频素材；必须有公开小样或预览视频地址。再运行 `collect-high-value-video-frames`：默认先采集前 10 个作品，若总参考帧少于 300 张则继续补采未处理作品，最多处理 30 个；复用 TransNetV2 高敏场景切分和去水印流程，默认 `--scene-threshold 0.28 --min-scene-duration 0.6`，每个检测场景只保留 1 张代表帧；如果实际下载视频时长显著短于站内声明时长，必须在记录中标记为小样不完整风险。
12. 用户在 Electron 的“参考帧”视图勾选可作参考图后，运行 `build-selected-reference-frames` 只复制勾选帧到 `00_调研/精选参考帧/`，并按每 12 张图生成 分析拼图 与 `参考帧分析任务.json`。Codex 必须实际打开 `00_调研/精选参考帧/分析拼图/*.jpg` 做视觉复核后，才能写回 `参考帧分析.json`；禁止只根据 `frame_id`、文件名、作品标题、历史分析文本或 JSON 元数据生成提示词。若拼图压缩导致主体数量、道具、文字、光线或空间细节无法确认，必须打开 `00_调研/精选参考帧/帧图片/` 中对应单张精选帧再次复核。
13. 分镜生成或补绑前运行 `bind-reference-frames`，生成 `00_调研/参考帧绑定计划.json`。参考帧是可选素材池，不要求每个镜头都绑定；绑定时按画面价值动态复用 0-3 次，并确保 `分镜总表.json`、单条分镜、`详细脚本.json`、prompt JSON 和 `生图请求.json` 都带 `reference_dependency`、原文件路径和参考用途说明。
14. 如果用户要把筛选好的参考帧直接送入 JiaoziStudio 画布，运行 `export-jiaozi-storyboard`。该命令必须读取 `精选参考帧清单.json` 与 Codex 视觉复核后的 `参考帧分析.json`，先根据主题、市场反挖摘要和参考帧结构化分析规划通用商业素材镜头组，再生成连贯分镜脚本、`referenceAssets`、每镜 `reference_dependency`、本地 `sourcePath` 和 `file://` 参考图地址；精选参考帧优先按用途绑定到合适镜头，低相关或高风险帧应保留在 `referenceAssets` 并明确标记为证据帧或低适配帧，不得强行绑定，默认写入 `06_导出/JiaoziStudio专用80镜头脚本.json` 和 `80镜头画面分镜脚本.md`。
15. `export-jiaozi-storyboard` 写出前必须自动执行逐镜头审校：逐条检查镜头主体/动作、绑定参考图视觉分析、图片提示词里的“参考图使用”和视频提示词动态是否一致。明显冲突时优先解绑参考图并把该镜头改回原创规划，不得让楼宇镜头绑定签字手部、握手镜头绑定纯签字图、鼓掌镜头的视频提示词写成握手等错配进入画布。审校还必须执行跨主题污染检查：先根据 `topic_profile.domain`、镜头主体、动作和场景确定本镜头主题域，视频提示词不得混入其他主题域的人物、场景、道具或动作；例如新能源汽车/道路/HUD/充电/电池/工厂镜头中出现商务人士、会议区域、合同、手持文件、会议桌、桌面道具等，必须作为 `blocking` 问题自动重写或阻断交付。审校结果必须写入 `06_导出/JiaoziStudio逐镜头参考审校报告.json` 和 `.md`；正式交付前冲突词命中必须为 0。
16. 对每张本地市场参考图生成 `reference_score`、`score_breakdown`、`category_tags`、`can_be_image_reference` 和 `reference_decision`；带角标、水印、多宫格、可读文字、品牌包装风险的图默认只作为市场证据，不自动进入 image2 图生图参考。
17. 将调研结果沉淀到 `00_调研/`：`搜索词.json`、`来源笔记.json`、`市场反挖/`、`市场参考图清单.json`、`视频参考帧/视频参考帧清单.json`、`精选参考帧/精选参考帧清单.json`、`参考帧绑定计划.json`、`代表画面.json`、`视觉分类.json`、`市场信号映射.json`、`视觉需求矩阵.json`、`创意角度.json`、`镜头组规划.json`。
11. 规划同场景参考图：生成 `参考图规划.json`。普通镜头默认 `standalone` 独立生成；高价值且适合多机位展开的参考图按 1 个 `anchor` 锚点图 + 1-2 个 `derived_view` 派生图组织，派生图必须参考锚点生成图保持同一场景、人物气质、服装体系、光线和空间关系，不再直接参考上传原图。
12. 脚本创作前自动生成 `00_输入/脚本创作简报.json`：画幅默认 `16:9`，默认不需要旁白、不需要字幕；风格定位、目标买家、商业用途、镜头组比例和参考图优先级从调研数据、`市场反挖摘要.json`、`视觉需求矩阵.json` 与 `镜头组规划.json` 推导，不要求用户手工补充。用户可选提供时长；若只提供时长未提供镜头数，则按约每 2.5 秒 1 个可售素材镜头估算总镜头数。
13. 根据 `脚本创作简报.json`、`视觉需求矩阵.json` 生成镜头配比，再结合 `镜头组规划.json` 和 `参考图规划.json` 生成中文生产型分镜和中文生图提示词。
13. 生图前先运行 `prepare-image2` 生成 `05_审核/生图队列.json` 和当前可执行镜头的 `03_图片/<镜头编号>/生图请求.json`；`standalone/anchor` 镜头按独立请求准备，`derived_view` 镜头必须等待对应锚点图生成后再以锚点图作为 image2 参考，避免派生镜头回到上传原图导致场景和人物不连续。
14. 生图主路径使用 Codex 内置 `image2` 能力：逐条读取 `02_生图提示词/*_生图提示词.json` 和 `03_图片/*/生图请求.json`，调用 image2 生成图片。
15. 将 image2 生成的本地图片登记到对应分镜目录，形成 `版本1.png`、`当前图.png` 和 `审核记录.json`。
16. 验证 `00_输入/`、`风格设定.json`、`分镜总表.json`、`分镜总表.csv`、单条分镜、单条提示词、`通过清单汇总.json`、`交付索引.csv` 是否齐全。
17. 顺便生成 `06_导出/JiaoZistudio专用脚本.json` 单文件脚本，便于 JiaoziStudio 画布直接导入；不再生成压缩包。
18. 只对明确的 `shot_id` 执行重生、替换当前图或扩展角度。

本地 Python 进程不能直接调用 Codex 会话里的 image2 工具，所以脚本内的 `codex_image2` provider 会生成待调用请求；真正生图由执行 Skill 的 Codex 使用内置 image2 完成。`mock_placeholder` 只用于离线验证目录和清单，不作为正式生产输出。

## 快速开始

生成 20 条分镜、前期调研文件和 image2 待生图请求：

```powershell
cd .\scripts
python .\run_mvp.py run --total-shots 20 --provider codex_image2
```

同一选题的后续命令必须复用同一个中文工程目录。推荐先运行 `mine-market` 生成或复用项目目录，再把该目录作为 `--project-dir` 传给拆帧、生图准备、登记图片和导出步骤；不要让每一步生成新的时间戳目录或英文目录。

如果已经完成联网调研，可把调研笔记保存为 JSON 并传入：

```powershell
python .\run_mvp.py run --input-json ..\output\<项目目录>\00_输入\原始输入.json --total-shots 20 --provider codex_image2 --research-json ..\output\<项目目录>\00_输入\原始调研笔记.json
```

先对主题执行光厂两轮关键词反挖：

```powershell
python .\run_mvp.py mine-market --topic "端午节 AI 视频素材" --seed-keywords "端午节,赛龙舟,粽子,包粽子,端午习俗"
```

如果光厂页面触发 JS/反爬，先用浏览器导出公开 DOM/JSON，再用离线导入模式：

```powershell
python .\run_mvp.py mine-market --topic "端午节 AI 视频素材" --first-pass-source-json ..\output\<项目目录>\00_输入\光厂第一轮导入.json --no-live-fetch
```

把反挖摘要喂给新项目，让 `镜头组规划.json` 继承商业方向与镜头比例：

```powershell
python .\run_mvp.py run --total-shots 24 --provider codex_image2 --market-mining-summary ..\output\<项目目录>\00_调研\市场反挖\市场反挖摘要.json
```

采集市场参考封面图到项目调研目录：

```powershell
python .\run_mvp.py collect-market-assets --source-json .\projects\<项目目录>\00_输入\market_reference_来源信息.json --project-dir .\projects\<项目目录> --max-images 24
```

采集公开小样视频关键帧并去水印到项目调研目录：

```powershell
python .\run_mvp.py collect-video-frames --url "<光厂作品链接或公开视频小样链接>" --project-dir .\projects\<项目目录> --title "参考作品名"
```

默认写入 `00_调研/视频参考帧/`，生成 `视频参考帧清单.json`、`视频参考帧索引.jsonl`、`视频镜头索引.jsonl` 和总览拼图。默认 `--mode keyframes`，避免全量帧造成存储和检索成本膨胀；确需逐帧保存时使用 `--mode every-frame --max-frames 0`，并确认本地空间足够。

按 TransNetV2 场景切分并每个场景只保留一张代表图：

```powershell
python .\run_mvp.py collect-scene-frames --url "<光厂作品链接或公开视频小样链接>" --project-dir .\projects\<项目目录> --title "参考作品名" --threshold 0.5 --min-scene-duration 2.0
```

`collect-scene-frames` 会复用旧项目 `E:\MyDrivers\ruanjian\picVideos` 中的 TransNetV2 权重和 `.venv`，默认输出仍写入 `00_调研/视频参考帧/`；每个 `场景_XXXX` 只保存一张中点代表图，并复用 `remwm/opencv/none` 去水印后端。

按第二轮市场信号选择高价值视频并批量拆分候选参考帧：

```powershell
python .\run_mvp.py prepare-high-value-video-frame-queue --project-dir .\projects\<项目目录> --max-works 30
python .\run_mvp.py collect-high-value-video-frames --project-dir .\projects\<项目目录> --initial-works 10 --min-total-frames 300 --max-works 30 --workers 6 --scene-threshold 0.28 --min-scene-duration 0.6
```

Electron 勾选“参考帧”后，复制精选帧、生成 Codex 拼图打标任务，并把精选参考帧绑定到分镜：

```powershell
python .\run_mvp.py build-selected-reference-frames --project-dir .\projects\<项目目录> --max-sheet-items 12
python .\run_mvp.py bind-reference-frames --project-dir .\projects\<项目目录>
```

根据精选参考帧和视觉复核分析，生成可直接导入 JiaoziStudio 的 80 镜头画面分镜脚本：

```powershell
python .\run_mvp.py export-jiaozi-storyboard --project-dir .\projects\<项目目录> --shot-count 80 --duration-per-shot 4
```

对已经导出的旧脚本逐镜头审校并自动修正明显错配：

```powershell
python .\run_mvp.py audit-jiaozi-storyboard --project-dir .\projects\<项目目录> --auto-fix
```

如果已有 `市场参考图清单.json`，新建项目时可让分镜参考图计划自动匹配本地市场参考图：

```powershell
python .\run_mvp.py run --total-shots 24 --provider codex_image2 --market-reference-assets ..\output\<项目目录>\00_调研\市场参考图清单.json
```

离线测试目录、清单和版本逻辑：

```powershell
cd .\scripts
python .\run_mvp.py run --total-shots 20 --provider mock_placeholder
```

## image2 生图步骤

先准备当前可执行的生图请求：

```powershell
python .\run_mvp.py prepare-image2 --project-dir .\projects\<项目目录>
```

默认按独立镜头准备请求；如果某条镜头显式引用的本地参考图文件尚未上传或不存在，该镜头会进入 blocked。确实要一次性写出全部请求时才使用 `--all`。

对 `05_审核/生图队列.json` 中 `prepared` 列表里的每个 `image2_request_path`：

1. 读取其中的 `prompt`、`negative_prompt` 和 `aspect_ratio`。
2. 调用 Codex 内置 image2 生图能力生成图片。
3. 保存或取得 image2 结果图片的本地路径。
4. 登记图片：

```powershell
python .\run_mvp.py register-image --project-dir .\projects\<项目目录> --shot-id shot_001 --source-image <image2输出图片路径>
```

登记后脚本会复制为 `版本1.png`，同步为 `当前图.png`，写入 `审核记录.json`，并更新导出清单。

## 前期调研步骤

正式生成分镜前必须先调研主题：

1. 读取 `00_调研/搜索词.json` 或由 Codex 根据选题直接生成搜索词。
2. 只能在调研白名单内搜索代表性素材结果和竞品素材，不得使用白名单外网页补方向。
3. 先在光厂/VJShi 跑 `mine-market` 两轮反挖：第一轮用 3-5 个种子词按平台默认排序搜索，详情页提取标题、详情关键词和公开预览；第一轮只做语义关键词整理并生成买家搜索提示词；第二轮只使用这些提示词再次搜索并取每条前 10 个作品，第二轮详情完成后才结合购买量、销售额/素材收入、点击量做方向优先级。
4. 其他白名单平台只做补充验证和参考图补充，不得盖过光厂主市场信号；国外高端平台主要用于镜头语言，不作为国内商业需求唯一依据。
5. 普通命令行请求遇到反爬或 JS 挑战时，使用 Chrome/DevTools 从页面 DOM 提取公开图片 URL 和关键词，再用 `mine-market --first-pass-source-json ... --no-live-fetch` 或 `collect-market-assets` 处理。
6. 把每个白名单来源整理成 `来源笔记.json` 条目：来源类型、URL、摘要、代表画面、关键词、避坑点；白名单外来源不得写入 `来源笔记.json`。
7. 把市场封面资产整理成 `市场参考图清单.json`，本地图片放在 `参考图/`，只用于调研和参考，不作为交付素材。
8. `mine-market` 完成两轮反挖后，必须把调研摘要和候选方向交给用户，并主动询问是否继续采集高价值作品的公开预览视频、去水印拆帧、进入 Electron 参考帧挑选；用户未确认时停止在调研结果，不自动运行高价值视频拆帧。
9. 对市场参考图打分并归类：市场信号、预览质量、元数据相关度、参考安全性和平台优先级共同决定 `reference_score`；`reference_score >= 70` 且低风险的图才自动进入图生图参考计划。
10. 根据资料更新 `视觉分类.json`、`市场信号映射.json`、`视觉需求矩阵.json`、`创意角度.json` 和 `镜头组规划.json`。
11. `市场信号映射.json` 必须回答“市场为什么需要这类画面”：命中的来源、关键词、购买/下载/搜索信号、高价值画面、用途和避坑点。
12. `视觉需求矩阵.json` 必须回答“这类画面值不值得生成多少”：市场需求、AI 可生成性、视频动作潜力、商业复用价值、风险分和推荐权重。
13. 生成 `参考图规划.json`：普通镜头默认 `standalone`；参考图按用途和画面价值绑定，普通参考图通常 1 次，高价值动作/空间/人物关系图可复用 2-3 次。复用超过 1 次时第一条必须是 `anchor`，后续必须是 `derived_view` 并指向 `reference_shot_id`，低相关或高风险图为 0 次，仅保留为市场证据。
14. 生成分镜前先写入 `00_输入/脚本创作简报.json`，固定默认画幅 `16:9`、无旁白、无字幕；风格定位、目标买家、情绪节奏、镜头语言偏好和商业用途由调研数据推导，除主题和可选时长外，不要求用户额外补齐。
15. 生成分镜时优先遵循 `脚本创作简报.json` 与 `镜头组规划.json` 的镜头比例和代表画面，且每组镜头数量必须能追溯到 `视觉需求矩阵.json`。

调研借鉴画面类型、素材需求、镜头语言、构图、光线、色彩和商业质感，不复刻真实品牌、企业 UI、Logo、厂牌、水印、包装细节或可识别版权画面。高分参考图和精选参考帧可以用于 image2 图生图方向输入，允许相似参考，但最终生成图与任一来源图相似度目标不得超过 90%。

### 调研白名单

高价值方向调研只能使用以下素材交易/授权平台：

- 国内主力：光厂/VJShi（`vjshi.com`）、新片场素材（`stock.xinpianchang.com`）、视觉中国 VCG（`vcg.com`）。
- 国外主力：Pond5（`pond5.com`）、Shutterstock Video（`shutterstock.com`）、Adobe Stock Video（`stock.adobe.com`）、Getty Images Creative Video（`gettyimages.com`）、iStock Footage（`istockphoto.com`）。
- 国外高端镜头语言参考：Artgrid（`artgrid.io`）、Filmsupply（`filmsupply.com`）、Dissolve（`dissolve.com`）。

硬性排除：摄图网、包图网、千图网、图虫创意、135editor、公众号排版站、教程站、SEO 聚合页、Storyblocks、Motion Array、Envato/Envato Elements 都不得进入 `来源笔记.json`、`市场信号映射.json` 或 `视觉需求矩阵.json`，最多只能在人工说明里作为“不要参考”的低质量来源备注。

## 主要操作

- 新建项目：运行 `run_mvp.py run` 或调用 `ai_video_asset_skill.main_orchestrator.run_skill(user_input)`。
- 重生镜头：使用 `regenerate` 子命令；旧图保留，新图写成 `v2.png`、`v3.png`。
- 替换当前图：调用 `replace_current_image(project_dir, shot_id, image_version, reason)`。
- 扩展锚点图：使用 `expand` 子命令，基于指定 `shot_id/当前图.png` 生成更多角度请求。
- 查看失败队列：使用 `failed-queue` 子命令。
- 导出已通过清单：使用 `export-approved` 子命令。
- 导出画布脚本：使用 `export-package` 子命令；默认写入 `06_导出/JiaoZistudio专用脚本.json`，不再生成压缩包。
- 导出精选参考帧驱动的 JiaoziStudio 80 镜头脚本：使用 `export-jiaozi-storyboard` 子命令；默认写入 `06_导出/JiaoziStudio专用80镜头脚本.json`，并保留每张参考帧的本地 `sourcePath` 和 `file://` 地址。
- 逐镜头审校画布脚本：使用 `audit-jiaozi-storyboard --auto-fix` 子命令；默认读取 `06_导出/JiaoziStudio专用80镜头脚本.json`，输出 `JiaoziStudio逐镜头参考审校报告.json/.md`，并在明显冲突时解绑参考图、重写图片/视频提示词。
- 可视化协作：进入 `electron-viewer/` 运行 `npm install && npm start`，选择项目目录后查看两轮作品、关键词、商业方向、参考图评分，并把人工标记写入 `00_调研/市场反挖/人工审核.json`。

## 生产规则

- 通用商业素材包第一性原理：先判断客户会买哪些镜头，再匹配参考帧，再写差异化提示词。不要从参考图出发硬凑 80 个相似画面，也不要为了复刻某张参考图牺牲素材包的可售性、覆盖面和剪辑连贯性。
- `globalStyle` / `stylePrompt` 只能包含视觉风格、色调、光线、画质、镜头稳定性、商业可售性和版权安全策略；不得写入具体主体、场景、道具、人种、服饰、动作、品牌、行业实体或单个画面内容。具体画面必须放到单镜头的 `主体`、`场景`、`景别构图`、`参考图使用` 等字段。
- 通用镜头组默认覆盖：`开场建立`、`主体展示`、`过程动作`、`细节特写`、`人物/使用场景`、`转场氛围`、`成果/情绪`、`结尾留白`。不同主题按市场信号、参考帧覆盖和商业用途自动配比；非人物类主题不得强行加入人物、西装、合同、会议室等商务元素。
- 领域隔离优先于通用模板：每个镜头只能从当前主题域、`subject`、`action`、`scene`、`shot_role` 和绑定参考帧中取画面信息。通用模板里的“进入画面”“主体动作”“空间透视”等词不能触发其他领域的默认场景或道具。新能源汽车主题应使用车辆、道路、前车距离、HUD、感知光效、充电枪、线缆、电池包、电芯、产线、机械臂、工程师、能源设施等语义；除非镜头主体明确是车企人员或工程师使用场景，不得出现商务人士、会议区域、合同、手持文件、会议桌、桌面道具等商务签约语义。
- 参考帧分析必须同时保留中文可读 `ai_prompt_analysis` 和结构化字段：`visual_summary`、`subject_type`、`scene_type`、`shot_role_tags`、`composition_tags`、`motion_potential`、`commercial_use_cases`、`topic_fit_score`、`image2_usage_weight`、`reference_use_policy`、`risk_flags`、`prompt_ready_brief`、`negative_prompt_notes`。旧项目只有 `ai_prompt_analysis` 时允许降级解析，但新分析必须按结构化契约写回。
- 参考帧是“素材池”，不是每个镜头都必须绑定的 image2 参考。参考帧绑定必须按用途匹配：建立镜头匹配空间/环境/宽幅图，细节镜头匹配局部/材质/微距图，动作镜头匹配操作/互动姿态，转场和结尾匹配光影、留白、空镜或氛围图。没有明确匹配关系的镜头必须保持原创规划，不要为了用完参考图而强行连接；低相关、水印、Logo、可读文字、多宫格、明显版权风险帧只作为市场证据或构图/风格弱参考。每张参考帧动态计算 `reuse_budget`：证据/高风险为 0，普通参考为 1，高价值可多机位画面为 2，强场景/强动作/强商业价值画面最多 3；复用超过 1 次时必须形成 `anchor -> derived_view` 链，派生图直接参考锚点生成图，不再直接连接上传原始参考图。
- JiaoziStudio 图片提示词必须像人类摄影导演描述一张最终画面：直接写主体、场景、前中后景、镜头位置、光线、材质、画面密度和商业用途，不得硬套固定字段模板，不得写“围绕某某生成素材”“画面 brief”“补充要求”等元叙述。允许保留少量稳定标题，例如 `生成图片：`、`参考图使用：`、`整体质感：`、`不要出现：`，但正文必须是可直接喂给生图模型的画面描述。
- 参考图说明必须是“当前镜头要参考这张图的哪些地方”：构图、机位、光线、景深、主体位置、手部关系、材质或空间层次；同时明确不要照搬人物身份、Logo、水印、可读文字、真实品牌、真实公司、签名和可识别版权细节。不得把 `reuse_budget`、`usage_role`、标签列表等机器字段直接塞进生图提示词。
- JiaoziStudio 视频提示词必须从当前生成图出发写 image-to-video 运动指令，重点描述镜头运动、主体运动、环境运动和稳定约束；不得给当前图片新增另一个场景、另一个主体职业或另一套道具，不得把道路切成会议室、把充电站切成办公室、把产线切成签约现场。需要转场时必须拆成独立镜头。不要重复大段图片描述，不要写时长前缀，不要硬套 `视频运镜 / 动作重点 / 主体动态 / 场景动画` 固定栏。楼宇外景、空会议室、签字特写、握手、多人会议、走廊入场、转场留白、新能源道路巡航、充电连接、电池特写、汽车工厂、工程师调试等必须使用各自领域的不同运动策略。
- 每次导出或导入旧脚本前必须执行逐镜头参考审校。审校优先级：先看镜头主体/动作是否与参考帧视觉分析一致，再看图片提示词有没有明确说明“参考这张图的哪些地方”，再看视频提示词是否与当前画面动作一致，最后做跨主题冲突词扫描。冲突处理原则：明显错配直接解绑参考图并改为原创规划；视频提示词跨主题污染时必须按当前镜头主体和动作重写；只有构图、光线或质感可参考但主体不一致时，提示词必须写成弱参考，不得让模型把参考图主体带进当前镜头。审校报告中 `blocking_count` 必须为 0，且主题域冲突词命中为 0，脚本才可交付。
- 导出前必须做去重与多样性检查：统计主体、场景、构图和参考帧复用次数。超过阈值时优先换镜头组、换参考帧、改景别、改留白方向或降权为转场/证据帧，避免整包画面同质化。
- 每条分镜只描述一个明确画面瞬间。
- 分镜前必须先分析主题代表画面和商业素材需求，避免生成泛泛的科技图。
- 所有分镜、提示词、质检建议和面向 Codex 的说明都使用中文。
- 市场参考图只用于理解题材、构图、色彩、镜头类型和关键词覆盖，不能作为最终交付图，也不能照搬生成。
- 视频小样参考帧只用于拆解镜头语言、构图、光线、色彩和节奏，不作为最终交付素材；去水印后的帧不能直接商用。精选参考帧允许作为相似参考，但最终生成图与来源帧相似度目标不得超过 90%，且不得保留真实品牌、Logo、水印、可读包装或可识别版权元素。
- 生图提示词必须写成详细生产 brief，至少包含输出定位、核心画面、主体设定、前中后景、镜头语言、光线色彩、材质细节、画面细节密度、文字策略、参考图使用和禁止项；不要只把分镜字段简单拼接。
- 人物类且国内销售语境明确时，人物、空间、工装和场景语境优先贴合中国市场；主题不是人物类时，不得强行加入中国人、中国工程师、中国企业员工等元素。
- 默认不要文字；如果画面语义确实需要文字，只允许少量贴合场景的大号清晰中文，避免后续生视频时模糊、畸形或乱码。禁止小字、密集字、品牌字、Logo 字、水印和无意义中英文。
- 同场景多景别、多角度可以复用同一高价值参考素材，但必须改变至少两项：景别、机位、前景遮挡、动作阶段、运镜或留白方向；第一张生成 `anchor` 锚点图，后续 1-2 张 `derived_view` 必须以上一张锚点图为直接参考，保持同一空间、同一人物气质、同一服装体系、同一光线色调和连续逻辑气氛。
- 每条分镜、`分镜总表.json`、`详细脚本.json`、单条提示词和 `生图请求.json` 都必须带 `reference_dependency`；可视化连线只是辅助展示，实际依赖以该字段为准。
- 每个选题必须有 `风格设定.json` 锁定视觉统一性。
- 商业可售性优先：无商标标志、无品牌名、无可读文字、无水印、无版权角色、无脏乱或廉价感。
- 每个选题只保留一个中文工程目录，每条分镜独立图片目录；面向用户查看的工程目录名、分镜、提示词、审核说明和交付说明都使用中文。内部机器契约文件名和 JSON 字段可保持稳定英文，以避免破坏已有脚本引用，但不得用英文内部任务名派生新的工程目录。
- 图片版本保留为 `版本1.png`、`版本2.png`、`版本3.png`；当前采用版本复制为 `当前图.png`。
- 重生或替换时不删除旧版本，必须写入 `05_审核/替换记录.json`。
- 重试必须受 `user_input_max_retry` 限制，避免重复生图造成额度浪费。

## 参考

需要字段、目录、状态机、提示词模板和成本规则时，读取 `references/workflow-contract.md`。
## 光厂作品详情采集规则

- 光厂调研脚本按模块拆分调用：搜索页采集用 `fetch-vjshi-search-results`，作品详情采集用 `fetch-vjshi-work` / `fetch-vjshi-works`，不要把搜索页解析和详情页解析混成一个不可复用脚本。
- 关键词搜索或已打开搜索页采集使用：
```powershell
python -m ai_video_asset_skill.main_orchestrator fetch-vjshi-search-results --keyword "机器人" --output-jsonl .\projects\<项目目录>\00_调研\市场反挖\光厂搜索_机器人.jsonl --limit 80
```
- 如果已经在浏览器里选好了“视频素材”等筛选条件，也可以直接传当前搜索页 URL：
```powershell
python -m ai_video_asset_skill.main_orchestrator fetch-vjshi-search-results --url "https://www.vjshi.com/so/2374.html?categoryIdForSoftware=230&st=y" --keyword "机器人" --output-jsonl .\projects\<项目目录>\00_调研\市场反挖\光厂搜索_机器人.jsonl
```
- 搜索页采集结果只记录 `search_keyword`、`rank`、`title`、`work_url`、`work_id`、`cover_url`、`aigc_flag` 等搜索页可见线索；购买、点击、上传日期、文件大小、作者、预览视频等详情字段必须在下一步用详情采集脚本获取。
- 作品详情的数据主权归 `fetch-vjshi-work` / `fetch-vjshi-works`，不要从搜索页卡片、关联推荐、全页面散乱数字里推断详情字段。
- 搜索页只负责提供候选作品 URL、搜索关键词、平台默认排序和封面线索；一旦进入作品层级，标题、购买、点击、上传日期、文件大小、AIGC 说明、作者、预览视频、预览图、详情关键词必须以作品详情页解析结果为准。
- 第一轮关键词分析只整理标题、详情关键词和来源搜索词，输出跟主题相关的关键词和买家搜索提示词；购买量、点击量、上传时间、素材收入等字段只能在第二轮详情完成后用于商业方向优先级，不参与第一轮关键词发现。
- 单个作品测试或补采使用：
```powershell
python -m ai_video_asset_skill.main_orchestrator fetch-vjshi-work --url "<光厂作品URL>" --search-keyword "<来源搜索词>"
```
- 批量采集作品详情使用：
```powershell
python -m ai_video_asset_skill.main_orchestrator fetch-vjshi-works --url-file .\projects\<项目目录>\00_输入\光厂作品链接.txt --output-jsonl .\projects\<项目目录>\00_调研\市场反挖\光厂作品详情.jsonl --search-keyword "<来源搜索词>"
```
- `fetch-vjshi-works` 支持 TXT、JSON、JSONL URL 输入；JSON/JSONL 中可使用 `work_url`、`url` 或 `page_url` 字段。
- 批量采集遇到单个 URL 失败时，不中断整批；失败项写入 `errors`，成功项继续写入输出。
- 采集只保存公开可见的页面元数据、预览图、公开小样/预览视频地址和关键词；不要下载付费原片，不保存账号密钥、Cookie 或登录凭据。
- 如果详情页触发 gzip、JS Cookie 挑战等公开访问保护，脚本会自动处理；若仍无法解析，必须把该作品标记为 `needs_recheck`，不要编造购买量、点击量、收入或关键词。

## 高价值参考帧补采与人工筛选规则

- 高价值公开视频小样默认先采集前 10 个作品，并使用 TransNetV2 高敏场景切分；每个检测场景只保留 1 张代表帧。若详情声明时长和实际下载视频时长明显不一致，必须标记小样不完整风险，再决定是否改用人工下载小样或换源。
- 如果前 10 个作品的一场一帧参考图总数少于 300 张，必须继续按第二轮市场信号补充作品链接并拆分，直到参考图总数不少于 300 张，或最多采集 30 个作品。
- 不要为了凑满 300 张而切换到每秒抽帧或逐帧密集抽帧；优先增加高价值作品来源，减少重复相似帧和人工筛选负担。
- 公开预览视频帧只能用于镜头语言、构图、光线、色彩和商业质感参考，不能作为最终交付素材或直接商用素材。
- 所有需要人工判断的参考帧必须在 Electron 的“参考帧”页面筛选；用户标记 `high_value` 或 `image2_reference` 后，运行/点击保存精选参考帧，将图片复制到 `00_调研/精选参考帧/帧图片/`，并生成 `精选参考帧清单.json`、`参考帧分析任务.json`、`分析拼图/*.jpg` 和待 Codex 写回的 `参考帧分析.json`。
- 写回 `参考帧分析.json` 前必须完成一次视觉复核：先打开 `分析拼图/*.jpg` 按编号逐帧核对主体、构图、前中后景、光线、色彩、材质和关键道具；对拼图中看不清、容易误判或用户质疑的帧，必须继续打开 `帧图片/精选帧_*.jpg` 单图复核。复核结论必须来自图片画面本身，不得只来自作品标题、文件名、旧分析、frame_id 或 JSON 元数据。
