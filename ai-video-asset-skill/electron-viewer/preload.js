const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("marketViewer", {
  listProjects: () => ipcRenderer.invoke("project:list"),
  selectProject: () => ipcRenderer.invoke("project:select"),
  readProject: (projectDir) => ipcRenderer.invoke("project:read", projectDir),
  writeReview: (payload) => ipcRenderer.invoke("review:write", payload),
  buildSelectedReferenceFrames: (payload) => ipcRenderer.invoke("reference-frames:build-selected", payload),
  watchProject: (projectDir) => ipcRenderer.invoke("project:watch", projectDir),
  unwatchProject: () => ipcRenderer.invoke("project:unwatch"),
  onProjectsChanged: (callback) => {
    if (typeof callback !== "function") return () => {};
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("projects:changed", listener);
    return () => ipcRenderer.removeListener("projects:changed", listener);
  },
  onProjectChanged: (callback) => {
    if (typeof callback !== "function") return () => {};
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("project:changed", listener);
    return () => ipcRenderer.removeListener("project:changed", listener);
  }
});
