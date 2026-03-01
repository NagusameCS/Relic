"""
Relic dark theme — pure black background with monochrome white accents
and red highlights for warnings / critical findings.
"""

RELIC_CSS = """\
/* ══════════════════════════════════════════════════════════════════
   RELIC DARK THEME — #000000 base, white foreground, red accents
   ══════════════════════════════════════════════════════════════════ */

Screen {
    background: #000000;
    color: #e0e0e0;
}

/* ── Header / Footer ─────────────────────────────────────────── */

Header {
    background: #0a0a0a;
    color: #ffffff;
    dock: top;
    height: 3;
    content-align: center middle;
    text-style: bold;
    border-bottom: solid #1a1a1a;
}

Footer {
    background: #0a0a0a;
    color: #888888;
    dock: bottom;
    height: 1;
}

/* ── Panels ──────────────────────────────────────────────────── */

.panel {
    background: #050505;
    border: solid #1a1a1a;
    padding: 1;
    margin: 0 1;
}

.panel-title {
    color: #ffffff;
    text-style: bold;
    background: #111111;
    padding: 0 2;
}

/* ── Output log ──────────────────────────────────────────────── */

#output-log {
    background: #000000;
    color: #cccccc;
    border: solid #1a1a1a;
    height: 1fr;
    overflow-y: auto;
    padding: 1;
}

.log-info {
    color: #888888;
}

.log-command {
    color: #ffffff;
    text-style: bold;
}

.log-command-llm {
    color: #00ff88;
    text-style: bold;
}

.log-output {
    color: #aaaaaa;
}

.log-error {
    color: #ff4444;
    text-style: bold;
}

.log-warning {
    color: #ffaa00;
}

.log-finding {
    color: #ff2222;
    text-style: bold;
}

.log-success {
    color: #00ff88;
}

/* ── Input bar ───────────────────────────────────────────────── */

#input-bar {
    dock: bottom;
    height: 3;
    background: #0a0a0a;
    border-top: solid #1a1a1a;
    padding: 0 1;
}

#prompt-input {
    background: #111111;
    color: #ffffff;
    border: solid #222222;
    padding: 0 1;
    width: 1fr;
}

#prompt-input:focus {
    border: solid #444444;
}

/* ── Sidebar ─────────────────────────────────────────────────── */

#sidebar {
    width: 32;
    background: #050505;
    border-right: solid #1a1a1a;
    dock: left;
    padding: 1;
}

.sidebar-section {
    margin-bottom: 1;
}

.sidebar-label {
    color: #666666;
    text-style: bold;
}

.sidebar-item {
    color: #cccccc;
    padding: 0 1;
}

.sidebar-item:hover {
    background: #1a1a1a;
    color: #ffffff;
}

/* ── Status indicators ───────────────────────────────────────── */

.status-connected {
    color: #00ff88;
}

.status-disconnected {
    color: #ff4444;
}

.status-working {
    color: #ffaa00;
}

/* ── Disclaimer banner ───────────────────────────────────────── */

#disclaimer {
    background: #0a0000;
    color: #ff4444;
    border: solid #330000;
    padding: 1 2;
    margin: 1;
    text-align: center;
    text-style: bold;
}

/* ── Buttons ─────────────────────────────────────────────────── */

Button {
    background: #1a1a1a;
    color: #ffffff;
    border: solid #333333;
    margin: 0 1;
    min-width: 12;
}

Button:hover {
    background: #222222;
    border: solid #444444;
}

Button:focus {
    border: solid #555555;
}

Button.btn-danger {
    background: #220000;
    color: #ff4444;
    border: solid #440000;
}

Button.btn-danger:hover {
    background: #330000;
}

Button.btn-primary {
    background: #001a00;
    color: #00ff88;
    border: solid #003300;
}

Button.btn-primary:hover {
    background: #002200;
}

/* ── Modal / Dialogs ─────────────────────────────────────────── */

.modal-overlay {
    background: rgba(0, 0, 0, 0.85);
}

.modal-dialog {
    background: #0a0a0a;
    border: solid #222222;
    padding: 2;
    width: 70;
    max-height: 30;
}

/* ── Tables ──────────────────────────────────────────────────── */

DataTable {
    background: #000000;
    color: #cccccc;
}

DataTable > .datatable--header {
    background: #111111;
    color: #ffffff;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #1a1a1a;
    color: #ffffff;
}

/* ── Progress ────────────────────────────────────────────────── */

ProgressBar {
    background: #111111;
    color: #00ff88;
}

/* ── Scrollbars ──────────────────────────────────────────────── */

ScrollBar {
    background: #0a0a0a;
    color: #333333;
}

ScrollBar:hover {
    color: #555555;
}
"""
