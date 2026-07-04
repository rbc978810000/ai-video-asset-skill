const state = {
  projectDir: "",
  projectsRoot: "",
  projects: [],
  data: null,
  review: null,
  activeFeature: "research",
  reviewDirty: false,
  frameFilters: {
    sourceId: "",
    label: "",
    selection: "",
    minQuality: ""
  },
  selectedBuildStatus: "",
  workSort: {
    first: { key: "", direction: "desc" },
    second: { key: "", direction: "desc" }
  }
};

const AUTO_SYNC_DELAY_MS = 500;
const AUTO_SAVE_DELAY_MS = 300;
let projectListSyncTimer = null;
let projectDataSyncTimer = null;
let reviewSaveTimer = null;
let reviewSaveInFlight = false;
let reviewSaveQueued = false;
let reviewSavePromise = null;
let loadProjectRequestId = 0;
let reviewRevision = 0;

const labels = [
  ["high_value", "\u9ad8\u4ef7\u503c"],
  ["evidence_only", "\u53ea\u4f5c\u8bc1\u636e"],
  ["excluded", "\u6392\u9664"],
  ["image2_reference", "\u53ef\u56fe\u751f\u56fe\u53c2\u8003"],
  ["needs_recheck", "\u9700\u590d\u67e5"]
];

window.addEventListener("DOMContentLoaded", async () => {
  bindChrome();
  bindAutoSync();
  renderPlaceholder();
  await refreshProjects();
});

function bindChrome() {
  document.getElementById("chooseProject").addEventListener("click", async () => {
    const projectDir = await window.marketViewer.selectProject();
    if (projectDir) {
      await flushReviewSave();
      await loadProject(projectDir);
    }
  });

  document.getElementById("projectSelect").addEventListener("change", async (event) => {
    if (event.target.value) {
      await flushReviewSave();
      await loadProject(event.target.value);
    }
  });

  document.querySelectorAll(".feature").forEach((button) => {
    button.addEventListener("click", () => switchFeature(button.dataset.feature));
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(tab.dataset.tab).classList.add("active");
    });
  });
}

function bindAutoSync() {
  if (window.marketViewer.onProjectsChanged) {
    window.marketViewer.onProjectsChanged(scheduleProjectsRefresh);
  }
  if (window.marketViewer.onProjectChanged) {
    window.marketViewer.onProjectChanged((payload) => {
      if (!state.projectDir) return;
      if (normalizePath(payload && payload.projectDir) !== normalizePath(state.projectDir)) return;
      scheduleProjectReload();
    });
  }
  window.addEventListener("beforeunload", () => {
    if (state.reviewDirty) flushReviewSave();
    if (window.marketViewer.unwatchProject) window.marketViewer.unwatchProject();
  });
}

function scheduleProjectsRefresh() {
  clearTimeout(projectListSyncTimer);
  projectListSyncTimer = setTimeout(async () => {
    projectListSyncTimer = null;
    await refreshProjects({ autoSync: true });
  }, AUTO_SYNC_DELAY_MS);
}

function scheduleProjectReload() {
  clearTimeout(projectDataSyncTimer);
  projectDataSyncTimer = setTimeout(async () => {
    projectDataSyncTimer = null;
    if (state.projectDir) await loadProject(state.projectDir, { autoSync: true });
  }, AUTO_SYNC_DELAY_MS);
}

async function refreshProjects(_options = {}) {
  const result = await window.marketViewer.listProjects();
  state.projectsRoot = result.root || "";
  state.projects = result.projects || [];
  renderProjectSelect();
  if (!state.projectDir && state.projects.length) {
    const preferred = state.projects.find((item) => item.hasMarketMining) || state.projects[0];
    await loadProject(preferred.projectDir);
  } else if (!state.projects.length) {
    setProjectStatus(result.error ? `工程目录读取失败：${result.error}` : "工程目录中暂无项目。");
  }
}

function renderProjectSelect() {
  const select = document.getElementById("projectSelect");
  if (!state.projects.length) {
    select.innerHTML = `<option value="">未发现项目</option>`;
    return;
  }
  select.innerHTML = state.projects
    .map((project) => {
      const flag = project.hasMarketMining ? " · 已调研" : project.hasStoryboard ? " · 已分镜" : "";
      return `<option value="${escapeAttr(project.projectDir)}">${escapeHtml(project.name + flag)}</option>`;
    })
    .join("");
  if (state.projectDir) select.value = state.projectDir;
}

async function loadProject(projectDir, options = {}) {
  const requestId = ++loadProjectRequestId;
  const previousProjectDir = state.projectDir;
  try {
    const data = await window.marketViewer.readProject(projectDir);
    if (requestId !== loadProjectRequestId) return;
    const preserveReview = Boolean(
      options.autoSync &&
      state.reviewDirty &&
      normalizePath(previousProjectDir) === normalizePath(projectDir)
    );
    state.projectDir = projectDir;
    state.data = data;
    state.selectedBuildStatus = "";
    state.review = preserveReview ? state.review : data.operatorReview || {};
    if (!preserveReview) {
      state.reviewDirty = false;
      reviewRevision = 0;
    }
    if (window.marketViewer.watchProject) await window.marketViewer.watchProject(projectDir);
    renderProjectSelect();
    setProjectStatus(projectDir);
    renderAll();
  } catch (error) {
    if (requestId !== loadProjectRequestId) return;
    state.data = null;
    state.review = null;
    state.reviewDirty = false;
    reviewRevision = 0;
    setProjectStatus(`读取失败：${error.message}`);
    renderPlaceholder();
  }
}

function switchFeature(feature) {
  state.activeFeature = feature;
  document.querySelectorAll(".feature").forEach((item) => item.classList.toggle("active", item.dataset.feature === feature));
  document.querySelectorAll(".feature-panel").forEach((item) => item.classList.remove("active"));
  document.getElementById(`feature-${feature}`).classList.add("active");
  const titles = { research: "调研", script: "脚本撰写", image: "生图" };
  document.getElementById("featureTitle").textContent = titles[feature] || "工作台";
  if (feature === "script") renderComingSoon("feature-script", "脚本撰写");
  if (feature === "image") renderComingSoon("feature-image", "生图");
}

function setProjectStatus(text) {
  document.getElementById("projectPath").textContent = text || "未选择项目";
}

function renderAll() {
  if (!state.data) {
    renderPlaceholder();
    return;
  }
  renderProjectMeta();
  renderWorks();
  renderKeywords();
  renderDirections();
  renderGallery();
  renderFrames();
  renderReview();
}

function renderProjectMeta() {
  const manifest = state.data.projectManifest || {};
  const seedKeywords = (state.data.seedKeywords || {}).seed_keywords || [];
  const title = manifest.project_title || projectName(state.projectDir);
  const miningState = state.data.hasMarketMining ? "已生成市场反挖数据" : "未发现市场反挖数据";
  document.getElementById("projectMeta").textContent = `${title} · ${miningState}${seedKeywords.length ? ` · 种子词：${seedKeywords.join("、")}` : ""}`;
}

function renderPlaceholder() {
  ["works", "keywords", "directions", "gallery", "frames", "review"].forEach((id) => {
    document.getElementById(id).innerHTML = empty("请选择右上角工程，或先运行 mine-market 生成调研数据。");
  });
  document.getElementById("projectMeta").textContent = state.projectsRoot
    ? `工程根目录：${state.projectsRoot}`
    : "正在读取工程根目录。";
}

function renderWorks() {
  const first = state.data.firstPassWorkDetails || [];
  const second = state.data.secondPassWorkDetails || [];
  document.getElementById("works").innerHTML = `
    <div class="summary-grid">
      ${metric("第一轮详情", first.length)}
      ${metric("第二轮详情", second.length)}
      ${metric("买家提示词", promptItems().length)}
      ${metric("商业方向", directionItems().length)}
    </div>
    <h4>第一轮作品</h4>
    ${workTable(first, "first")}
    <h4>第二轮作品</h4>
    ${workTable(second, "second")}
  `;
  bindSortButtons();
  bindReviewButtons();
}

function renderKeywords() {
  const analysis = state.data.keywordAnalysis || {};
  const classified = analysis.classified_terms || {};
  document.getElementById("keywords").innerHTML = `
    <div class="columns">
      ${termList("题材词", classified.topic_terms)}
      ${termList("画面词", classified.visual_terms)}
      ${termList("镜头词", classified.camera_terms)}
      ${termList("商业用途词", classified.commercial_use_terms)}
    </div>
    <h4>买家搜索提示词</h4>
    <div class="prompt-list">
      ${promptItems().map(promptCard).join("") || empty("暂无提示词")}
    </div>
  `;
  bindReviewButtons();
}

function renderDirections() {
  const rows = directionItems();
  document.getElementById("directions").innerHTML = `
    <div class="direction-grid">
      ${rows.map(directionCard).join("") || empty("暂无商业方向")}
    </div>
  `;
  bindReviewButtons();
}

function renderGallery() {
  const assets = ((state.data.referenceAssets || {}).assets || []);
  document.getElementById("gallery").innerHTML = `
    <div class="gallery-grid">
      ${assets.map(assetCard).join("") || empty("暂无参考图 manifest")}
    </div>
  `;
  bindReviewButtons();
}

function renderFrames() {
  const frames = frameItems();
  const visibleFrames = frames;
  document.getElementById("frames").innerHTML = `
    <div class="frame-toolbar frame-toolbar-simple">
      <button id="selectVisibleFrames">\u5168\u9009\u5f53\u524d\u663e\u793a</button>
      <button id="clearVisibleFrames">\u6e05\u7a7a\u5f53\u524d\u663e\u793a</button>
      <button id="saveSelectedFrames" class="primary-action">\u4fdd\u5b58\u7cbe\u9009\u53c2\u8003\u5e27</button>
    </div>
    <div class="frame-status">
      \u5171 ${visibleFrames.length} \u5f20 \u00b7 \u5df2\u52fe\u9009 ${selectedFrameCount()} \u5f20 ${state.selectedBuildStatus ? "\u00b7 " + escapeHtml(state.selectedBuildStatus) : ""}
    </div>
    <div class="gallery-grid frame-grid">
      ${visibleFrames.map(frameCard).join("") || empty("\u6682\u65e0\u53c2\u8003\u5e27\u3002")}
    </div>
  `;
  bindFrameControls();
}

function renderReview() {
  const review = state.review || {};
  document.getElementById("review").innerHTML = `
    <div class="review-block">
      <h4>人工审核文件</h4>
      <p>写入位置：00_调研/市场反挖/人工审核.json</p>
      <pre>${escapeHtml(JSON.stringify(review, null, 2))}</pre>
    </div>
  `;
}

function renderComingSoon(targetId, title) {
  document.getElementById(targetId).innerHTML = `
    <div class="coming-soon">
      <h3>${escapeHtml(title)}</h3>
      <p>这个功能位已经预留，当前先集中做调研协作。</p>
    </div>
  `;
}

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function workTable(rows, tableId) {
  if (!rows.length) return empty("暂无作品数据");
  const sortedRows = sortWorkRows(rows, tableId);
  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>封面</th><th>关键词</th><th>标题</th><th>购买</th><th>${sortHeader(tableId, "download", "下载")}</th><th>${sortHeader(tableId, "income", "收入")}</th><th>上传</th><th>审核</th>
          </tr>
        </thead>
        <tbody>
          ${sortedRows.map((row) => `
            <tr>
              <td>${image(row.cover_url || (row.preview_images || [])[0], row.title)}</td>
              <td>${escapeHtml(row.search_keyword || "")}</td>
              <td><a href="${escapeAttr(row.work_url || "#")}">${escapeHtml(row.title || row.work_id || "")}</a></td>
              <td>${row.purchase_count ?? ""}</td>
              <td>${formatDownload(row)}</td>
              <td>${formatIncome(row)}</td>
              <td>${escapeHtml(row.upload_time || "")}</td>
              <td>${reviewButtons("work_reviews", row.work_id || row.work_url)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function sortHeader(tableId, key, label) {
  const current = state.workSort[tableId] || {};
  const active = current.key === key;
  const marker = active ? (current.direction === "asc" ? "↑" : "↓") : "↕";
  return `<button class="sort-button ${active ? "active" : ""}" data-table-id="${escapeAttr(tableId)}" data-sort-key="${escapeAttr(key)}" title="${escapeAttr(label)}排序">${escapeHtml(label)} <span>${marker}</span></button>`;
}

function bindSortButtons() {
  document.querySelectorAll(".sort-button").forEach((button) => {
    button.addEventListener("click", () => {
      const tableId = button.dataset.tableId;
      const key = button.dataset.sortKey;
      const current = state.workSort[tableId] || { key: "", direction: "desc" };
      state.workSort[tableId] = {
        key,
        direction: current.key === key && current.direction === "desc" ? "asc" : "desc"
      };
      renderWorks();
    });
  });
}

function sortWorkRows(rows, tableId) {
  const current = state.workSort[tableId] || {};
  if (!current.key) return rows;
  return rows.slice().sort((left, right) => {
    const leftValue = numericSortValue(left, current.key);
    const rightValue = numericSortValue(right, current.key);
    if (leftValue === null && rightValue === null) return 0;
    if (leftValue === null) return 1;
    if (rightValue === null) return -1;
    return current.direction === "asc" ? leftValue - rightValue : rightValue - leftValue;
  });
}

function numericSortValue(row, key) {
  if (key === "income") return incomeAmount(row);
  if (key === "download") return downloadAmount(row);
  return null;
}

function termList(title, rows) {
  const items = Array.isArray(rows) ? rows.slice(0, 24) : [];
  return `
    <section class="list-panel">
      <h4>${title}</h4>
      ${items.map((row) => `
        <div class="term-row">
          <span>${escapeHtml(row.term || "")}</span>
          <strong>${row.weighted_score ?? row.count ?? ""}</strong>
        </div>
      `).join("") || empty("暂无")}
    </section>
  `;
}

function promptCard(row) {
  return `
    <article class="card">
      <div class="card-head">
        <h4>${escapeHtml(row.prompt || "")}</h4>
        <span>${escapeHtml(row.direction_name || "")}</span>
      </div>
      <p>${escapeHtml(row.market_signal_summary || "")}</p>
      <div>${chips(row.commercial_use)}</div>
      <div>${reviewButtons("prompt_reviews", row.prompt_id || row.prompt)}</div>
    </article>
  `;
}

function directionCard(row) {
  return `
    <article class="card direction">
      <div class="card-head">
        <h4>${escapeHtml(row.direction_name || "")}</h4>
        <span>score ${row.market_signal_score ?? ""}</span>
      </div>
      <p>${escapeHtml(row.prompt_guidance_for_image_generation || "")}</p>
      <div>${chips(row.buyer_search_prompts)}</div>
      <dl>
        <dt>AI</dt><dd>${row.ai_generation_feasibility ?? ""}</dd>
        <dt>Motion</dt><dd>${row.video_motion_potential ?? ""}</dd>
        <dt>Reuse</dt><dd>${row.commercial_reuse_value ?? ""}</dd>
        <dt>Risk</dt><dd>${row.risk_score ?? ""}</dd>
      </dl>
      <div>${reviewButtons("direction_reviews", row.direction_id || row.direction_name)}</div>
    </article>
  `;
}

function assetCard(row) {
  const src = localAssetSrc(row.local_path);
  return `
    <article class="asset">
      ${image(src, row.title)}
      <h4>${escapeHtml(row.title || row.asset_id || "")}</h4>
      <p>score ${row.reference_score ?? ""}</p>
      <div>${chips(row.reference_risk_flags)}</div>
      <div>${reviewButtons("asset_reviews", row.asset_id || row.local_path)}</div>
    </article>
  `;
}

function frameCard(row) {
  const src = localAssetSrc(row.thumb_path || row.path || row.resolved_thumb_path || row.resolved_path);
  const current = frameLabel(row.frame_id || "");
  const checked = isSelectedReferenceLabel(current);
  return `
    <article class="frame-card ${checked ? "selected-frame" : ""}">
      <label class="frame-check" title="\u52fe\u9009\u4e3a\u7cbe\u9009\u53c2\u8003\u5e27">
        <input type="checkbox" data-frame-check="${escapeAttr(row.frame_id || "")}" ${checked ? "checked" : ""} />
        <span></span>
      </label>
      ${image(src, "")}
    </article>
  `;
}

function frameItems() {
  const direct = state.data && state.data.videoReferenceFrames;
  if (Array.isArray(direct) && direct.length) return direct;
  return ((state.data.videoReferenceAssets || {}).assets || []);
}

function selectedFrameCount() {
  const reviews = ((state.review || {}).frame_reviews || {});
  return Object.values(reviews).filter((item) => item && ["image2_reference", "high_value"].includes(item.label)).length;
}

function markedFrameCount() {
  return Object.keys(((state.review || {}).frame_reviews || {})).length;
}

function frameSourceItems() {
  return ((state.data && state.data.videoReferenceAssets || {}).sources || []);
}

function filteredFrameItems(frames) {
  const minQuality = state.frameFilters.minQuality === "" ? null : Number(state.frameFilters.minQuality);
  return frames.filter((frame) => {
    const label = frameLabel(frame.frame_id || "");
    const selected = isSelectedReferenceLabel(label);
    if (state.frameFilters.sourceId && frame.source_id !== state.frameFilters.sourceId) return false;
    if (state.frameFilters.label && label !== state.frameFilters.label) return false;
    if (state.frameFilters.selection === "selected" && !selected) return false;
    if (state.frameFilters.selection === "unselected" && selected) return false;
    if (state.frameFilters.selection === "marked" && !label) return false;
    if (minQuality !== null && Number(frame.quality_score || 0) < minQuality) return false;
    return true;
  });
}

function frameLabel(frameId) {
  return ((((state.review || {}).frame_reviews || {})[frameId] || {}).label) || "";
}

function isSelectedReferenceLabel(label) {
  return label === "high_value" || label === "image2_reference";
}

function bindFrameControls() {
  const selectVisible = document.getElementById("selectVisibleFrames");
  const clearVisible = document.getElementById("clearVisibleFrames");
  const save = document.getElementById("saveSelectedFrames");
  if (selectVisible) selectVisible.addEventListener("click", () => applyBulkFrameLabel("image2_reference"));
  if (clearVisible) clearVisible.addEventListener("click", () => applyBulkFrameLabel(""));
  if (save) save.addEventListener("click", saveSelectedReferenceFrames);
  document.querySelectorAll("[data-frame-check]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => setFrameChecked(checkbox.dataset.frameCheck || "", checkbox.checked));
  });
}

function updateFrameFilter(key, value) {
  state.frameFilters[key] = value;
  renderFrames();
}

function setFrameChecked(frameId, checked) {
  if (!frameId) return;
  state.review.frame_reviews = state.review.frame_reviews || {};
  if (checked) {
    state.review.frame_reviews[frameId] = {
      label: "image2_reference",
      updated_at: new Date().toISOString()
    };
  } else {
    delete state.review.frame_reviews[frameId];
  }
  markReviewChanged();
  renderFrames();
}

async function saveSelectedReferenceFrames() {
  if (!state.projectDir) return;
  state.selectedBuildStatus = "\u6b63\u5728\u4fdd\u5b58\u7cbe\u9009\u53c2\u8003\u5e27...";
  renderFrames();
  try {
    await flushReviewSave();
    const result = await window.marketViewer.buildSelectedReferenceFrames({
      projectDir: state.projectDir,
      maxSheetItems: 12
    });
    state.selectedBuildStatus = "\u5df2\u4fdd\u5b58 " + (result.system_output_selected_count || 0) + " \u5f20\uff0c\u751f\u6210 " + (result.system_output_contact_sheet_count || 0) + " \u4e2a Codex \u5206\u6790\u62fc\u56fe\u3002";
    await loadProject(state.projectDir, { autoSync: true });
    state.selectedBuildStatus = "\u5df2\u4fdd\u5b58 " + (result.system_output_selected_count || 0) + " \u5f20\uff0c\u751f\u6210 " + (result.system_output_contact_sheet_count || 0) + " \u4e2a Codex \u5206\u6790\u62fc\u56fe\u3002";
    renderFrames();
  } catch (error) {
    state.selectedBuildStatus = "\u4fdd\u5b58\u5931\u8d25\uff1a" + error.message;
    renderFrames();
  }
}

function applyBulkFrameLabel(label) {
  const visibleFrames = frameItems();
  state.review.frame_reviews = state.review.frame_reviews || {};
  visibleFrames.forEach((frame) => {
    const frameId = frame.frame_id || "";
    if (!frameId) return;
    if (!label) {
      delete state.review.frame_reviews[frameId];
      return;
    }
    state.review.frame_reviews[frameId] = {
      label,
      updated_at: new Date().toISOString()
    };
  });
  markReviewChanged();
  renderAll();
}

function directionItems() {
  const value = state.data && state.data.commercialDirections;
  if (Array.isArray(value)) return value;
  return (value && value.directions) || [];
}

function promptItems() {
  const value = state.data && state.data.buyerSearchPrompts;
  if (Array.isArray(value)) return value;
  return (value && value.prompts) || [];
}

function reviewButtons(bucket, id) {
  const safeId = escapeAttr(String(id || ""));
  const current = (((state.review || {})[bucket] || {})[id] || {}).label;
  return `
    <div class="review-buttons" data-bucket="${bucket}" data-id="${safeId}">
      ${labels.map(([key, label]) => `
        <button class="${current === key ? "selected" : ""}" data-label="${key}">${label}</button>
      `).join("")}
    </div>
  `;
}

function bindReviewButtons() {
  document.querySelectorAll(".review-buttons button").forEach((button) => {
    button.addEventListener("click", () => {
      const group = button.closest(".review-buttons");
      const bucket = group.dataset.bucket;
      const id = group.dataset.id;
      state.review[bucket] = state.review[bucket] || {};
      state.review[bucket][id] = {
        label: button.dataset.label,
        updated_at: new Date().toISOString()
      };
      markReviewChanged();
      renderAll();
    });
  });
}

function markReviewChanged() {
  reviewRevision += 1;
  state.reviewDirty = true;
  scheduleReviewSave();
}

function scheduleReviewSave() {
  clearTimeout(reviewSaveTimer);
  reviewSaveTimer = setTimeout(() => {
    reviewSaveTimer = null;
    saveReview();
  }, AUTO_SAVE_DELAY_MS);
}

async function flushReviewSave() {
  clearTimeout(reviewSaveTimer);
  reviewSaveTimer = null;
  while (reviewSaveInFlight && reviewSavePromise) {
    await reviewSavePromise;
    clearTimeout(reviewSaveTimer);
    reviewSaveTimer = null;
  }
  if (state.reviewDirty) await saveReview();
}

async function saveReview() {
  if (!state.projectDir || !state.review) return;
  if (reviewSaveInFlight) {
    reviewSaveQueued = true;
    if (reviewSavePromise) await reviewSavePromise;
    return;
  }
  reviewSaveInFlight = true;
  const projectDir = state.projectDir;
  const revision = reviewRevision;
  const review = cloneJson(state.review);
  reviewSavePromise = (async () => {
    try {
      const result = await window.marketViewer.writeReview({
        projectDir,
        review
      });
      if (normalizePath(projectDir) === normalizePath(state.projectDir) && revision === reviewRevision) {
        state.review = result.review;
        state.reviewDirty = false;
        renderReview();
      }
    } catch (error) {
      state.reviewDirty = true;
      console.error("Auto-save review failed:", error);
    } finally {
      reviewSaveInFlight = false;
      reviewSavePromise = null;
      if (reviewSaveQueued) {
        reviewSaveQueued = false;
        scheduleReviewSave();
      }
    }
  })();
  await reviewSavePromise;
}

function localAssetSrc(localPath) {
  if (!localPath || !state.projectDir) return "";
  if (/^https?:\/\//i.test(localPath)) return localPath;
  const normalized = String(localPath).replace(/\\/g, "/");
  const projectDir = state.projectDir.replace(/\\/g, "/");
  const researchRelative = /^(视频参考帧|参考图)\//.test(normalized)
    ? `00_调研/${normalized}`
    : normalized;
  const joined = normalized.includes(":") ? normalized : `${projectDir}/${researchRelative}`;
  const cleanPath = joined.replace(/\\/g, "/").replace(/^\/+/, "");
  return encodeURI(`file:///${cleanPath}`);
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function normalizePath(value) {
  return String(value || "").replace(/\\/g, "/").toLowerCase();
}

function image(src, alt) {
  if (!src) return `<div class="thumb empty-thumb"></div>`;
  return `<img class="thumb" src="${escapeAttr(src)}" alt="${escapeAttr(alt || "")}" loading="lazy" />`;
}

function chips(items) {
  const list = Array.isArray(items) ? items : items ? [items] : [];
  if (!list.length) return "";
  return `<div class="chips">${list.slice(0, 8).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>`;
}

function formatIncome(row) {
  const amount = incomeAmount(row);
  if (amount === null) return `<span class="muted">未公开</span>`;
  return `<span class="money">${escapeHtml(formatPlainNumber(amount))}</span>`;
}

function formatDownload(row) {
  const amount = downloadAmount(row);
  if (amount === null) return `<span class="muted">未公开</span>`;
  return escapeHtml(formatPlainNumber(amount));
}

function incomeAmount(row) {
  return firstMoneyNumber(
    row.material_income,
    row.income,
    row.revenue,
    row.sales_amount,
    row.sales_total,
    row.material_revenue,
    row.income_amount,
    row["素材收入"],
    row["收入"]
  );
}

function downloadAmount(row) {
  return firstNumber(
    row.download_count,
    row.downloads,
    row.download,
    row.download_count_total,
    row["下载"]
  );
}

function firstNumber(...values) {
  for (const value of values) {
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string") {
      const match = value.replace(/,/g, "").match(/\d+(?:\.\d+)?/);
      if (match) return Number(match[0]);
    }
  }
  return null;
}

function firstMoneyNumber(...values) {
  for (const value of values) {
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string") {
      const normalized = value.replace(/,/g, "").trim();
      if (/^\d+(?:\.\d+)?$/.test(normalized)) return Number(normalized);
      const match = normalized.match(/(?:￥|¥)\s*(\d+(?:\.\d+)?)\s*(万元|万|元)?|(\d+(?:\.\d+)?)\s*(万元|万|元)/);
      if (!match) continue;
      const amount = Number(match[1] || match[3]);
      if (!Number.isFinite(amount)) continue;
      const unit = match[2] || match[4] || "";
      return unit === "万" || unit === "万元" ? amount * 10000 : amount;
    }
  }
  return null;
}

function formatPlainNumber(value) {
  const rounded = Math.round(value * 100) / 100;
  return Number.isInteger(rounded) ? String(rounded) : String(rounded);
}

function empty(text) {
  return `<div class="empty">${escapeHtml(text)}</div>`;
}

function projectName(projectDir) {
  return String(projectDir || "").split(/[\\/]/).filter(Boolean).pop() || "未命名项目";
}

function shortLabel(value, limit) {
  const text = String(value || "");
  return text.length > limit ? `${text.slice(0, Math.max(0, limit - 3))}...` : text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#096;");
}
