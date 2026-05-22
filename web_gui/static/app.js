/* Vivian Web GUI — main application script.
 *
 * Responsibilities, top to bottom:
 *  - Activity bar / sidebar paging
 *  - File tree (lazy expansion)
 *  - Tabs + Monaco editor (one model per file)
 *  - AI panel streaming via SSE
 *  - Build / run / git output streaming via SSE
 *  - Web Serial flash + monitor (browser-only, no server involvement)
 *  - Plugin registry (window.vivian.registerPlugin)
 */
(() => {
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// ── State ─────────────────────────────────────────────────────────────
const state = {
  workspace: "",
  tabs: [],          // {path, model, dirty}
  activeTab: null,   // path
  monaco: null,
  editor: null,
  pendingSse: null,  // current EventSource
  pendingAbort: null,
  serial: { port: null, reader: null, writer: null, sse: null, mode: null },
  esp: { isEsp: false, compiler: null },
  plugins: [],       // {name, description, enabled, hooks}
  hooks: { onFileOpen: [], onFileSave: [] },
  // AI responding state
  thinkingStart: null,
  thinkingTimer: null,
  chatConfig: null,
  currentMode: "default",
};

const ESP_TARGETS = [
  "esp32", "esp32s2", "esp32s3", "esp32c2", "esp32c3", "esp32c5",
  "esp32c6", "esp32c61", "esp32h2", "esp32h21", "esp32p4",
];

const LANG_BY_EXT = {
  ".js": "javascript", ".mjs": "javascript", ".jsx": "javascript",
  ".ts": "typescript", ".tsx": "typescript",
  ".py": "python", ".rs": "rust", ".go": "go", ".java": "java",
  ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
  ".cs": "csharp", ".php": "php", ".rb": "ruby", ".swift": "swift", ".kt": "kotlin",
  ".html": "html", ".css": "css", ".scss": "scss", ".less": "less",
  ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "ini", ".ini": "ini",
  ".md": "markdown", ".sh": "shell", ".bash": "shell", ".zsh": "shell",
  ".sql": "sql", ".xml": "xml", ".dockerfile": "dockerfile",
};
function languageFor(path) {
  const ext = path.match(/\.[^.\\/]+$/)?.[0]?.toLowerCase() || "";
  return LANG_BY_EXT[ext] || "plaintext";
}

// ── Activity bar ──────────────────────────────────────────────────────
$$("#activity-bar .act").forEach(btn => {
  btn.addEventListener("click", () => switchPage(btn.dataset.page));
});
function switchPage(name) {
  $$("#activity-bar .act").forEach(b => b.classList.toggle("active", b.dataset.page === name));
  $$("#sidebar .page").forEach(p => p.classList.toggle("hidden", p.id !== `page-${name}`));
}
switchPage("explorer");

// ── File tree ─────────────────────────────────────────────────────────
async function loadTree(path = "") {
  const res = await fetch("/api/tree" + (path ? `?path=${encodeURIComponent(path)}` : ""));
  const data = await res.json();
  if (data.error) return null;
  state.workspace = data.path;
  $("#workspace-path").textContent = data.path;
  renderTree(data, $("#file-tree"), 0);
  refreshBranch();
  refreshScm();
  refreshBuildInfo();
  return data;
}
function renderTree(data, container, depth) {
  container.innerHTML = "";
  for (const entry of data.entries) {
    if (entry.hidden && depth === 0 && entry.name !== ".github") continue;
    const div = document.createElement("div");
    div.className = "entry " + (entry.is_dir ? "dir" : "file");
    div.style.paddingLeft = (12 + depth * 12) + "px";
    div.dataset.path = entry.path;
    const chev = entry.is_dir ? "▸" : "  ";
    div.innerHTML = `<span class="chev">${chev}</span><span class="name">${escapeHtml(entry.name)}</span>`;
    div.addEventListener("click", async () => {
      if (entry.is_dir) {
        // Lazy expand: replace inline
        if (div.dataset.expanded === "1") {
          // collapse: remove following children at higher depth
          let next = div.nextElementSibling;
          while (next && parseInt(next.style.paddingLeft) > parseInt(div.style.paddingLeft)) {
            const toRemove = next; next = next.nextElementSibling; toRemove.remove();
          }
          div.dataset.expanded = "0";
          div.querySelector(".chev").textContent = "▸";
          return;
        }
        const res = await fetch("/api/tree?path=" + encodeURIComponent(entry.path));
        const sub = await res.json();
        if (sub.error) return;
        let after = div;
        for (const e of sub.entries) {
          if (e.hidden) continue;
          const child = document.createElement("div");
          child.className = "entry " + (e.is_dir ? "dir" : "file");
          child.style.paddingLeft = (12 + (depth + 1) * 12) + "px";
          child.dataset.path = e.path;
          child.innerHTML = `<span class="chev">${e.is_dir ? "▸" : "  "}</span><span class="name">${escapeHtml(e.name)}</span>`;
          child.addEventListener("click", () => openFile(e.path));
          after.after(child); after = child;
        }
        div.dataset.expanded = "1";
        div.querySelector(".chev").textContent = "▾";
      } else {
        openFile(entry.path);
      }
    });
    container.appendChild(div);
  }
}
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

// ── Tabs + Monaco editor ──────────────────────────────────────────────
async function ensureMonaco() {
  if (state.monaco) return state.monaco;
  await window.__monacoReady;
  state.monaco = monaco;
  monaco.editor.defineTheme("vivian-dark", {
    base: "vs-dark", inherit: true, rules: [], colors: { "editor.background": "#1e1e1e" },
  });
  state.editor = monaco.editor.create($("#monaco-host"), {
    value: "", language: "plaintext", theme: "vivian-dark",
    automaticLayout: true, minimap: { enabled: $("#set-minimap").checked },
    wordWrap: $("#set-wordwrap").checked ? "on" : "off",
    fontSize: parseInt($("#set-font").value, 10) || 13,
  });
  state.editor.onDidChangeModelContent(() => {
    const tab = state.tabs.find(t => t.path === state.activeTab);
    if (tab && !tab.dirty) {
      tab.dirty = true;
      renderTabs();
    }
  });
  state.editor.onDidChangeCursorPosition(e => {
    $("#sb-cursor").textContent = `Ln ${e.position.lineNumber}, Col ${e.position.column}`;
  });
  return monaco;
}

async function openFile(path, gotoLine = 0) {
  await ensureMonaco();
  let tab = state.tabs.find(t => t.path === path);
  if (!tab) {
    const res = await fetch("/api/file?path=" + encodeURIComponent(path));
    const data = await res.json();
    if (data.error) { alert(`Cannot open: ${data.error}`); return; }
    const model = monaco.editor.createModel(data.content, languageFor(path), monaco.Uri.file(path));
    tab = { path, model, dirty: false };
    state.tabs.push(tab);
  }
  state.activeTab = path;
  _updateIncludeLabel();
  state.editor.setModel(tab.model);
  if (gotoLine > 0) {
    state.editor.revealLineInCenter(gotoLine);
    state.editor.setPosition({ lineNumber: gotoLine, column: 1 });
  }
  state.editor.focus();
  $("#welcome").classList.add("hidden");
  $("#monaco-host").style.display = "block";
  $("#sb-lang").textContent = languageFor(path);
  renderTabs();
  refreshBuildInfo();
  for (const cb of state.hooks.onFileOpen) try { cb(path); } catch (e) { console.warn(e); }
}

function renderTabs() {
  const bar = $("#tabbar");
  bar.innerHTML = "";
  for (const t of state.tabs) {
    const el = document.createElement("div");
    el.className = "tab" + (t.path === state.activeTab ? " active" : "") + (t.dirty ? " dirty" : "");
    el.innerHTML = `<span class="name">${escapeHtml(basename(t.path))}</span><span class="close">✕</span>`;
    el.title = t.path;
    el.addEventListener("click", e => {
      if (e.target.classList.contains("close")) { closeTab(t.path); return; }
      openFile(t.path);
    });
    bar.appendChild(el);
  }
  if (state.tabs.length === 0) {
    $("#welcome").classList.remove("hidden");
    $("#monaco-host").style.display = "none";
  }
}
function basename(p) { return p.split(/[\\/]/).pop(); }

function closeTab(path) {
  const tab = state.tabs.find(t => t.path === path);
  if (!tab) return;
  if (tab.dirty && !confirm(`${basename(path)} has unsaved changes. Close anyway?`)) return;
  tab.model.dispose();
  state.tabs = state.tabs.filter(t => t.path !== path);
  if (state.activeTab === path) {
    state.activeTab = state.tabs.length ? state.tabs[state.tabs.length - 1].path : null;
    _updateIncludeLabel();
    if (state.activeTab) state.editor.setModel(state.tabs.find(t => t.path === state.activeTab).model);
    else state.editor.setModel(monaco.editor.createModel("", "plaintext"));
  }
  renderTabs();
}

async function saveCurrent() {
  if (!state.activeTab) return;
  const tab = state.tabs.find(t => t.path === state.activeTab);
  const content = tab.model.getValue();
  const r = await fetch("/api/file", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: tab.path, content }),
  });
  const data = await r.json();
  if (data.error) { alert(`Save failed: ${data.error}`); return; }
  tab.dirty = false; renderTabs();
  for (const cb of state.hooks.onFileSave) try { cb(tab.path); } catch (e) { console.warn(e); }
}

window.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); saveCurrent(); }
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "f") {
    e.preventDefault(); switchPage("search"); $("#search-q").focus();
  }
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "a") {
    e.preventDefault();
    $("#ai-panel").classList.toggle("hidden");
  }
});

$("#welcome-new").addEventListener("click", e => {
  e.preventDefault();
  const path = prompt("New file path (absolute):");
  if (path) openFile(path);
});
$("#welcome-open").addEventListener("click", e => {
  e.preventDefault();
  const path = prompt("File path to open:");
  if (path) openFile(path);
});
$("#welcome-folder").addEventListener("click", e => {
  e.preventDefault();
  const path = prompt("Folder to use as workspace:", state.workspace);
  if (path) setWorkspace(path);
});
$("#btn-open-folder").addEventListener("click", () => {
  const path = prompt("Workspace folder:", state.workspace);
  if (path) setWorkspace(path);
});
async function setWorkspace(path) {
  const r = await fetch("/api/workspace", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  const data = await r.json();
  if (!data.ok) { alert(`Cannot set workspace: ${data.error || "?"}`); return; }
  await loadTree();
}

// ── AI panel ──────────────────────────────────────────────────────────
const transcript = $("#ai-transcript");
function modeOptions() {
  return (state.chatConfig && state.chatConfig.available_modes) || [];
}
function appendAi(html, cls = "") {
  const span = document.createElement("span");
  if (cls) span.className = cls;
  span.innerHTML = html;
  transcript.appendChild(span);
  transcript.scrollTop = transcript.scrollHeight;
}
function appendText(text, cls = "") {
  const node = document.createElement("span");
  if (cls) node.className = cls;
  node.textContent = text;
  transcript.appendChild(node);
  transcript.scrollTop = transcript.scrollHeight;
}

// ── AI chat ───────────────────────────────────────────────────────────
// Keep the "Include open file" label updated whenever the active tab changes
function _updateIncludeLabel() {
  const label = $("#ai-include-name");
  if (!label) return;
  if (state.activeTab) {
    const name = state.activeTab.split(/[\\/]/).pop();
    label.textContent = `Include: ${name}`;
    label.title = state.activeTab;
  } else {
    label.textContent = "Include open file";
    label.title = "";
    // Uncheck if no file is open
    const cb = $("#ai-include-file");
    if (cb) cb.checked = false;
  }
}

// Hook into active tab changes (called from openFile / closeTab / etc.)
const _origOpenFile = typeof openFile !== "undefined" ? openFile : null;

$("#ai-send").addEventListener("click", sendPrompt);
$("#ai-input").addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendPrompt(); }
});
$("#ai-stop").addEventListener("click", () => {
  fetch("/api/ai/interrupt", { method: "POST" });
  if (state.pendingAbort) { state.pendingAbort.abort(); state.pendingAbort = null; }
  if (state.pendingSse) { state.pendingSse.close(); state.pendingSse = null; }
  setResponding(false);
});

// ── AI stats ──────────────────────────────────────────────────────────
async function fetchStats() {
  try {
    const r = await fetch("/api/ai/stats");
    if (!r.ok) return;
    const d = await r.json();
    const fmt = n => n >= 1000 ? (n / 1000).toFixed(1) + "k" : String(n);
    const el = id => document.getElementById(id);
    if (el("sb-tokens-in"))  el("sb-tokens-in").textContent  = `↑ ${fmt(d.input_tokens)}`;
    if (el("sb-tokens-out")) el("sb-tokens-out").textContent = `↓ ${fmt(d.output_tokens)}`;
    if (el("sb-cost"))       el("sb-cost").textContent       = `$${d.cost_usd.toFixed(6)}`;
    if (el("sb-ctx"))        el("sb-ctx").textContent        = `ctx ${d.context_pct}%`;
    // Warn visually when context is getting full
    if (el("sb-ctx")) {
      el("sb-ctx").style.color = d.context_pct > 80 ? "#ff6b6b"
                                : d.context_pct > 60 ? "#ffd93d" : "";
    }
  } catch { /* network error — ignore */ }
}

// ── Responding state ─────────────────────────────────────────────────
function setResponding(on) {
  const sendBtn  = $("#ai-send");
  const thinking = $("#ai-thinking");
  if (sendBtn)  sendBtn.disabled = on;
  if (thinking) thinking.classList.toggle("hidden", !on);

  if (on) {
    state.thinkingStart = performance.now();
    // Live elapsed counter in status bar
    state.thinkingTimer = setInterval(() => {
      const el = document.getElementById("sb-resp-time");
      if (el && state.thinkingStart !== null) {
        const s = ((performance.now() - state.thinkingStart) / 1000).toFixed(1);
        el.textContent = `⏱ ${s}s`;
      }
    }, 100);
  } else {
    if (state.thinkingTimer) {
      clearInterval(state.thinkingTimer);
      state.thinkingTimer = null;
    }
    if (state.thinkingStart !== null) {
      const s = ((performance.now() - state.thinkingStart) / 1000).toFixed(1);
      const el = document.getElementById("sb-resp-time");
      if (el) el.textContent = `⏱ ${s}s`;
      state.thinkingStart = null;
    }
  }
}

function _handleAIEvent(data) {
  if (data.type === "chunk") appendText(data.text);
  else if (data.type === "tool_start") {
    appendText(`\n  ⚙ ${data.name}`, "tool");
  } else if (data.type === "tool_args") {
    // Show key arg inline after the tool name
    const args = data.args || {};
    const val = args.command || args.pattern || args.file_path || args.path
              || args.url || args.query || Object.values(args)[0] || "";
    const summary = val ? String(val).slice(0, 70) : "";
    appendText(summary ? `  ${summary}\n` : "\n", "tool");
  } else if (data.type === "tool") {
    // Legacy combined tool event (result only)
    if (!data._start_shown) appendText(`\n  ⚙ ${data.name}\n`, "tool");
    const r = data.result || {};
    if (r.error) appendText("  ✗ " + r.error + "\n", "err");
    if (r.stdout) appendText(r.stdout);
    if (r.stderr) appendText(r.stderr, "err");
    // Auto-open written/edited files in Monaco
    if (r.filePath && state.editor) {
      openFile(r.filePath);
    }
    // Compact result summary for non-Bash tools
    if (!r.error && !r.stdout && !r.stderr) {
      let summary = "";
      if (r.files)    summary = `${r.files.length} file(s)`;
      else if (r.numLines !== undefined) summary = `${r.numLines} lines`;
      else if (r.matches) summary = `${r.numMatches ?? r.matches.length} match(es)`;
      else if (r.filePath) summary = r.isNewFile ? `created ${r.filePath.split("/").pop()}` : `updated ${r.filePath.split("/").pop()}`;
      if (summary) appendText(`  ✔ ${summary}\n`, "tool");
    }
  } else if (data.type === "system") {
    appendText(`\n[${data.text}]\n`, "tool");
  } else if (data.type === "error") {
    appendText("\nError: " + data.error + "\n", "err");
    setResponding(false);
  } else if (data.type === "done") {
    appendText("\n");
    setResponding(false);
    fetchStats();
  }
}

async function sendPrompt() {
  const ta = $("#ai-input");
  const prompt = ta.value.trim();
  if (!prompt || state.pendingSse || state.pendingAbort) return;
  ta.value = "";
  setResponding(true);

  // Build file context if checkbox is checked and a file is open
  let fileContext = "";
  const includeCb = $("#ai-include-file");
  if (includeCb && includeCb.checked && state.activeTab) {
    const tab = state.tabs.find(t => t.path === state.activeTab);
    if (tab) {
      const ext = state.activeTab.split(".").pop() || "text";
      const name = state.activeTab.split(/[\\/]/).pop();
      fileContext = `\n\nOpen file — ${name}:\n\`\`\`${ext}\n${tab.model.getValue()}\n\`\`\``;
    }
  }

  appendText("\nYou: ", "you");
  const modeLabel = modeOptions().find(m => m.id === state.currentMode)?.label || state.currentMode;
  appendText(`[${modeLabel}] `, "tool");
  appendText(prompt + (fileContext ? `  [+ ${state.activeTab.split(/[\\/]/).pop()}]` : "") + "\n");
  appendText("\nVivian: ", "viv");

  if (fileContext) {
    // Use fetch() + streaming so we can POST the file content
    const ac = new AbortController();
    state.pendingAbort = ac;
    try {
      const resp = await fetch("/api/ai/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, file_context: fileContext, mode: state.currentMode }),
        signal: ac.signal,
      });
      if (!resp.ok) { setResponding(false); appendText(`\nError: HTTP ${resp.status}\n`, "err"); return; }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      outer: while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop();
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let data;
          try { data = JSON.parse(line.slice(6)); } catch { continue; }
          _handleAIEvent(data);
          if (data.type === "done") { break outer; }
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") appendText(`\nError: ${err.message}\n`, "err");
    } finally {
      setResponding(false);
      state.pendingAbort = null;
    }
  } else {
    // No file — use EventSource (GET) as before
    const src = new EventSource("/api/ai/stream?q=" + encodeURIComponent(prompt) + "&mode=" + encodeURIComponent(state.currentMode));
    state.pendingSse = src;
    src.onmessage = ev => {
      const data = JSON.parse(ev.data);
      _handleAIEvent(data);
      if (data.type === "done") { src.close(); state.pendingSse = null; }
    };
    src.onerror = () => { setResponding(false); src.close(); state.pendingSse = null; };
  }
}

async function loadChatConfig() {
  const resp = await fetch("/api/gui/config");
  if (!resp.ok) return;
  state.chatConfig = await resp.json();
  const modes = modeOptions();
  const select = $("#ai-mode");
  if (select) {
    select.innerHTML = "";
    for (const mode of modes) {
      const opt = document.createElement("option");
      opt.value = mode.id;
      opt.textContent = `${mode.label} · ${mode.description}`;
      select.appendChild(opt);
    }
    state.currentMode = state.chatConfig.default_mode || (modes[0] && modes[0].id) || "default";
    select.value = state.currentMode;
    select.onchange = () => { state.currentMode = select.value; };
  }

  const includeOpen = Boolean(state.chatConfig?.gui_settings?.include_open_file_by_default);
  if ($("#ai-include-file")) $("#ai-include-file").checked = includeOpen;

  if ($("#config-path")) $("#config-path").textContent = `Config file: ${state.chatConfig.config_path}`;
  if ($("#config-json")) $("#config-json").value = JSON.stringify(state.chatConfig, null, 2);
  if ($("#config-employee")) $("#config-employee").checked = Boolean(state.chatConfig.is_employee);
  if ($("#config-show-internal")) $("#config-show-internal").checked = Boolean(state.chatConfig?.user_settings?.show_internal_modes);
  if ($("#config-default-mode")) {
    const defaultMode = $("#config-default-mode");
    defaultMode.innerHTML = "";
    for (const mode of modes) {
      const opt = document.createElement("option");
      opt.value = mode.id;
      opt.textContent = mode.label;
      defaultMode.appendChild(opt);
    }
    defaultMode.value = state.chatConfig.default_mode || state.currentMode;
  }
}

function mergeConfigFormIntoJson() {
  let parsed = {};
  try {
    parsed = JSON.parse($("#config-json").value || "{}");
  } catch (err) {
    throw new Error(`Invalid JSON: ${err.message}`);
  }
  parsed.is_employee = $("#config-employee").checked;
  parsed.default_mode = $("#config-default-mode").value || parsed.default_mode || "default";
  parsed.user_settings = { ...(parsed.user_settings || {}), show_internal_modes: $("#config-show-internal").checked };
  return parsed;
}

async function saveChatConfig() {
  const status = $("#config-status");
  try {
    const config = mergeConfigFormIntoJson();
    const resp = await fetch("/api/gui/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    state.chatConfig = await resp.json();
    if (status) status.textContent = "Saved config.";
    await loadChatConfig();
  } catch (err) {
    if (status) status.textContent = err.message;
  }
}

$("#config-reload").addEventListener("click", () => loadChatConfig());
$("#config-save").addEventListener("click", () => saveChatConfig());
$("#config-employee").addEventListener("change", () => {
  const json = $("#config-json");
  if (json) json.value = JSON.stringify(mergeConfigFormIntoJson(), null, 2);
});
$("#config-show-internal").addEventListener("change", () => {
  const json = $("#config-json");
  if (json) json.value = JSON.stringify(mergeConfigFormIntoJson(), null, 2);
});
$("#config-default-mode").addEventListener("change", () => {
  const json = $("#config-json");
  if (json) json.value = JSON.stringify(mergeConfigFormIntoJson(), null, 2);
});

// ── Search ────────────────────────────────────────────────────────────
$("#search-go").addEventListener("click", runSearch);
$("#search-q").addEventListener("keydown", e => { if (e.key === "Enter") runSearch(); });
async function runSearch() {
  const q = $("#search-q").value.trim();
  if (!q) { $("#search-results").innerHTML = ""; $("#search-status").textContent = ""; return; }
  const params = new URLSearchParams({
    q, case: $("#search-case").checked ? "1" : "0",
    word: $("#search-word").checked ? "1" : "0",
    regex: $("#search-regex").checked ? "1" : "0",
    include: $("#search-include").value, exclude: $("#search-exclude").value,
  });
  const r = await fetch("/api/search?" + params);
  const data = await r.json();
  if (data.error) { $("#search-status").textContent = data.error; return; }
  const byFile = {};
  for (const h of data.hits) (byFile[h.path] ||= []).push(h);
  const container = $("#search-results"); container.innerHTML = "";
  for (const p of Object.keys(byFile).sort()) {
    const fileEl = document.createElement("div");
    fileEl.className = "entry dir";
    const rel = p.startsWith(state.workspace) ? p.slice(state.workspace.length + 1) : p;
    fileEl.innerHTML = `<span class="chev">▾</span><span class="name">${escapeHtml(rel)}  (${byFile[p].length})</span>`;
    container.appendChild(fileEl);
    for (const h of byFile[p]) {
      const hit = document.createElement("div");
      hit.className = "entry file"; hit.style.paddingLeft = "32px";
      hit.innerHTML = `<span class="chev">  </span><span class="name">${h.line}: ${escapeHtml(h.text)}</span>`;
      hit.addEventListener("click", () => openFile(p, h.line));
      container.appendChild(hit);
    }
  }
  $("#search-status").textContent = `${data.total} matches in ${Object.keys(byFile).length} files · ${data.engine}`;
}

// ── SCM ───────────────────────────────────────────────────────────────
async function refreshScm() {
  const r = await fetch("/api/git/status");
  const s = await r.json();
  const branchEl = $("#scm-branch");
  if (!s.is_repo) { branchEl.textContent = "(not a git repository)"; renderScmList("scm-staged", []); renderScmList("scm-changes", []); return; }
  let suffix = "";
  if (s.ahead || s.behind) suffix = `  ↑${s.ahead}  ↓${s.behind}`;
  branchEl.textContent = `⎇  ${s.branch || "(detached)"}${suffix}`;
  $("#sb-branch").textContent = `⎇ ${s.branch || "—"}`;
  $("#scm-staged-header").textContent = `STAGED CHANGES   (${s.staged.length})`;
  $("#scm-changes-header").textContent = `CHANGES   (${s.changes.length})`;
  renderScmList("scm-staged", s.staged, true);
  renderScmList("scm-changes", s.changes, false);
}
function renderScmList(id, entries, isStaged) {
  const c = $("#" + id); c.innerHTML = "";
  for (const e of entries) {
    const div = document.createElement("div");
    div.className = "entry file";
    div.innerHTML = `<span class="chev">${escapeHtml(e.x)}${escapeHtml(e.y)}</span><span class="name">${escapeHtml(e.path)}</span>`;
    div.addEventListener("click", () => openFile(state.workspace + "/" + e.path));
    div.addEventListener("dblclick", async () => {
      await fetch("/api/git/action", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: isStaged ? "unstage" : "stage", path: e.path }),
      });
      refreshScm();
    });
    c.appendChild(div);
  }
}
$("#scm-refresh").addEventListener("click", refreshScm);
$$("button[data-git]").forEach(b => b.addEventListener("click", () => {
  const cmd = { pull: "pull --ff-only", push: "push", fetch: "fetch --all --prune" }[b.dataset.git];
  if (cmd) streamSubprocess({ kind: "git", argv: cmd }, refreshScm);
}));
$("#scm-merge").addEventListener("click", () => {
  const branch = prompt("Branch to merge into current:"); if (!branch) return;
  streamSubprocess({ kind: "git", argv: `merge --no-edit ${branch}` }, refreshScm);
});
$("#scm-commit").addEventListener("click", () => doCommit(false));
$("#scm-commit-push").addEventListener("click", () => doCommit(true));
async function doCommit(thenPush) {
  const msg = $("#scm-msg").value.trim();
  if (!msg) { alert("Enter a commit message."); return; }
  const r = await fetch("/api/git/action", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "commit", message: msg }),
  });
  const data = await r.json();
  if (!data.ok) { alert(`Commit failed: ${data.error}`); return; }
  $("#scm-msg").value = ""; await refreshScm();
  if (thenPush) streamSubprocess({ kind: "git", argv: "push" }, refreshScm);
}
async function refreshBranch() {
  refreshScm(); // status fills branch label too
}

// ── Run panel ─────────────────────────────────────────────────────────
$$("input[name=run-mode]").forEach(rb => rb.addEventListener("change", refreshRunTarget));
$("#run-custom").addEventListener("input", refreshRunTarget);
$("#run-stop").addEventListener("click", () => state.pendingSse?.close());
$("#run-go").addEventListener("click", () => {
  const mode = $("input[name=run-mode]:checked").value;
  const args = $("#run-args").value.trim();
  if (mode === "custom") {
    const cmd = $("#run-custom").value.trim();
    if (!cmd) return;
    const full = args ? `${cmd} ${args}` : cmd;
    streamSubprocess({ kind: "run", argv: full });
    return;
  }
  if (!state.activeTab) return;
  if (mode === "script") {
    const argv = runnerForFile(state.activeTab);
    if (!argv) { alert("No runner for this file type."); return; }
    streamSubprocess({ kind: "run", argv: [...argv, ...(args ? args.split(/\s+/) : [])].join(" ") });
  } else if (mode === "binary") {
    const stem = state.activeTab.replace(/\.[^.\\/]+$/, "");
    streamSubprocess({ kind: "run", argv: [stem, ...(args ? args.split(/\s+/) : [])].join(" ") });
  }
});
function runnerForFile(path) {
  const ext = path.match(/\.[^.\\/]+$/)?.[0]?.toLowerCase() || "";
  const map = {
    ".py": ["python3", path], ".js": ["node", path], ".mjs": ["node", path],
    ".sh": ["bash", path], ".rb": ["ruby", path], ".php": ["php", path],
    ".lua": ["lua", path], ".ts": ["ts-node", path],
  };
  return map[ext];
}
function refreshRunTarget() {
  const mode = $("input[name=run-mode]:checked").value;
  $("#run-custom").disabled = mode !== "custom";
  const t = $("#run-target");
  if (mode === "custom") { t.textContent = "Will run: " + ($("#run-custom").value || "(empty)"); return; }
  if (!state.activeTab) { t.textContent = "Open a file to run it."; return; }
  if (mode === "script") {
    const r = runnerForFile(state.activeTab);
    t.textContent = r ? "Will run: " + r.join(" ") : "No runner for this file.";
  } else {
    t.textContent = "Will run: " + state.activeTab.replace(/\.[^.\\/]+$/, "");
  }
}

// ── Output dock (build/run/git streaming + monitor input) ─────────────
function ensureDock() { $("#output-dock").classList.remove("hidden"); }
$("#output-clear").addEventListener("click", () => { $("#output-body").textContent = ""; });
$("#output-close").addEventListener("click", () => $("#output-dock").classList.add("hidden"));
$("#output-stop").addEventListener("click", () => state.pendingSse?.close());
function appendOutput(text) {
  const body = $("#output-body");
  body.textContent += text;
  body.scrollTop = body.scrollHeight;
}
function streamSubprocess(params, onDone) {
  if (state.pendingSse) { state.pendingSse.close(); state.pendingSse = null; }
  ensureDock();
  $("#output-title").textContent = `OUTPUT — ${params.kind}`;
  const qs = new URLSearchParams(params);
  const src = new EventSource("/api/run/stream?" + qs);
  state.pendingSse = src;
  src.onmessage = ev => {
    const data = JSON.parse(ev.data);
    if (data.type === "started") appendOutput(`\n$ ${data.argv.join(" ")}\n  (in ${data.cwd})\n`);
    else if (data.type === "stdout") appendOutput(data.text);
    else if (data.type === "error") appendOutput(`\n[error] ${data.error}\n`);
    else if (data.type === "done") {
      appendOutput(`\n[exit ${data.code ?? "?"}]\n`);
      src.close(); state.pendingSse = null;
      if (onDone) onDone();
    }
  };
  src.onerror = () => { src.close(); state.pendingSse = null; };
}

// ── ESP-IDF status bar block + build/flash dispatch ───────────────────
const espSel = $("#esp-target");
for (const t of ESP_TARGETS) {
  const o = document.createElement("option"); o.value = t; o.textContent = t; espSel.appendChild(o);
}
espSel.value = "esp32s3";

async function refreshBuildInfo() {
  const file = state.activeTab || "";
  const r = await fetch(`/api/build/info?file=${encodeURIComponent(file)}`);
  const info = await r.json();
  state.esp.isEsp = info.is_esp;
  state.esp.compiler = info.compiler;
  $("#sb-esp").classList.toggle("hidden", !info.is_esp);
  $("#sb-compile").classList.toggle("hidden", info.is_esp || !info.compiler);
  if (info.compiler) $("#sb-compile-label").textContent = info.compiler;
}

$("#esp-build").addEventListener("click", () => streamSubprocess({
  kind: "build", target: espSel.value, file: state.activeTab || "",
}));
$("#sb-compile").addEventListener("click", () => streamSubprocess({
  kind: "build", file: state.activeTab || "",
}));
$("#esp-stop").addEventListener("click", () => state.pendingSse?.close());

const flashMenu = $("#esp-flash-menu");
$("#esp-flash").addEventListener("click", e => {
  e.stopPropagation();
  flashMenu.classList.toggle("hidden");
});
document.addEventListener("click", () => flashMenu.classList.add("hidden"));
flashMenu.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
  const method = b.dataset.method;
  if (method === "webserial") return flashWithWebSerial();
  streamSubprocess({ kind: "flash", target: espSel.value, method });
}));

// ── Web Serial monitor ────────────────────────────────────────────────
$("#esp-monitor").addEventListener("click", openSerialMonitor);

async function ensurePort() {
  if (state.serial.port) return state.serial.port;
  if (!("serial" in navigator)) {
    alert("Web Serial isn't available in this browser. Use Chrome or Edge over http://localhost.");
    return null;
  }
  try {
    state.serial.port = await navigator.serial.requestPort();
  } catch (e) {
    return null; // user cancelled
  }
  return state.serial.port;
}

async function openSerialMonitor() {
  // Prefer browser-native Web Serial — zero latency, no server in the path.
  if ("serial" in navigator) {
    return openSerialMonitorWebSerial();
  }
  // Firefox / Safari fallback: server-side pyserial bridge over SSE.
  return openSerialMonitorServer();
}

async function openSerialMonitorWebSerial() {
  const port = await ensurePort();
  if (!port) return;
  if (!port.readable) {
    const baud = parseInt(prompt("Baud rate?", "115200"), 10) || 115200;
    try { await port.open({ baudRate: baud }); }
    catch (e) { alert("Could not open port: " + e.message); return; }
  }
  ensureDock();
  $("#output-title").textContent = "WEB SERIAL MONITOR";
  $("#output-input-row").classList.remove("hidden");
  appendOutput("\n[connected via Web Serial — Ctrl+] disconnects]\n");

  state.serial.mode = "webserial";
  const decoder = new TextDecoder();
  state.serial.abort = new AbortController();
  const reader = port.readable.getReader();
  state.serial.reader = reader;
  state.serial.writer = port.writable.getWriter();
  (async () => {
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        appendOutput(decoder.decode(value));
      }
    } catch (e) {
      appendOutput("\n[reader error] " + e.message + "\n");
    } finally {
      try { reader.releaseLock(); } catch {}
    }
  })();
}

async function openSerialMonitorServer() {
  // Populate the picker and show the modal
  await refreshSerialPorts();
  $("#serial-error").textContent = "";
  $("#serial-modal").classList.remove("hidden");
}

async function refreshSerialPorts() {
  const sel = $("#serial-port");
  sel.innerHTML = "";
  let info;
  try {
    info = await (await fetch("/api/serial/ports")).json();
  } catch (e) {
    $("#serial-error").textContent = "Could not reach server: " + e.message;
    return;
  }
  if (info.pyserial_error) {
    $("#serial-error").textContent = info.pyserial_error;
    return;
  }
  if (!info.ports || info.ports.length === 0) {
    const opt = document.createElement("option");
    opt.textContent = "(no serial ports detected)"; opt.disabled = true; opt.selected = true;
    sel.appendChild(opt);
    return;
  }
  for (const p of info.ports) {
    const opt = document.createElement("option");
    opt.value = p.path;
    opt.textContent = `${p.path}  ·  ${p.description}${p.vid_pid ? "  [" + p.vid_pid + "]" : ""}`;
    sel.appendChild(opt);
  }
}

$("#serial-refresh").addEventListener("click", refreshSerialPorts);
$("#serial-cancel").addEventListener("click", () => $("#serial-modal").classList.add("hidden"));
$("#serial-open").addEventListener("click", async () => {
  const port = $("#serial-port").value;
  const baud = parseInt($("#serial-baud").value, 10) || 115200;
  if (!port) { $("#serial-error").textContent = "Pick a port first."; return; }
  const r = await fetch("/api/serial/open", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ port, baud }),
  });
  const data = await r.json();
  if (!data.ok) { $("#serial-error").textContent = data.error || "open failed"; return; }
  $("#serial-modal").classList.add("hidden");

  ensureDock();
  $("#output-title").textContent = `SERIAL MONITOR — ${port} @ ${baud}`;
  $("#output-input-row").classList.remove("hidden");
  appendOutput(`\n[connected via server bridge — Ctrl+] disconnects]\n`);

  state.serial.mode = "server";
  const src = new EventSource("/api/serial/stream");
  state.serial.sse = src;
  const decoder = new TextDecoder();
  src.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "data" && msg.b64) {
      const bin = atob(msg.b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      appendOutput(decoder.decode(bytes, { stream: true }));
    } else if (msg.type === "closed") {
      appendOutput("\n[bridge closed by server]\n");
      src.close(); state.serial.sse = null;
    }
  };
  src.onerror = () => {
    appendOutput("\n[bridge SSE error]\n");
    src.close(); state.serial.sse = null;
  };
});

async function closeSerial() {
  if (state.serial.mode === "webserial") {
    try { await state.serial.reader?.cancel(); } catch {}
    try { state.serial.writer?.releaseLock(); } catch {}
    try { await state.serial.port?.close(); } catch {}
  } else if (state.serial.mode === "server") {
    try { state.serial.sse?.close(); } catch {}
    try { await fetch("/api/serial/close", { method: "POST" }); } catch {}
  }
  state.serial = { port: null, reader: null, writer: null, sse: null, mode: null };
  $("#output-input-row").classList.add("hidden");
  appendOutput("\n[disconnected]\n");
}

$("#output-input").addEventListener("keydown", async e => {
  if (e.key === "]" && e.ctrlKey) { e.preventDefault(); await closeSerial(); return; }
  if (e.key !== "Enter") return;
  const text = e.target.value + "\n";
  e.target.value = "";
  if (state.serial.mode === "webserial" && state.serial.writer) {
    try { await state.serial.writer.write(new TextEncoder().encode(text)); }
    catch (err) { appendOutput("\n[write error] " + err.message + "\n"); }
  } else if (state.serial.mode === "server") {
    try {
      const r = await fetch("/api/serial/write", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: text }),
      });
      const d = await r.json();
      if (!d.ok) appendOutput("\n[write error] " + (d.error || "?") + "\n");
    } catch (err) { appendOutput("\n[write error] " + err.message + "\n"); }
  }
});

async function flashWithWebSerial() {
  alert(
    "Web Serial flashing isn't implemented in this MVP — that needs an ESP32 ROM bootloader\n" +
    "protocol implementation (esptool.js). For now the Monitor button uses Web Serial; flashing\n" +
    "still routes through idf.py on the server. Pick UART/JTAG/DFU in the menu."
  );
}

// ── Settings ──────────────────────────────────────────────────────────
$("#set-font").addEventListener("input", e => {
  if (state.editor) state.editor.updateOptions({ fontSize: parseInt(e.target.value, 10) || 13 });
});
$("#set-minimap").addEventListener("change", e => {
  if (state.editor) state.editor.updateOptions({ minimap: { enabled: e.target.checked } });
});
$("#set-wordwrap").addEventListener("change", e => {
  if (state.editor) state.editor.updateOptions({ wordWrap: e.target.checked ? "on" : "off" });
});

// ── Plugins (browser-side) ────────────────────────────────────────────
window.vivian = {
  registerPlugin(spec) {
    // spec: { name, description, onActivate(api), onFileOpen(path), onFileSave(path) }
    const entry = { ...spec, enabled: true };
    state.plugins.push(entry);
    if (spec.onActivate) try { spec.onActivate(pluginApi(entry)); } catch (e) { console.warn(e); }
    if (spec.onFileOpen) state.hooks.onFileOpen.push(spec.onFileOpen);
    if (spec.onFileSave) state.hooks.onFileSave.push(spec.onFileSave);
    renderPlugins();
  },
};
function pluginApi(entry) {
  return {
    showMessage: (msg) => alert(msg),
    currentFile: () => state.activeTab,
    workspace:   () => state.workspace,
    openFile,
    appendOutput,
  };
}
function renderPlugins() {
  const ul = $("#plugin-list"); ul.innerHTML = "";
  for (const p of state.plugins) {
    const li = document.createElement("li");
    li.textContent = `${p.name}${p.description ? "  ·  " + p.description : ""}`;
    ul.appendChild(li);
  }
  if (state.plugins.length === 0) {
    const li = document.createElement("li");
    li.style.color = "var(--fg-dim)";
    li.textContent = "No plugins loaded. Call vivian.registerPlugin({...}) from a <script> or the console.";
    ul.appendChild(li);
  }
}
$("#reload-plugins").addEventListener("click", () => location.reload());
renderPlugins();

// Drop a hello-world plugin so the panel isn't empty by default.
window.vivian.registerPlugin({
  name: "hello",
  description: "Logs file opens to the console.",
  onFileOpen: (p) => console.log("[hello plugin] opened:", p),
});

// ── Boot ──────────────────────────────────────────────────────────────
ensureMonaco().then(() => loadChatConfig().then(() => loadTree().then(() => {
  refreshRunTarget();
  fetchStats();
  setInterval(fetchStats, 10000); // refresh stats every 10s
})));
})();
