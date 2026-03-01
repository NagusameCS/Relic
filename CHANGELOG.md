# Changelog

All notable changes to Relic are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [0.1.0] — 2026-03-01

### Added

**Core Framework**
- Engine orchestration loop with LLM-driven iterative planning (`core/engine.py`)
- Pydantic configuration system with YAML + environment variable loading (`core/config.py`)
- Session persistence as JSON with command history and findings (`core/session.py`)
- Scope enforcement — allowlist-based command blocking for authorized targets only
- Event system (LogEvent, CommandEvent, OutputEvent, PlanEvent, FindingEvent)
- Safety cap of 50 iterations per objective

**LLM Client**
- Async Ollama HTTP client with `generate()`, `chat()`, and `generate_stream()` (`llm/ollama_client.py`)
- Thinking mode support for GLM-4.7-Flash chain-of-thought reasoning
- Automatic `_chat_via_generate()` fallback when chat endpoint returns empty content
- `_strip_thinking()` to clean `<think>` tags from generate responses
- Model management: `ensure_model()`, `list_models()`, `model_info()`, `health_check()`
- Fallback model support (primary → fallback → first available)

**86 Modules across 9 Categories**
- Reconnaissance (9): port-scan, subdomain-enum, dns-recon, web-recon, tech-detect, screenshot, http-probe, vhost-enum, cloud-enum
- Exploitation (8): sqli, brute-force, metasploit, password-crack, xss-exploit, lfi-exploit, rce-exploit, deserialization
- Web Testing (22): gobuster, ffuf, dirsearch, wfuzz, nikto, nuclei, wappalyzer, waf-detect, xss, ssrf, lfi, cmdi, wpscan, joomscan, droopescan, security-headers, cors, clickjack, spider, param-miner, subdomain-takeover, graphql
- Network (13): masscan, rustscan, nmap-advanced, tcpdump, arp-spoof, responder, bettercap, smb-enum, ldap-enum, snmp-enum, netcat, ping-sweep, traceroute
- OSINT (11): whois, theharvester, amass, subfinder, shodan, censys, dns-advanced, wayback, cert-transparency, google-dork, gitleaks
- Crypto & SSL (6): sslyze, testssl, sslscan, cert-analysis, cipher-enum, tls-version
- Post-Exploitation (8): linpeas, winpeas, sudo-check, cred-harvest, mimikatz, pivot, persistence, data-exfil
- API Testing (8): rest-fuzz, jwt-analysis, auth-bypass, idor, rate-limit, api-schema, ssrf-api, cors-api
- Reporting (1): report (Jinja2 + LLM markdown generation)

**Web UI**
- Static browser-based interface (HTML/CSS/JS) on GitHub Pages
- FastAPI backend on port 8746 with 13 REST endpoints + WebSocket
- Real-time event streaming via WebSocket
- Model selector with 7 presets grouped by hardware tier (VRAM/RAM requirements)
- Scope management from sidebar
- Module browser with search
- Findings dashboard with severity breakdown
- Generate Report button (LLM-generated executive summary)
- Inline Explain Error button on error log lines
- Setup guide modal (5-step installation walkthrough)
- Pure black & white design, Google Material Symbols Outlined icons

**Terminal UI**
- Textual-based TUI with dark theme
- Sidebar (session info, VM status, LLM status, module tree)
- Output log with command history
- Prompt with objective and `/cmd` support
- CLI disclaimer acceptance flow

**Setup & Distribution**
- One-click `relic-setup.bat` Windows installer
  - Auto-detects/installs Python 3.10+ via winget
  - Auto-detects/installs Ollama
  - Hardware detection (RAM via WMI, VRAM via nvidia-smi)
  - Auto-selects best model for detected hardware
  - Pulls model, installs package, creates desktop launcher
  - Terms & Conditions acceptance
- `pip install relic[web]` for manual installation
- `relic-web` and `relic` entry point commands

**Configuration**
- `config.default.yaml` with sensible defaults
- LLM settings: model, temperature, num_ctx, max_tokens, timeout, fallback
- VM settings: provider, image, memory, CPUs, snapshots, privileged mode
- Scope settings: authorized_targets, strict mode, authorization URL
- Environment variable overrides with `RELIC_` prefix

**Documentation**
- Comprehensive README with architecture, module tables, detection considerations, deep dive, API reference
- SECURITY.md with vulnerability reporting policy
- CONTRIBUTING.md with module development guide
- CHANGELOG.md (this file)
- MIT License with security disclaimer
