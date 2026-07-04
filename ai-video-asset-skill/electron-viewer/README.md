# Market Mining Viewer

默认项目根目录是 `ai-video-asset-skill/output/`。`mine-market` 和 `run` 不传自定义目录时，会优先复用同日同主题的中文工程目录，找不到才创建新目录；调研、分镜、生图请求、参考帧和导出都应保存在同一个工程目录里。

本地 Electron 观察壳，只读取同一个 AI 视频素材项目目录中的文件：

- `00_调研/市场反挖/*.json`
- `00_调研/市场反挖/*.jsonl`
- `00_调研/市场参考图清单.json`
- `00_调研/视频参考帧/视频参考帧清单.json`
- `00_调研/视频参考帧/视频参考帧索引.jsonl`
- `00_调研/精选参考帧/精选参考帧清单.json`

它允许写回 `00_调研/市场反挖/人工审核.json`，用于人工标记高价值、只作证据、排除、可图生图参考、需要复查。参考帧页点击“保存精选参考帧”后，会调用本地 Python 流程复制 `high_value` / `image2_reference` 帧到 `00_调研/精选参考帧/帧图片/`，并生成 Codex 视觉分析任务。

```powershell
cd ai-video-asset-skill/electron-viewer
npm install
npm start
```

不要在这个壳里保存账号密钥、Cookie 或付费素材原片。Codex/skill 仍然是主执行者。
