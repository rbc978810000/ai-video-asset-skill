# ai_video_asset_skill

用于商业 AI 视频素材生产的 Python3 MVP。

## 正式工作流

正式生产使用 `codex_image2` provider。脚本先生成前期调研文件，再生成中文分镜、中文提示词和 `生图请求.json`，然后由 Codex 调用内置 image2 生图能力，最后登记真实图片。

同一选题只使用一个中文工程目录。先期调研和正式生成不传 `--project-dir` 时会优先复用同日同主题目录；后续采集、拆帧、筛选、登记图片和导出命令都应显式传同一个 `--project-dir`，不要让每一步生成新的时间戳目录或英文目录。

```powershell
python .\run_mvp.py run --output-root .\projects --provider codex_image2
python .\run_mvp.py run --output-root .\projects --provider codex_image2 --research-json .\research_notes.json
python .\run_mvp.py register-image --project-dir .\projects\<项目目录> --shot-id shot_001 --source-image <image2输出图片路径>
```

`research_notes.json` 可选；如果不传，脚本会生成默认搜索词、代表画面 taxonomy 和镜头分配表。正式使用时建议先联网调研，再把资料笔记传入。

## 离线测试

离线测试使用 `mock_placeholder`，只验证目录、清单和版本逻辑，不代表真实素材质量。

```powershell
python .\run_mvp.py run --total-shots 20 --output-root .\projects --provider mock_placeholder
```

## 本地依赖

首次运行先安装 Python 依赖并做自检：

```powershell
cd ..\..
python -m pip install -r .\requirements.txt
python .\scripts\check_runtime.py
```

公开视频小样拆帧需要 `opencv-python`、`numpy` 和 `Pillow`。`m3u8` 下载需要 `ffmpeg`；高质量去水印可选配置 `remwm`；TransNetV2 场景切分需要额外配置模型权重和含 TensorFlow 的 Python 环境。推荐通过环境变量配置：

```powershell
$env:AI_VIDEO_FFMPEG="D:\tools\ffmpeg\bin\ffmpeg.exe"
$env:AI_VIDEO_REMWM_ROOT="D:\tools\remwm-win"
$env:AI_VIDEO_TRANSNET_ROOT="D:\tools\picVideos"
$env:AI_VIDEO_TRANSNET_PYTHON="D:\tools\picVideos\.venv\Scripts\python.exe"
$env:AI_VIDEO_TRANSNET_WEIGHTS="D:\tools\picVideos\transnetv2-weights"
python .\scripts\check_runtime.py --strict-video
```

为兼容原本地环境，脚本仍会尝试查找 skill 附近的 `picVideos/` 目录；公开安装用户应优先使用上面的环境变量或命令行参数。

## 常用命令

```powershell
python .\run_mvp.py regenerate --project-dir .\projects\<项目目录> --shot-id shot_018 --reason "人工要求重生"
python .\run_mvp.py expand --project-dir .\projects\<项目目录> --shot-id shot_018 --count 6 --provider codex_image2
python .\run_mvp.py collect-video-frames --url "<光厂作品链接或公开视频小样链接>" --project-dir .\projects\<项目目录>
python .\run_mvp.py collect-scene-frames --url "<光厂作品链接或公开视频小样链接>" --project-dir .\projects\<项目目录> --threshold 0.5 --min-scene-duration 2.0
python .\run_mvp.py prepare-high-value-video-frame-queue --project-dir .\projects\<项目目录> --max-works 30
python .\run_mvp.py collect-high-value-video-frames --project-dir .\projects\<项目目录> --initial-works 10 --min-total-frames 300 --max-works 30 --workers 6
python .\run_mvp.py build-selected-reference-frames --project-dir .\projects\<项目目录>
python .\run_mvp.py failed-queue --project-dir .\projects\<项目目录>
python .\run_mvp.py export-approved --project-dir .\projects\<项目目录>
```

`collect-video-frames` 默认抽关键帧并写入 `00_调研/视频参考帧/`，用 `视频参考帧清单.json` 和 jsonl 索引供后续 agent 检索。确需逐帧保存时才使用 `--mode every-frame --max-frames 0`。
`collect-scene-frames` 使用 `AI_VIDEO_TRANSNET_*` 或命令行参数指定的 TransNetV2 环境做场景切分，每个场景中点只取一张代表图，并复用 `remwm/opencv/none` 去水印后端。
`collect-high-value-video-frames` 默认先采集前 10 个高价值公开视频预览；如果一场一帧后的总参考帧少于 300 张，会继续按市场信号补充作品链接，直到至少 300 张或最多 30 个作品。补采策略不使用每秒抽帧来凑数量，避免产生大量相似图。
Electron 参考帧页用于人工筛选：把需要的帧标记为 `high_value` 或 `image2_reference` 后点击“保存精选参考帧”，会复制到 `00_调研/精选参考帧/帧图片/`，并生成 `精选参考帧清单.json`、`参考帧分析任务.json`、`分析拼图/*.jpg` 和待 Codex 写回的 `参考帧分析.json`。

## 成本说明

`codex_image2` 是正式生图路径，调用时可能消耗真实生成额度；必须按需调用、限制重试、保留版本并避免重复生成。`mock_placeholder` 不调用外部服务，不消耗额度。
