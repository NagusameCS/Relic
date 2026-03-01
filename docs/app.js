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
    models: [],
    history: [],
    historyIdx: -1,
};

// ── DOM refs ─────────────────────────────────────────────────────

const dom = {
    apiUrl:       () => $("#api-url"),
    btnConnect:   () => $("#btn-connect"),
    btnSend:      () => $("#btn-send"),
    btnStop:      () => $("#btn-stop"),
    status:       () => $("#status-indicator"),
    modelLabel:   () => $("#model-label"),
    modelSelect:  () => $("#model-select"),
    modelSpecs:   () => $("#model-specs"),
    outputLog:    () => $("#output-log"),
    promptInput:  () => $("#prompt-input"),
    scopeList:    () => $("#scope-list"),
    moduleTree:   () => $("#module-tree"),
    moduleCount:  () => $("#module-count"),
    moduleGrid:   () => $("#module-grid"),
    moduleSearch: () => $("#module-search"),
    sessionList:  () => $("#session-list"),
    findingsBody: () => $("#findings-body"),
    noFindings:   () => $("#no-findings"),
    findingsTable:() => $("#findings-table"),
    countCritical:() => $("#count-critical"),
    countHigh:    () => $("#count-high"),
    countMedium:  () => $("#count-medium"),
    countLow:     () => $("#count-low"),
    countInfo:    () => $("#count-info"),
};

// ── Utilities ────────────────────────────────────────────────────

function ts() {
    return new Date().toLocaleTimeString("en-US", { hour12: false });
}

function esc(text) {
    const d = document.createElement("div");
    d.textContent = String(text);
    return d.innerHTML;
}

function appendLog(html, cls = "", opts = {}) {
    const log = dom.outputLog();
    const line = document.createElement("div");
    line.className = `log-line ${cls}`.trim();
    let content = `<span class="timestamp">${ts()}</span>${html}`;

    // If this is an error, add an Explain button
    if (opts.explainable && state.connected) {
        const rawText = opts.rawText || html.replace(/<[^>]+>/g, "");
        const safeText = btoa(unescape(encodeURIComponent(rawText)));
        content += ` <button class="btn-explain" onclick="explainError('${safeText}')">` +
            `<span class="material-symbols-outlined">lightbulb</span>Explain</button>`;
    }

    line.innerHTML = content;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
}

function setStatus(s) {
    const el = dom.status();
    el.className = `status ${s}`;
    el.innerHTML = s === "connected" ? '<span class="material-symbols-outlined icon-inline">check_circle</span> Connected'
                 : s === "working"   ? '<span class="material-symbols-outlined icon-inline">autorenew</span> Working'
                 : '<span class="material-symbols-outlined icon-inline">circle</span> Disconnected';
}

// ── Modals ───────────────────────────────────────────────────────

function openModal(id) { $(id).style.display = "flex"; }
function closeModal(id) { $(id).style.display = "none"; }

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

        const [scope, modules, sessions, models] = await Promise.all([
            apiGet("/api/scope"),
            apiGet("/api/modules"),
            apiGet("/api/sessions"),
            apiGet("/api/models"),
        ]);

        renderScope(scope);
        renderModules(modules);
        renderSessions(sessions);
        renderModels(models);
        connectWebSocket();

    } catch (e) {
        state.connected = false;
        setStatus("disconnected");
        appendLog(`Connection failed: ${esc(e.message)}`, "log-error", { explainable: true, rawText: e.message });
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
            const isErr = (ev.level || "").includes("error");
            appendLog(esc(ev.message), `log-${ev.level || "info"}`, { explainable: isErr, rawText: ev.message });
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

    state.history.push(text);
    state.historyIdx = state.history.length;
    input.value = "";

    if (!state.connected) {
        appendLog("Not connected — click Connect first.", "log-error", { explainable: false });
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
            appendLog(`Error: ${esc(e.message)}`, "log-error", { explainable: true, rawText: e.message });
        }
        setStatus("connected");
    } else {
        appendLog(`Objective: ${esc(text)}`, "log-command");
        setStatus("working");
        try {
            await apiPost("/api/objective", { objective: text });
            appendLog("Objective submitted — streaming output below…", "log-info");
        } catch (e) {
            appendLog(`Error: ${esc(e.message)}`, "log-error", { explainable: true, rawText: e.message });
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
        appendLog(`Error: ${esc(e.message)}`, "log-error", { explainable: true, rawText: e.message });
    }
}

// ── Model selector ───────────────────────────────────────────────

function renderModels(models) {
    state.models = models;
    const sel = dom.modelSelect();
    sel.innerHTML = "";

    const tiers = { recommended: "Recommended", high: "High-end", medium: "Mid-range", low: "Low-end" };
    const grouped = {};
    for (const m of models) {
        const t = m.tier || "medium";
        if (!grouped[t]) grouped[t] = [];
        grouped[t].push(m);
    }

    for (const [tier, label] of Object.entries(tiers)) {
        if (!grouped[tier]) continue;
        const group = document.createElement("optgroup");
        group.label = label;
        for (const m of grouped[tier]) {
            const opt = document.createElement("option");
            opt.value = m.id;
            opt.textContent = `${m.name} (${m.size_gb} GB)${m.installed ? " ✓" : ""}`;
            if (m.active) opt.selected = true;
            group.appendChild(opt);
        }
        sel.appendChild(group);
    }

    // Show specs of currently selected
    updateModelSpecs();
}

function updateModelSpecs() {
    const sel = dom.modelSelect();
    const id = sel.value;
    const m = state.models.find(x => x.id === id);
    const el = dom.modelSpecs();
    if (!m) { el.innerHTML = ""; return; }

    el.innerHTML = `
        <div class="spec-row"><span>VRAM</span><span class="spec-val">≥ ${m.min_vram_gb} GB</span></div>
        <div class="spec-row"><span>RAM</span><span class="spec-val">≥ ${m.min_ram_gb} GB</span></div>
        <div class="spec-row"><span>Disk</span><span class="spec-val">${m.size_gb} GB</span></div>
        <div class="spec-row"><span>Status</span><span class="${m.installed ? "spec-installed" : "spec-missing"}">${m.installed ? "Installed" : "Not installed"}</span></div>
        <div style="margin-top:4px;color:var(--dim)">${esc(m.description)}</div>`;
}

async function switchModel() {
    const sel = dom.modelSelect();
    const id = sel.value;
    if (!id || !state.connected) return;

    const m = state.models.find(x => x.id === id);
    appendLog(`Switching model to <b>${esc(m ? m.name : id)}</b>…`, "log-info");

    try {
        const res = await api("/api/model", {
            method: "PUT",
            body: JSON.stringify({ model: id }),
        });
        dom.modelLabel().textContent = res.model || id;
        appendLog(`Model switched to <b>${esc(res.model)}</b>`, "log-success");

        if (m && !m.installed) {
            appendLog(`Model not installed locally. Run: <b>ollama pull ${esc(m.ollama)}</b>`, "log-warning");
        }
    } catch (e) {
        appendLog(`Failed to switch model: ${esc(e.message)}`, "log-error", { explainable: true, rawText: e.message });
    }
}

// ── Render helpers ───────────────────────────────────────────────

function renderScope(scope) {
    const el = dom.scopeList();
    if (!scope.authorized_targets || scope.authorized_targets.length === 0) {
        el.innerHTML = "<em>No targets set</em>";
        return;
    }
    el.innerHTML = scope.authorized_targets
        .map(t => `<div class="scope-item">${esc(t)}</div>`)
        .join("");

    const input = $("#target-url");
    if (input && !input.value) {
        input.value = scope.authorized_targets[0] || "";
    }
}

async function setTarget() {
    const input = $("#target-url");
    const target = (input.value || "").trim();
    if (!target) {
        appendLog("Enter a target URL first.", "log-warning");
        return;
    }
    if (!state.connected) {
        appendLog("Not connected — click Connect first.", "log-error");
        return;
    }
    try {
        const scope = await api("/api/scope", {
            method: "PUT",
            body: JSON.stringify({
                authorized_targets: [target],
                authorization_url: target.startsWith("http") ? target : `https://${target}`,
            }),
        });
        renderScope(scope);
        appendLog(`Target set: <b>${esc(target)}</b>`, "log-success");
    } catch (e) {
        appendLog(`Failed to set target: ${esc(e.message)}`, "log-error", { explainable: true, rawText: e.message });
    }
}

function renderModules(modules) {
    state.modules = modules;

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
        el.innerHTML = '<span class="dim">None</span>';
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

// ── Report Generation ────────────────────────────────────────────

async function generateReport() {
    if (!state.connected) {
        appendLog("Not connected — click Connect first.", "log-error");
        return;
    }

    openModal("#report-overlay");
    $("#report-content").textContent = "Generating report…";

    try {
        const res = await apiPost("/api/report", {});
        if (res.error) {
            $("#report-content").textContent = `Error: ${res.error}`;
        } else {
            $("#report-content").textContent = res.report;
        }
    } catch (e) {
        $("#report-content").textContent = `Failed to generate report: ${e.message}`;
    }
}

// ── Error Explanation ────────────────────────────────────────────
// Global function so inline onclick works
window.explainError = async function(base64Text) {
    const errorText = decodeURIComponent(escape(atob(base64Text)));

    openModal("#explain-overlay");
    $("#explain-content").textContent = "Generating explanation…";

    try {
        const res = await apiPost("/api/explain", { error_text: errorText });
        if (res.error) {
            $("#explain-content").textContent = `Error: ${res.error}`;
        } else {
            $("#explain-content").textContent = res.explanation;
        }
    } catch (e) {
        $("#explain-content").textContent = `Failed: ${e.message}`;
    }
};

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
    $("#btn-set-target")?.addEventListener("click", setTarget);
    $("#btn-report")?.addEventListener("click", generateReport);

    // Model selector
    dom.modelSelect()?.addEventListener("change", () => {
        updateModelSpecs();
        switchModel();
    });

    // Setup modal
    $("#btn-setup")?.addEventListener("click", () => openModal("#setup-overlay"));
    $("#btn-close-setup")?.addEventListener("click", () => closeModal("#setup-overlay"));
    $("#btn-close-report")?.addEventListener("click", () => closeModal("#report-overlay"));
    $("#btn-close-explain")?.addEventListener("click", () => closeModal("#explain-overlay"));

    // Close modals on overlay click
    $$(".modal-overlay").forEach(ov => {
        ov.addEventListener("click", (e) => {
            if (e.target === ov) ov.style.display = "none";
        });
    });

    // Escape closes modals
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            $$(".modal-overlay").forEach(ov => ov.style.display = "none");
        }
    });

    // Allow Enter in target input
    $("#target-url")?.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); setTarget(); }
    });

    dom.moduleSearch()?.addEventListener("input", (e) => {
        renderModuleGrid(state.modules, e.target.value);
    });

    // Welcome
    appendLog("Welcome to <b>RELIC</b>", "log-command");
    appendLog("Enter the API URL and click Connect to begin.", "log-info");
    appendLog('Type an objective or use /cmd &lt;command&gt; to run raw commands.', "log-info");
    appendLog('Click <b>Setup</b> in the header if you need installation help.', "log-info");

    renderFindings();
}

document.addEventListener("DOMContentLoaded", init);
