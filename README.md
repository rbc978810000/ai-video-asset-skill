# AI Video Asset Skill

Codex skill for AI video commercial asset research, storyboard planning, image prompt generation, reference-frame workflows, and JiaoziStudio export.

## Install

Install this skill from GitHub with Codex's skill installer:

```powershell
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo rbc978810000/ai-video-asset-skill --path ai-video-asset-skill
```

On Windows, the installer script may live here:

```powershell
python $env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo rbc978810000/ai-video-asset-skill --path ai-video-asset-skill
```

Restart Codex after installation.

## What It Includes

- `ai-video-asset-skill/SKILL.md`: the skill instructions and trigger metadata.
- `ai-video-asset-skill/agents/openai.yaml`: UI-facing metadata.
- `ai-video-asset-skill/scripts/`: local Python workflow scripts.
- `ai-video-asset-skill/references/`: workflow contracts and detailed reference material.
- `ai-video-asset-skill/electron-viewer/`: optional local review UI source.
- `ai-video-asset-skill/tests/`: regression tests for the bundled scripts.

Generated outputs, downloaded preview videos, frame extraction results, caches, and `node_modules` are intentionally excluded from the repository.

## Verify Locally

From the skill folder:

```powershell
python -m pytest .\tests -q
```

Validate the skill metadata:

```powershell
$env:PYTHONUTF8='1'
python $env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\ai-video-asset-skill
```

## Optional Viewer

The Electron viewer is a local helper for reviewing market-mining outputs:

```powershell
cd .\ai-video-asset-skill\electron-viewer
npm install
npm start
```

Do not store account secrets, cookies, paid source media, or private production outputs in this repository.
