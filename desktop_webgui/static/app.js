/**
 * Vivian Desktop — Cyberpunk Windows 7 Desktop Shell
 * Handles: movable icons, drag-select, taskbar clock, start menu, context menu,
 *          icon double-click actions (calls back to Python server via /api/launch).
 */

"use strict";

// ── Icon Definitions ──────────────────────────────────────────────────────────
const ICONS = [
  { label: "Vivian AI",       emoji: "🤖", color: "var(--cyan)",   action: "chat"     },
  { label: "Skills",          emoji: "✦",  color: "var(--purple)", action: "skills"   },
  { label: "Terminal",        emoji: "💻", color: "var(--green)",  action: "terminal" },
  { label: "File System",     emoji: "📁", color: "var(--yellow)", action: "files"    },
  { label: "IDE / Editor",    emoji: "🖥️",  color: "var(--cyan)",   action: "ide"      },
  { label: "Web Browser",     emoji: "🌐", color: "var(--pink)",   action: "browser"  },
  { label: "Code Editor",     emoji: "📝", color: "var(--yellow)", action: "editor"   },
  { label: "Network",         emoji: "🌐", color: "var(--pink)",   action: "network"  },
  { label: "Settings",        emoji: "⚙️",  color: "var(--purple)", action: "settings" },
  { label: "Security",        emoji: "🛡️",  color: "var(--cyan)",   action: "security" },
  { label: "Task Monitor",    emoji: "📊", color: "var(--pink)",   action: "monitor"  },
];

const ICON_W    = 90;   // px — must match --icon-w + padding
const ICON_H    = 106;  // px — box + label
const COL_X     = 18;
const ROW_START = 18;
const ROW_STEP  = ICON_H + 12;

// ── State ─────────────────────────────────────────────────────────────────────
let dragging     = null;  // { el, offX, offY }
let rubberBand   = null;  // { startX, startY }
let selectedIcons = new Set();
let _ideUrl = "";         // filled from /api/health

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Fetch health first so we know the ide_url before rendering icons
  fetch("/api/health")
    .then(r => r.json())
    .then(data => { _ideUrl = data.ide_url || ""; })
    .catch(() => {})
    .finally(() => {
      buildIcons();
    });
  startClock();
  hookTaskbar();
  hookContextMenu();
  hookDesktopDrag();
});

// ── Build Icons ───────────────────────────────────────────────────────────────
function buildIcons() {
  const layer = document.getElementById("icon-layer");
  ICONS.forEach((data, i) => {
    const el = createIcon(data);
    el.style.left = COL_X + "px";
    el.style.top  = (ROW_START + i * ROW_STEP) + "px";
    layer.appendChild(el);
  });
}

function createIcon(data) {
  const el = document.createElement("div");
  el.className = "desktop-icon";
  el.dataset.action = data.action;
  el.style.setProperty("--icon-color", data.color);

  const box = document.createElement("div");
  box.className = "icon-box";
  box.style.setProperty("--icon-color", data.color);
  box.textContent = data.emoji;

  const lbl = document.createElement("div");
  lbl.className = "icon-label";
  lbl.textContent = data.label;

  el.appendChild(box);
  el.appendChild(lbl);

  // Drag
  el.addEventListener("mousedown", onIconMouseDown);
  // Double-click to activate
  el.addEventListener("dblclick", () => activateIcon(data.action));
  // Single click to select
  el.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!e.ctrlKey) clearSelection();
    toggleSelect(el);
  });

  return el;
}

// ── Icon Drag ─────────────────────────────────────────────────────────────────
function onIconMouseDown(e) {
  if (e.button !== 0) return;
  e.stopPropagation();

  const el = e.currentTarget;
  const rect = el.getBoundingClientRect();
  dragging = { el, offX: e.clientX - rect.left, offY: e.clientY - rect.top };

  el.style.zIndex = 100;
  document.addEventListener("mousemove", onDragMove);
  document.addEventListener("mouseup",   onDragUp, { once: true });
}

function onDragMove(e) {
  if (!dragging) return;
  const { el, offX, offY } = dragging;
  const desktop = document.getElementById("desktop");
  const dRect   = desktop.getBoundingClientRect();
  const maxX = dRect.width  - ICON_W  - 4;
  const maxY = dRect.height - ICON_H  - 4;

  let x = e.clientX - dRect.left - offX;
  let y = e.clientY - dRect.top  - offY;
  x = Math.max(0, Math.min(x, maxX));
  y = Math.max(0, Math.min(y, maxY));

  el.style.left = x + "px";
  el.style.top  = y + "px";
}

function onDragUp() {
  if (dragging) {
    dragging.el.style.zIndex = "";
    dragging = null;
  }
  document.removeEventListener("mousemove", onDragMove);
}

// ── Selection ─────────────────────────────────────────────────────────────────
function toggleSelect(el) {
  if (selectedIcons.has(el)) {
    el.classList.remove("selected");
    selectedIcons.delete(el);
  } else {
    el.classList.add("selected");
    selectedIcons.add(el);
  }
}

function clearSelection() {
  selectedIcons.forEach(el => el.classList.remove("selected"));
  selectedIcons.clear();
}

// ── Rubber-band Select ────────────────────────────────────────────────────────
function hookDesktopDrag() {
  const desktop = document.getElementById("desktop");
  const selBox  = document.getElementById("selection-box");

  desktop.addEventListener("mousedown", (e) => {
    if (e.button !== 0 || e.target !== desktop && e.target !== document.getElementById("icon-layer")) return;
    clearSelection();
    const dRect = desktop.getBoundingClientRect();
    rubberBand = { startX: e.clientX - dRect.left, startY: e.clientY - dRect.top };
    selBox.style.display = "block";
    selBox.style.left   = rubberBand.startX + "px";
    selBox.style.top    = rubberBand.startY + "px";
    selBox.style.width  = "0px";
    selBox.style.height = "0px";

    document.addEventListener("mousemove", onRubberMove);
    document.addEventListener("mouseup",   onRubberUp, { once: true });
  });

  function onRubberMove(e) {
    if (!rubberBand) return;
    const dRect = desktop.getBoundingClientRect();
    const cx = e.clientX - dRect.left;
    const cy = e.clientY - dRect.top;
    const x  = Math.min(cx, rubberBand.startX);
    const y  = Math.min(cy, rubberBand.startY);
    const w  = Math.abs(cx - rubberBand.startX);
    const h  = Math.abs(cy - rubberBand.startY);
    selBox.style.left   = x + "px";
    selBox.style.top    = y + "px";
    selBox.style.width  = w + "px";
    selBox.style.height = h + "px";

    // Select icons that intersect the band
    clearSelection();
    const band = selBox.getBoundingClientRect();
    document.querySelectorAll(".desktop-icon").forEach(icon => {
      const r = icon.getBoundingClientRect();
      if (r.left < band.right && r.right > band.left &&
          r.top  < band.bottom && r.bottom > band.top) {
        icon.classList.add("selected");
        selectedIcons.add(icon);
      }
    });
  }

  function onRubberUp() {
    rubberBand = null;
    selBox.style.display = "none";
    document.removeEventListener("mousemove", onRubberMove);
  }
}

// ── Activate Icon (double-click) ──────────────────────────────────────────────
function activateIcon(action) {
  // IDE icon — open the companion web_gui in a new tab
  if (action === "ide") {
    const url = _ideUrl || "http://127.0.0.1:7878/";
    window.open(url, "_blank");
    return;
  }
  // Browser icon — open a new blank browser tab
  if (action === "browser") {
    window.open("about:blank", "_blank");
    return;
  }
  // Chat — open the desktop chat app in a window overlay
  if (action === "chat") {
    openWindow("Vivian AI", "/apps/chat.html", 700, 520);
    return;
  }
  // Skills Manager
  if (action === "skills") {
    openWindow("Skills Manager", "/apps/skills.html", 720, 560);
    return;
  }
  // All other actions call the Python backend
  fetch("/api/launch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  }).catch(() => {});
}

// ── Window Manager ────────────────────────────────────────────────────────────
let _winZ = 100;

function openWindow(title, src, w = 680, h = 500) {
  const desktop = document.getElementById("desktop");

  const win = document.createElement("div");
  win.className = "desk-window";
  win.style.width  = w + "px";
  win.style.height = h + "px";
  // Offset each new window slightly
  const offset = (_winZ - 100) * 22;
  win.style.left = (Math.min(80 + offset, window.innerWidth  - w - 20)) + "px";
  win.style.top  = (Math.min(60 + offset, window.innerHeight - h - 50)) + "px";
  win.style.zIndex = ++_winZ;

  // Title bar
  const bar = document.createElement("div");
  bar.className = "desk-window-bar";

  const titleSpan = document.createElement("span");
  titleSpan.className = "desk-window-title";
  titleSpan.textContent = title;

  const btns = document.createElement("div");
  btns.className = "desk-window-btns";

  const minBtn = document.createElement("button");
  minBtn.className = "wbtn minimize";
  minBtn.title = "Minimize";
  minBtn.textContent = "─";
  minBtn.addEventListener("click", () => win.classList.toggle("minimized"));

  const maxBtn = document.createElement("button");
  maxBtn.className = "wbtn maximize";
  maxBtn.title = "Maximize";
  maxBtn.textContent = "□";
  maxBtn.addEventListener("click", () => win.classList.toggle("maximized"));

  const closeBtn = document.createElement("button");
  closeBtn.className = "wbtn close";
  closeBtn.title = "Close";
  closeBtn.textContent = "✕";
  closeBtn.addEventListener("click", () => win.remove());

  btns.append(minBtn, maxBtn, closeBtn);
  bar.append(titleSpan, btns);

  // iframe body
  const body = document.createElement("div");
  body.className = "desk-window-body";
  const iframe = document.createElement("iframe");
  iframe.src = src;
  iframe.allowFullscreen = true;
  body.appendChild(iframe);

  win.append(bar, body);
  desktop.appendChild(win);

  // Bring to front on click
  win.addEventListener("mousedown", () => { win.style.zIndex = ++_winZ; });

  // Drag via title bar
  _makeWindowDraggable(win, bar);

  return win;
}

function _makeWindowDraggable(win, handle) {
  let ox = 0, oy = 0;

  handle.addEventListener("mousedown", (e) => {
    if (e.target.classList.contains("wbtn")) return;
    e.preventDefault();
    ox = e.clientX - win.offsetLeft;
    oy = e.clientY - win.offsetTop;
    win.style.zIndex = ++_winZ;

    function onMove(ev) {
      let nx = ev.clientX - ox;
      let ny = ev.clientY - oy;
      nx = Math.max(0, Math.min(nx, window.innerWidth  - win.offsetWidth));
      ny = Math.max(0, Math.min(ny, window.innerHeight - win.offsetHeight - 38)); // taskbar
      win.style.left = nx + "px";
      win.style.top  = ny + "px";
    }
    function onUp() {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup",   onUp);
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup",   onUp);
  });
}

// ── Taskbar ───────────────────────────────────────────────────────────────────
function hookTaskbar() {
  const btn  = document.getElementById("start-btn");
  const menu = document.getElementById("start-menu");

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = !menu.classList.contains("hidden");
    menu.classList.toggle("hidden", open);
    btn.classList.toggle("active", !open);
  });

  // Close on outside click
  document.addEventListener("click", (e) => {
    if (!menu.contains(e.target) && e.target !== btn) {
      menu.classList.add("hidden");
      btn.classList.remove("active");
    }
  });

  // Start menu items
  document.querySelectorAll("#start-menu-list li[data-action]").forEach(li => {
    li.addEventListener("click", () => {
      menu.classList.add("hidden");
      btn.classList.remove("active");
      activateIcon(li.dataset.action);
    });
  });
}

// ── Clock ─────────────────────────────────────────────────────────────────────
function startClock() {
  const el = document.getElementById("clock");
  function tick() {
    const now = new Date();
    const hh  = String(now.getHours()).padStart(2, "0");
    const mm  = String(now.getMinutes()).padStart(2, "0");
    const ss  = String(now.getSeconds()).padStart(2, "0");
    const days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
    const mons = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    el.textContent = `${hh}:${mm}:${ss}  ${days[now.getDay()]} ${mons[now.getMonth()]} ${now.getDate()}`;
  }
  tick();
  setInterval(tick, 1000);
}

// ── Context Menu ──────────────────────────────────────────────────────────────
function hookContextMenu() {
  const menu = document.getElementById("ctx-menu");

  document.getElementById("desktop").addEventListener("contextmenu", (e) => {
    e.preventDefault();
    closeContextMenu();
    menu.style.left = Math.min(e.clientX, window.innerWidth  - 200) + "px";
    menu.style.top  = Math.min(e.clientY, window.innerHeight - 200) + "px";
    menu.classList.remove("hidden");
  });

  menu.querySelectorAll("li[data-cmd]").forEach(li => {
    li.addEventListener("click", () => {
      handleContextCmd(li.dataset.cmd);
      closeContextMenu();
    });
  });

  document.addEventListener("click",       closeContextMenu);
  document.addEventListener("contextmenu", (e) => { if (e.target.closest("#ctx-menu")) return; }, true);
}

function closeContextMenu() {
  document.getElementById("ctx-menu").classList.add("hidden");
}

function handleContextCmd(cmd) {
  if (cmd === "refresh") location.reload();
  // Other commands can hook into the Python backend via /api/launch
  else activateIcon(cmd);
}
