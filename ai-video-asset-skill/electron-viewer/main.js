const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const { execFile } = require("child_process");
const fsSync = require("fs");
const fs = require("fs/promises");
const path = require("path");

const PROJECTS_ROOT = path.resolve(__dirname, "..", "output");
const AUTO_SYNC_DEBOUNCE_MS = 700;
const projectWatchers = new Map();
let projectsWatcher = null;

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 980,
    minHeight: 680,
    title: "AI Video Market Mining Viewer",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });
  const webContentsId = win.webContents.id;
  win.on("closed", () => closeProjectWatcher(webContentsId));
  win.loadFile(path.join(__dirname, "index.html"));
  ensureProjectsWatcher();
}

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", closeAllWatchers);

function ensureProjectsWatcher() {
  if (projectsWatcher) return;
  try {
    fsSync.mkdirSync(PROJECTS_ROOT, { recursive: true });
    const notify = debounce(() => {
      sendToWindows("projects:changed", { root: PROJECTS_ROOT, changedAt: Date.now() });
    }, AUTO_SYNC_DEBOUNCE_MS);
    projectsWatcher = fsSync.watch(PROJECTS_ROOT, { persistent: false }, notify);
    projectsWatcher.on("error", () => {
      closeProjectsWatcher();
    });
  } catch (error) {
    console.warn(`Unable to watch projects root: ${error.message}`);
  }
}

function watchProjectForSender(sender, projectDir) {
  const root = path.resolve(String(projectDir || ""));
  closeProjectWatcher(sender.id);
  try {
    const stat = fsSync.statSync(root);
    if (!stat.isDirectory()) throw new Error(`Not a directory: ${root}`);
    const notify = debounce(() => {
      if (!sender.isDestroyed()) {
        sender.send("project:changed", { projectDir: root, changedAt: Date.now() });
      }
    }, AUTO_SYNC_DEBOUNCE_MS);
    const watcher = createProjectWatcher(root, notify);
    watcher.on("error", () => closeProjectWatcher(sender.id));
    projectWatchers.set(sender.id, watcher);
    return { ok: true, projectDir: root };
  } catch (error) {
    return { ok: false, projectDir: root, error: error.message };
  }
}

function createProjectWatcher(projectDir, notify) {
  try {
    return fsSync.watch(projectDir, { recursive: true, persistent: false }, notify);
  } catch (_error) {
    return fsSync.watch(projectDir, { persistent: false }, notify);
  }
}

function closeProjectWatcher(webContentsId) {
  const watcher = projectWatchers.get(webContentsId);
  if (!watcher) return;
  watcher.close();
  projectWatchers.delete(webContentsId);
}

function closeProjectsWatcher() {
  if (!projectsWatcher) return;
  projectsWatcher.close();
  projectsWatcher = null;
}

function closeAllWatchers() {
  for (const webContentsId of projectWatchers.keys()) {
    closeProjectWatcher(webContentsId);
  }
  closeProjectsWatcher();
}

function sendToWindows(channel, payload) {
  for (const win of BrowserWindow.getAllWindows()) {
    if (!win.isDestroyed()) win.webContents.send(channel, payload);
  }
}

function debounce(callback, delayMs) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => callback(...args), delayMs);
  };
}

ipcMain.handle("project:list", async () => {
  try {
    await fs.mkdir(PROJECTS_ROOT, { recursive: true });
    const entries = await fs.readdir(PROJECTS_ROOT, { withFileTypes: true });
    const projects = [];
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const projectDir = path.join(PROJECTS_ROOT, entry.name);
      const stat = await fs.stat(projectDir);
      projects.push({
        name: entry.name,
        projectDir,
        updatedAt: stat.mtimeMs,
        hasMarketMining: await exists(path.join(projectDir, "00_调研", "市场反挖")),
        hasStoryboard: await exists(path.join(projectDir, "01_分镜", "分镜总表.json"))
      });
    }
    projects.sort((left, right) => right.updatedAt - left.updatedAt);
    return { root: PROJECTS_ROOT, projects };
  } catch (error) {
    return { root: PROJECTS_ROOT, projects: [], error: error.message };
  }
});

ipcMain.handle("project:select", async () => {
  const result = await dialog.showOpenDialog({
    title: "选择 AI 视频素材项目目录",
    properties: ["openDirectory"]
  });
  if (result.canceled || !result.filePaths.length) return null;
  return result.filePaths[0];
});

ipcMain.handle("project:read", async (_event, projectDir) => {
  const root = path.resolve(String(projectDir || ""));
  const marketDir = path.join(root, "00_调研", "市场反挖");
  return {
    projectDir: root,
    marketDir,
    hasMarketMining: await exists(marketDir),
    projectManifest: await readJson(path.join(root, "项目清单.json"), {}),
    seedKeywords: await readJson(path.join(marketDir, "种子关键词.json"), {}),
    firstPassSearchResults: await readJsonl(path.join(marketDir, "光厂第一轮搜索结果.jsonl")),
    firstPassWorkDetails: await readJsonl(path.join(marketDir, "光厂第一轮作品详情.jsonl")),
    keywordAnalysis: await readJson(path.join(marketDir, "关键词分析.json"), {}),
    commercialDirections: await readJson(path.join(marketDir, "商业AI方向.json"), {}),
    buyerSearchPrompts: await readJson(path.join(marketDir, "买家搜索提示词.json"), {}),
    secondPassSearchResults: await readJsonl(path.join(marketDir, "光厂第二轮搜索结果.jsonl")),
    secondPassWorkDetails: await readJsonl(path.join(marketDir, "光厂第二轮作品详情.jsonl")),
    marketMiningSummary: await readJson(path.join(marketDir, "市场反挖摘要.json"), {}),
    operatorReview: await readJson(path.join(marketDir, "人工审核.json"), defaultReview(root)),
    referenceAssets: await readJson(path.join(root, "00_调研", "市场参考图清单.json"), {}),
    videoReferenceAssets: await readJson(path.join(root, "00_调研", "视频参考帧", "视频参考帧清单.json"), {}),
    videoReferenceFrames: await readJsonl(path.join(root, "00_调研", "视频参考帧", "视频参考帧索引.jsonl")),
    selectedReferenceFrames: await readJson(path.join(root, "00_调研", "精选参考帧", "精选参考帧清单.json"), {})
  };
});

ipcMain.handle("project:watch", async (event, projectDir) => {
  return watchProjectForSender(event.sender, projectDir);
});

ipcMain.handle("project:unwatch", async (event) => {
  closeProjectWatcher(event.sender.id);
  return { ok: true };
});

ipcMain.handle("review:write", async (_event, payload) => {
  const root = path.resolve(String(payload && payload.projectDir ? payload.projectDir : ""));
  const marketDir = path.join(root, "00_调研", "市场反挖");
  await assertDirectory(marketDir);
  const review = sanitizeReview(payload && payload.review, root);
  const outputPath = path.join(marketDir, "人工审核.json");
  await fs.writeFile(outputPath, JSON.stringify(review, null, 2), "utf8");
  return { ok: true, path: outputPath, review };
});

ipcMain.handle("reference-frames:build-selected", async (_event, payload) => {
  const root = path.resolve(String(payload && payload.projectDir ? payload.projectDir : ""));
  await assertDirectory(root);
  const maxSheetItems = Number(payload && payload.maxSheetItems ? payload.maxSheetItems : 12) || 12;
  const scriptPath = path.resolve(__dirname, "..", "scripts", "run_mvp.py");
  const result = await runPython([
    scriptPath,
    "build-selected-reference-frames",
    "--project-dir",
    root,
    "--max-sheet-items",
    String(maxSheetItems)
  ]);
  return { ok: true, ...result };
});

async function assertDirectory(dir) {
  const stat = await fs.stat(dir);
  if (!stat.isDirectory()) throw new Error(`目录不存在：${dir}`);
}

async function exists(file) {
  try {
    await fs.access(file);
    return true;
  } catch (_error) {
    return false;
  }
}

async function readJson(file, fallback) {
  try {
    const text = await fs.readFile(file, "utf8");
    return JSON.parse(text);
  } catch (_error) {
    return fallback;
  }
}

async function readJsonl(file) {
  try {
    const text = await fs.readFile(file, "utf8");
    return text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => JSON.parse(line));
  } catch (_error) {
    return [];
  }
}

function defaultReview(projectDir) {
  return {
    schema_version: "operator-review/v1",
    project_dir: projectDir,
    updated_at: new Date().toISOString(),
    review_labels: ["high_value", "evidence_only", "excluded", "image2_reference", "needs_recheck"],
    work_reviews: {},
    direction_reviews: {},
    prompt_reviews: {},
    asset_reviews: {},
    frame_reviews: {},
    notes: []
  };
}

function sanitizeReview(value, projectDir) {
  const review = value && typeof value === "object" ? value : defaultReview(projectDir);
  return {
    schema_version: "operator-review/v1",
    project_dir: projectDir,
    updated_at: new Date().toISOString(),
    review_labels: Array.isArray(review.review_labels)
      ? review.review_labels
      : ["high_value", "evidence_only", "excluded", "image2_reference", "needs_recheck"],
    work_reviews: objectOrEmpty(review.work_reviews),
    direction_reviews: objectOrEmpty(review.direction_reviews),
    prompt_reviews: objectOrEmpty(review.prompt_reviews),
    asset_reviews: objectOrEmpty(review.asset_reviews),
    frame_reviews: objectOrEmpty(review.frame_reviews),
    notes: Array.isArray(review.notes) ? review.notes : []
  };
}

function objectOrEmpty(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function runPython(args) {
  return new Promise((resolve, reject) => {
    execFile("python", args, { cwd: path.resolve(__dirname, "..", "scripts"), windowsHide: true, timeout: 120000 }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error(stderr.trim() || stdout.trim() || error.message));
        return;
      }
      const text = stdout.trim();
      if (!text) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(text));
      } catch (_parseError) {
        reject(new Error(`Python 输出不是 JSON: ${text}`));
      }
    });
  });
}
