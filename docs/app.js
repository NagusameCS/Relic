/* ══════════════════════════════════════════════════════════════════
   Relic Web UI — Main Application Logic
   ══════════════════════════════════════════════════════════════════ */
"use strict";

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

// ── State ────────────────────────────────────────────────────────

const state = {
    apiUrl: "http://127.0.0.1:8746",
    connected: false,
    ws: null,
    findings: [],
    modules: {},
    history: [],
    historyIdx: -1,
};

// ── DOM refs ─────────────────────────────────────────────────────

const dom = {
    apiUrl:      () => $("#api-url"),
    btnConnect:  () => $("#btn-connect"),
    btnSend:     () => $("#btn-send"),
    btnStop:     () => $("#btn-stop"),
    status:      () => $("#status-indicator"),
    modelLabel:  () => $("#model-label"),
    outputLog:   () => $("#output-log"),
    promptInput: () => $("#prompt-input"),
    scopeList:   () => $("#scope-list"),
    moduleTree:  () => $("#module-tree"),
    moduleCount: () => $("#module-count"),
    moduleGrid:  () => $("#module-grid"),
    moduleSearch:() => $("#module-search"),
    sessionList: () => $("#session-list"),
    findingsBody:() => $("#findings-body"),
    noFindings:  () => $("#no-findings"),
    findingsTable:() => $("#findings-table"),
    countCritical: () => $("#count-critical"),
    countHigh:   () => $("#count-high"),
    countMedium: () => $("#count-medium"),
    countLow:    () => $("#count-low"),
    countInfo:   () => $("#count-info"),
};

// ── Utilities ────────────────────────────────────────────────────

function ts() {
    return new Date().toLocaleTimeString("en-US", { hour12: false });
}

function esc(text) {
    const d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
}

function appendLog(html, cls = "") {
    const log = dom.outputLog();
    const line = document.createElement("div");
    line.className = `log-line ${cls}`.trim();
    line.innerHTML = `<span class="timestamp">${ts()}</span>${html}`;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
}

function setStatus(s) {
    const el = dom.status();
    el.className = `status ${s}`;
    el.textContent = s === "connected" ? "● Connected"
                   : s === "working"   ? "● Working…"
                   : "● Disconnected";
}

// ── API helpers ──────────────────────────────────────────────────

async function api(path, opts = {}) {
    const url = `${state.apiUrl}${path}`;
    const res = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...opts,
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
}

async function apiGet(path)  { return api(path); }
async function apiPost(path, body) {
    return api(path, { method: "POST", body: JSON.stringify(body) });
}

// ── Connection ───────────────────────────────────────────────────

async function connect() {
    state.apiUrl = dom.apiUrl().value.replace(/\/+$/, "");
    appendLog("Connecting to <b>" + esc(state.apiUrl) + "</b>…", "log-info");

    try {
        const status = await apiGet("/api/status");
        state.connected = true;
        setStatus("connected");
        dom.modelLabel().textContent = status.model || "—";
        dom.moduleCount().textContent = status.modules;
        appendLog(`Connected — model: <b>${esc(status.model)}</b>, modules: ${status.modules}`, "log-success");

        // Fetch scope, modules, sessions in parallel
        const [scope, modules, sessions] = await Promise.all([
            apiGet("/api/scope"),
            apiGet("/api/modules"),
            apiGet("/api/sessions"),
        ]);

        renderScope(scope);
        renderModules(modules);
        renderSessions(sessions);
        connectWebSocket();

    } catch (e) {
        state.connected = false;
        setStatus("disconnected");
        appendLog(`Connection failed: ${esc(e.message)}`, "log-error");
    }
}

function connectWebSocket() {
    const wsUrl = state.apiUrl.replace(/^http/, "ws") + "/ws";
    if (state.ws) { try { state.ws.close(); } catch(_){} }
    const ws = new WebSocket(wsUrl);
    state.ws = ws;

    ws.onopen = () => appendLog("WebSocket connected", "log-info");
    ws.onclose = () => {
        appendLog("WebSocket disconnected", "log-warning");
        state.ws = null;
    };
    ws.onerror = () => {};
    ws.onmessage = (ev) => {
        try { handleWsEvent(JSON.parse(ev.data)); } catch(_) {}
    };
}

// ── WebSocket event handler ──────────────────────────────────────

function handleWsEvent(ev) {
    switch (ev.type) {
        case "LogEvent":
            appendLog(esc(ev.message), `log-${ev.level || "info"}`);
            break;
        case "CommandEvent":
            appendLog(`$ ${esc(ev.command)}`, ev.source === "llm" ? "log-llm" : "log-command");
            break;
        case "OutputEvent":
            appendLog(esc(ev.text), `log-output`);
            break;
        case "PlanEvent":
            if (ev.tasks && ev.tasks.length) {
                appendLog(`Plan:\n${ev.tasks.map((t,i) => `  ${i+1}. ${esc(t)}`).join("\n")}`, "log-plan");
            }
            break;
        case "FindingEvent":
            if (ev.finding) addFinding(ev.finding);
            break;
    }
}

// ── Send objective / command ─────────────────────────────────────

async function send() {
    const input = dom.promptInput();
    const text = input.value.trim();
    if (!text) return;

    // Save history
    state.history.push(text);
    state.historyIdx = state.history.length;
    input.value = "";

    if (!state.connected) {
        appendLog("Not connected. Click <b>Connect</b> first.", "log-error");
        return;
    }

    if (text.startsWith("/cmd ")) {
        const cmd = text.slice(5);
        appendLog(`$ ${esc(cmd)}`, "log-command");
        setStatus("working");
        try {
            const res = await apiPost("/api/command", { command: cmd });
            appendLog(esc(res.output || "(no output)"), "log-output");
        } catch (e) {
            appendLog(`Error: ${esc(e.message)}`, "log-error");
        }
        setStatus("connected");
    } else {
        appendLog(`Objective: ${esc(text)}`, "log-command");
        setStatus("working");
        try {
            await apiPost("/api/objective", { objective: text });
            appendLog("Objective submitted — streaming output below…", "log-info");
        } catch (e) {
            appendLog(`Error: ${esc(e.message)}`, "log-error");
            setStatus("connected");
        }
    }
}

async function stop() {
    if (!state.connected) return;
    try {
        await apiPost("/api/stop", {});
        appendLog("Stop signal sent", "log-warning");
        setStatus("connected");
    } catch (e) {
        appendLog(`Error: ${esc(e.message)}`, "log-error");
    }
}

// ── Render helpers ───────────────────────────────────────────────

function renderScope(scope) {
    const el = dom.scopeList();
    if (!scope.authorized_targets || scope.authorized_targets.length === 0) {
        el.innerHTML = "<em>No scope defined</em>";
        return;
    }
    el.innerHTML = scope.authorized_targets
        .map(t => `<div class="scope-item">${esc(t)}</div>`)
        .join("");
}

function renderModules(modules) {
    state.modules = modules;

    // Sidebar tree
    const tree = dom.moduleTree();
    let html = "";
    for (const [cat, mods] of Object.entries(modules)) {
        html += `<div class="mod-category" onclick="this.classList.toggle('open')">${esc(cat)} (${mods.length})</div>`;
        html += `<div class="mod-list">`;
        for (const m of mods) {
            html += `<div class="mod-item" title="${esc(m.description)}">${esc(m.name)}</div>`;
        }
        html += `</div>`;
    }
    tree.innerHTML = html;

    // Module grid
    renderModuleGrid(modules);
}

function renderModuleGrid(modules, filter = "") {
    const grid = dom.moduleGrid();
    let html = "";
    const lf = filter.toLowerCase();
    for (const [cat, mods] of Object.entries(modules)) {
        for (const m of mods) {
            if (lf && !m.name.toLowerCase().includes(lf) && !m.description.toLowerCase().includes(lf) && !cat.toLowerCase().includes(lf)) {
                continue;
            }
            html += `
                <div class="module-card">
                    <div class="module-card-name">${esc(m.name)}</div>
                    <div class="module-card-cat">${esc(cat)}</div>
                    <div class="module-card-desc">${esc(m.description)}</div>
                </div>`;
        }
    }
    grid.innerHTML = html || `<div class="empty-state">No modules match "${esc(filter)}"</div>`;
}

function renderSessions(sessions) {
    const el = dom.sessionList();
    if (!sessions || sessions.length === 0) {
        el.innerHTML = "<em>None</em>";
        return;
    }
    el.innerHTML = sessions
        .map(s => `<div class="mod-item">${esc(s.name || s.id)} [${esc(s.status)}]</div>`)
        .join("");
}

// ── Findings ─────────────────────────────────────────────────────

function addFinding(f) {
    state.findings.push(f);
    appendLog(`[FINDING] ${f.severity || "?"}: ${f.title || f.description || ""}`, "log-finding");
    renderFindings();
}

function renderFindings() {
    const body = dom.findingsBody();
    const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };

    body.innerHTML = "";
    for (const f of state.findings) {
        const sev = (f.severity || "info").toLowerCase();
        counts[sev] = (counts[sev] || 0) + 1;

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><span class="sev-${sev}">${esc(sev.toUpperCase())}</span></td>
            <td>${esc(f.title || "—")}</td>
            <td><code>${esc(f.module || "—")}</code></td>
            <td>${esc(f.description || "—")}</td>`;
        body.appendChild(tr);
    }

    dom.countCritical().textContent = `${counts.critical} Critical`;
    dom.countHigh().textContent     = `${counts.high} High`;
    dom.countMedium().textContent   = `${counts.medium} Medium`;
    dom.countLow().textContent      = `${counts.low} Low`;
    dom.countInfo().textContent     = `${counts.info} Info`;

    const hasFindings = state.findings.length > 0;
    dom.noFindings().style.display     = hasFindings ? "none" : "block";
    dom.findingsTable().style.display  = hasFindings ? "table" : "none";
}

// ── Tabs ─────────────────────────────────────────────────────────

function initTabs() {
    $$(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            $$(".tab").forEach(t => t.classList.remove("active"));
            $$(".tab-content").forEach(c => c.classList.remove("active"));
            tab.classList.add("active");
            $(`#tab-${tab.dataset.tab}`).classList.add("active");
        });
    });
}

// ── Keyboard ─────────────────────────────────────────────────────

function initKeyboard() {
    const input = dom.promptInput();
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            send();
        } else if (e.key === "ArrowUp") {
            if (state.historyIdx > 0) {
                state.historyIdx--;
                input.value = state.history[state.historyIdx] || "";
            }
        } else if (e.key === "ArrowDown") {
            if (state.historyIdx < state.history.length - 1) {
                state.historyIdx++;
                input.value = state.history[state.historyIdx] || "";
            } else {
                state.historyIdx = state.history.length;
                input.value = "";
            }
        }
    });
}

// ── Boot ─────────────────────────────────────────────────────────

function init() {
    initTabs();
    initKeyboard();

    dom.btnConnect().addEventListener("click", connect);
    dom.btnSend().addEventListener("click", send);
    dom.btnStop().addEventListener("click", stop);

    dom.moduleSearch()?.addEventListener("input", (e) => {
        renderModuleGrid(state.modules, e.target.value);
    });

    // Welcome message
    appendLog("Welcome to <b>RELIC</b> — Pentesting Automation", "log-success");
    appendLog("Enter the API URL and click <b>Connect</b> to begin.", "log-info");
    appendLog("Type an objective or use <b>/cmd &lt;command&gt;</b> to run raw commands.", "log-info");

    renderFindings();
}

document.addEventListener("DOMContentLoaded", init);
