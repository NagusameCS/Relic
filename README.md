# RELIC

```
██████╗ ███████╗██╗     ██╗ ██████╗
██╔══██╗██╔════╝██║     ██║██╔════╝
██████╔╝█████╗  ██║     ██║██║
██╔══██╗██╔══╝  ██║     ██║██║
██║  ██║███████╗███████╗██║╚██████╗
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝ ╚═════╝
    Local LLM Pentesting Automation
```

> **Automated penetration testing powered entirely by local LLMs. No cloud. No API keys. Your data never leaves your machine.**

[![MIT License](https://img.shields.io/badge/license-MIT-white?style=flat-square)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-white?style=flat-square)](https://python.org)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-white?style=flat-square)](https://ollama.com)

---

## Legal Disclaimer

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                          ⚠  LEGAL DISCLAIMER  ⚠                           ║
║                                                                              ║
║  Relic is designed EXCLUSIVELY for authorized security testing and           ║
║  educational purposes. By using this software, you acknowledge and agree:    ║
║                                                                              ║
║  1. You have EXPLICIT WRITTEN AUTHORIZATION from the system owner(s)        ║
║     before conducting any security testing.                                  ║
║                                                                              ║
║  2. Unauthorized access to computer systems is ILLEGAL under the Computer   ║
║     Fraud and Abuse Act (CFAA), the Computer Misuse Act, and similar        ║
║     laws worldwide. Violations carry severe criminal penalties.              ║
║                                                                              ║
║  3. You accept FULL RESPONSIBILITY for your actions. The developers and     ║
║     contributors of Relic bear NO LIABILITY for any misuse of this tool.    ║
║                                                                              ║
║  4. This tool should ONLY be used against systems you OWN or have explicit  ║
║     written permission to test.                                              ║
║                                                                              ║
║  5. All testing must be conducted within ISOLATED, VIRTUALIZED              ║
║     ENVIRONMENTS to prevent unintended impact on production systems.        ║
║                                                                              ║
║  USE RESPONSIBLY  ·  HACK ETHICALLY  ·  RESPECT THE LAW                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

**By downloading, installing, or using Relic, you agree to these terms.**

---

## Table of Contents

- [What is Relic?](#what-is-relic)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Quick Start (One-Click Setup)](#quick-start-one-click-setup)
- [Manual Installation](#manual-installation)
- [Web UI](#web-ui)
- [Terminal UI](#terminal-ui)
- [Modules (86)](#modules-86)
- [Model Selection & Hardware Requirements](#model-selection--hardware-requirements)
- [Configuration](#configuration)
- [Scope Enforcement & Safety](#scope-enforcement--safety)
- [Detection Considerations](#detection-considerations)
- [How the Engine Works (Deep Dive)](#how-the-engine-works-deep-dive)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [FAQ](#faq)
- [License](#license)

---

## What is Relic?

Relic is an open-source penetration testing automation framework that uses **local large language models** (LLMs) to plan, execute, and adapt security assessments — all running on your own hardware with zero cloud dependencies.

**Core principles:**

| Principle | Detail |
|-----------|--------|
| **100% Local** | LLM inference via [Ollama](https://ollama.com). No OpenAI, no API keys, no data exfiltration. Everything stays on your machine. |
| **AI-Driven** | The LLM autonomously plans commands, executes them, analyses output, and adapts its strategy across iterations. |
| **86 Modules** | Covers 9 categories: reconnaissance, exploitation, web testing, network analysis, OSINT, crypto/SSL, post-exploitation, API testing, and reporting. |
| **Scope-Locked** | Hard-coded scope enforcement at the engine level. Commands targeting unauthorized hosts are blocked before execution. |
| **Virtualized** | All offensive commands execute inside isolated VMs (Vagrant/VirtualBox), never on your host system. |
| **Dual Interface** | Rich terminal TUI (Textual) + browser-based Web UI served via FastAPI. |

---

## How It Works

Relic operates as an **autonomous pentesting loop**. You provide a high-level objective, and the LLM iteratively works toward it:

```
┌───────────────────────────────────────────────────────────┐
│                    YOU (the operator)                       │
│  "Find and exploit vulnerabilities on 10.0.0.5"           │
└───────────────────┬───────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────┐
│                   RELIC ENGINE                             │
│                                                           │
│  1. Receive objective                                     │
│  2. Build context (scope + history + findings)            │
│  3. Send to LLM with structured prompt                    │
│  4. LLM returns JSON plan:                                │
│     [{"command": "nmap -sV 10.0.0.5",                    │
│       "description": "Service enumeration"}]              │
│  5. Scope check — block if out-of-scope                   │
│  6. Execute command in VM via SSH                          │
│  7. Capture output, feed back to LLM                      │
│  8. LLM analyses, proposes next commands                  │
│  9. Repeat steps 4-8 until objective met or [] returned   │
│ 10. Record findings in session                            │
└───────────────────────────────────────────────────────────┘
```

The engine caps at **50 iterations** per objective as a safety measure. You can stop at any time.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 USER INTERFACES                                  │
│  ┌──────────────────────┐    ┌──────────────────────┐           │
│  │   Terminal TUI        │    │   Web UI (Browser)   │           │
│  │   Textual + Rich      │    │   Static HTML/JS     │           │
│  │   relic               │    │   → FastAPI :8746    │           │
│  └──────────┬───────────┘    └──────────┬───────────┘           │
│             │                           │ HTTP + WebSocket       │
│             ▼                           ▼                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    ENGINE (core/engine.py)               │    │
│  │  • Objective loop          • Scope enforcement           │    │
│  │  • Plan parsing (JSON)     • Event broadcasting          │    │
│  │  • Task execution          • Session management          │    │
│  └─────┬───────────┬─────────────────────┬─────────────────┘    │
│        │           │                     │                       │
│        ▼           ▼                     ▼                       │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐      │
│  │ Sessions │  │  LLM Client  │  │     VM Manager       │      │
│  │  (JSON)  │  │  (Ollama)    │  │  (Vagrant + SSH)     │      │
│  │  ~/.relic │  │  :11434      │  │  Kali Linux VM       │      │
│  └──────────┘  └──────────────┘  └──────────────────────┘      │
│                                          │                       │
│  ┌──────────────────────────────────────┐│                       │
│  │          86 MODULES                   ││                       │
│  │  recon · exploit · web · network     ││                       │
│  │  osint · crypto · post-exploit       ││                       │
│  │  api · reporting                     ││                       │
│  └──────────────────────────────────────┘│                       │
└──────────────────────────────────────────┘                       │
```

### Component Breakdown

| Component | File | Purpose |
|-----------|------|---------|
| **Engine** | `core/engine.py` | Central orchestrator. Runs the objective loop, enforces scope, parses LLM plans, executes tasks, emits events. |
| **LLM Client** | `llm/ollama_client.py` | Async HTTP client for Ollama. Supports `generate()`, `chat()` with thinking mode, streaming, model switching, and `_chat_via_generate()` fallback. |
| **Session Manager** | `core/session.py` | Persists engagement state (command history, findings, metadata) as JSON files in `~/.relic/sessions/`. |
| **Config** | `core/config.py` | Pydantic config loaded from YAML → env vars → defaults. Covers LLM, VM, scope, modules, UI settings. |
| **Scope Enforcer** | `core/engine.py` | Allowlist-based system. Commands referencing hosts outside `authorized_targets` are blocked before reaching the VM. |
| **Web API** | `web/api.py` | FastAPI server (port 8746) with REST endpoints + WebSocket for real-time event streaming. |
| **TUI** | `ui/app.py` | Textual-based terminal interface with dark theme, sidebar, output pane, and prompt. |
| **Modules** | `modules/*.py` | 86 modules across 9 categories. Each defines commands, parsing logic, and finding extraction. |

---

## Quick Start (One-Click Setup)

**Windows users** — download and double-click one file:

1. Download [`relic-setup.bat`](relic-setup.bat) from the repository
2. Double-click it
3. Accept the Terms & Conditions (press **Y**)
4. Everything else is fully automatic — no more input needed

The setup wizard will:

| Step | What it does |
|------|-------------|
| 1 | Detect Python 3.10+ (installs via winget if missing) |
| 2 | Detect Ollama (downloads & installs silently if missing) |
| 3 | Start the Ollama service and wait for readiness |
| 4 | `pip install relic[web]` from this repository |
| 5 | Detect your GPU (VRAM via nvidia-smi) and RAM |
| 6 | Auto-select and download the best AI model for your hardware |
| 7 | Create a **"Launch RELIC.bat"** shortcut on your Desktop |
| 8 | Start the server and open the Web UI in your browser |

After setup, just double-click **Launch RELIC.bat** on your desktop whenever you want to use Relic.

---

## Manual Installation

### Prerequisites

- **Python 3.10+** — [python.org/downloads](https://python.org/downloads)
- **Ollama** — [ollama.com/download](https://ollama.com/download)
- **Vagrant + VirtualBox** *(for VM execution)* — [vagrantup.com](https://www.vagrantup.com/) + [virtualbox.org](https://www.virtualbox.org/)

### Install

```bash
# Clone
git clone https://github.com/NagusameCS/Relic.git
cd Relic

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install with web UI support
pip install -e ".[web]"

# Pull a model (see Model Selection section for recommendations)
ollama pull glm4-flash
```

### Launch

```bash
# Web UI (recommended — browser-based)
relic-web
# Opens at http://127.0.0.1:8746

# Terminal UI
relic
```

---

## Web UI

The browser-based interface is served as a static site and connects to the local FastAPI backend.

**Live interface:** [https://nagusamecs.github.io/Relic](https://nagusamecs.github.io/Relic) *(requires local backend running)*

### Features

- **Real-time output** — WebSocket streams engine events (logs, commands, output, findings) as they happen
- **Model selector** — Switch between 7 LLM presets grouped by hardware tier, with live VRAM/RAM requirements display
- **Scope manager** — Set authorized targets directly from the sidebar
- **Module browser** — Search and browse all 86 modules with descriptions, filterable by name/category
- **Findings dashboard** — Table with severity counts (Critical / High / Medium / Low / Info) and per-finding details
- **Generate Report** — One-click LLM-generated executive summary of all findings
- **Explain Errors** — Inline button on every error log line sends it to the LLM for plain-English explanation
- **Session history** — View past engagement sessions
- **Setup guide** — Built-in modal with step-by-step installation instructions

### Design

Pure black & white aesthetic. No colors, no gradients — just `#000000` through `#ffffff`. Google Material Symbols Outlined for iconography.

---

## Terminal UI

Classic terminal interface built with [Textual](https://textual.textualize.io/) and [Rich](https://rich.readthedocs.io/).

```bash
relic                    # Launch with disclaimer prompt
relic --no-disclaimer    # Skip disclaimer (scripted use)
relic --version          # Show version
relic config --show      # Display current config as JSON
relic disclaimer         # Show the full disclaimer text
```

### TUI Commands

| Input | Action |
|-------|--------|
| Free text | Sends as objective to LLM for autonomous execution |
| `!nmap -sV 10.0.0.5` | Execute raw command in VM |
| `/help` | Show help |
| `/vm start` | Start the Kali Linux VM |
| `/session my-pentest` | Create/load a named session |
| `/module port-scan 10.0.0.5` | Run a specific module |
| `/report` | Generate a markdown pentest report |
| `Escape` | Stop the current LLM execution |
| `Ctrl+C` | Quit |

---

## Modules (86)

### Reconnaissance (9 modules)

| Module | Description | Tool |
|--------|-------------|------|
| `port-scan` | TCP/UDP port scanning with service/version/OS detection | nmap |
| `subdomain-enum` | Subdomain discovery + HTTP probing | subfinder, httpx |
| `dns-recon` | DNS record enumeration + zone transfer attempts | dig, dnsrecon |
| `web-recon` | Directory brute-force, technology fingerprinting, Nikto scan | gobuster, nikto |
| `tech-detect` | Web technology stack identification | whatweb, wappalyzer |
| `screenshot` | Capture screenshots of web targets | gowitness |
| `http-probe` | HTTP/HTTPS probing of discovered hosts | httpx |
| `vhost-enum` | Virtual host enumeration via Host header fuzzing | gobuster vhost |
| `cloud-enum` | Cloud resource enumeration (S3 buckets, Azure blobs, GCP) | cloud_enum |

### Exploitation (8 modules)

| Module | Description | Tool |
|--------|-------------|------|
| `sqli` | SQL injection detection and exploitation | sqlmap |
| `brute-force` | Credential brute-forcing across protocols (SSH, FTP, HTTP, etc.) | hydra |
| `metasploit` | Automated Metasploit exploit selection and execution | msfconsole |
| `password-crack` | Offline hash cracking | john, hashcat |
| `xss-exploit` | Cross-site scripting exploitation | dalfox |
| `lfi-exploit` | Local file inclusion exploitation | custom |
| `rce-exploit` | Remote code execution exploitation | custom |
| `deserialization` | Insecure deserialization exploitation | ysoserial |

### Web Testing (22 modules)

| Module | Description | Tool |
|--------|-------------|------|
| `gobuster` | Directory/file brute-force | gobuster |
| `ffuf` | Fast web fuzzer for dirs, params, and vhosts | ffuf |
| `dirsearch` | Directory discovery | dirsearch |
| `wfuzz` | Payload-based web fuzzing | wfuzz |
| `nikto` | Web server vulnerability scanner | nikto |
| `nuclei` | Template-based vulnerability scanning (9000+ templates) | nuclei |
| `wappalyzer` | Technology fingerprinting | wappalyzer |
| `waf-detect` | Web Application Firewall detection and fingerprinting | wafw00f |
| `xss` | Cross-site scripting detection | dalfox, XSStrike |
| `ssrf` | Server-side request forgery testing | custom |
| `lfi` | Local file inclusion testing | custom |
| `cmdi` | OS command injection testing | commix |
| `wpscan` | WordPress vulnerability scanning | wpscan |
| `joomscan` | Joomla vulnerability scanning | joomscan |
| `droopescan` | Drupal/SilverStripe CMS scanning | droopescan |
| `security-headers` | HTTP security header analysis | custom |
| `cors` | CORS misconfiguration detection | custom |
| `clickjack` | Clickjacking (X-Frame-Options) testing | custom |
| `spider` | Web crawling and link extraction | gospider |
| `param-miner` | Hidden parameter discovery | arjun, parameth |
| `subdomain-takeover` | Subdomain takeover detection | subjack |
| `graphql` | GraphQL introspection and query testing | graphql-cop |

### Network (13 modules)

| Module | Description | Tool |
|--------|-------------|------|
| `masscan` | High-speed port scanning (millions of packets/sec) | masscan |
| `rustscan` | Fast Rust-based port scanner → nmap handoff | rustscan |
| `nmap-advanced` | Advanced nmap with NSE scripts | nmap |
| `tcpdump` | Packet capture and analysis | tcpdump |
| `arp-spoof` | ARP spoofing for MitM positioning | arpspoof |
| `responder` | LLMNR/NBT-NS/mDNS poisoner for credential capture | responder |
| `bettercap` | Network attack framework (ARP, DNS, HTTPS proxy) | bettercap |
| `smb-enum` | SMB share and user enumeration | enum4linux, smbclient |
| `ldap-enum` | LDAP directory enumeration | ldapsearch |
| `snmp-enum` | SNMP community string and MIB enumeration | snmpwalk |
| `netcat` | Raw TCP/UDP connection utility | netcat |
| `ping-sweep` | ICMP host discovery | nmap -sn |
| `traceroute` | Network path tracing | traceroute |

### OSINT (11 modules)

| Module | Description | Tool |
|--------|-------------|------|
| `whois` | Domain registration and ownership lookup | whois |
| `theharvester` | Email, subdomain, and name harvesting from public sources | theHarvester |
| `amass` | Attack surface discovery and mapping | amass |
| `subfinder` | Fast passive subdomain enumeration | subfinder |
| `shodan` | Shodan search for exposed services and devices | shodan |
| `censys` | Censys internet-wide scan data queries | censys |
| `dns-advanced` | Advanced DNS enumeration (DNSSEC, AXFR, brute-force) | dnsrecon |
| `wayback` | Wayback Machine URL history retrieval | waybackurls |
| `cert-transparency` | Certificate Transparency log monitoring | crt.sh |
| `google-dork` | Google dorking for information disclosure | custom |
| `gitleaks` | Git repository secret scanning | gitleaks |

### Crypto & SSL (6 modules)

| Module | Description | Tool |
|--------|-------------|------|
| `sslyze` | SSL/TLS configuration analysis | sslyze |
| `testssl` | Comprehensive TLS testing | testssl.sh |
| `sslscan` | SSL cipher and certificate scanner | sslscan |
| `cert-analysis` | X.509 certificate chain validation and analysis | openssl |
| `cipher-enum` | Cipher suite enumeration and grading | nmap ssl-enum |
| `tls-version` | TLS version support detection (SSLv3, TLS 1.0–1.3) | custom |

### Post-Exploitation (8 modules)

| Module | Description | Tool |
|--------|-------------|------|
| `linpeas` | Linux privilege escalation enumeration | linPEAS |
| `winpeas` | Windows privilege escalation enumeration | winPEAS |
| `sudo-check` | Sudo misconfiguration and GTFOBins check | sudo -l |
| `cred-harvest` | Credential harvesting from config files, histories, etc. | custom |
| `mimikatz` | Windows credential extraction | mimikatz |
| `pivot` | Network pivoting setup (port forwards, SOCKS proxy) | chisel, ssh |
| `persistence` | Persistence mechanism installation (cron, services, etc.) | custom |
| `data-exfil` | Data exfiltration channel testing | custom |

### API Testing (8 modules)

| Module | Description | Tool |
|--------|-------------|------|
| `rest-fuzz` | REST API endpoint fuzzing | custom, ffuf |
| `jwt-analysis` | JWT token analysis, cracking, and claim manipulation | jwt_tool |
| `auth-bypass` | Authentication bypass testing (IDOR, forced browsing, etc.) | custom |
| `idor` | Insecure Direct Object Reference detection | custom |
| `rate-limit` | Rate limiting and throttle bypass testing | custom |
| `api-schema` | OpenAPI/Swagger schema discovery and validation | custom |
| `ssrf-api` | SSRF via API endpoint parameters | custom |
| `cors-api` | API-specific CORS misconfiguration testing | custom |

### Reporting (1 module)

| Module | Description | Tool |
|--------|-------------|------|
| `report` | Generates a structured Markdown pentest report from session findings | Jinja2 + LLM |

---

## Model Selection & Hardware Requirements

Relic auto-selects the best model for your hardware during setup. You can also switch models from the Web UI at any time.

| Model | Parameters | Disk | Min VRAM | Min RAM | Tier | Notes |
|-------|-----------|------|----------|---------|------|-------|
| **GLM-4.7-Flash** | 30B (3B active, MoE) | 19 GB | 6 GB | 16 GB | Recommended | Best quality. Mixture-of-Experts means only 3B params active at once — surprisingly fast for its size. |
| **Gemma 3 12B** | 12B (dense) | 8 GB | 8 GB | 16 GB | High-end | Strong reasoning, needs full 8 GB VRAM. |
| **Qwen 2.5 7B** | 7B (dense) | 5 GB | 5 GB | 8 GB | Mid-range | Good code understanding, balanced speed/quality. |
| **Gemma 3 4B** | 4B (dense) | 3 GB | 4 GB | 8 GB | Mid-range | Lightweight, decent for 4 GB VRAM cards. |
| **Qwen 2.5 3B** | 3B (dense) | 2 GB | 2 GB | 4 GB | Low-end | Runs on almost anything, acceptable quality. |
| **Llama 3.2 3B** | 3B (dense) | 2 GB | 2 GB | 4 GB | Low-end | Meta's compact model. Fast inference. |
| **Phi-3.5 Mini** | 3.8B (dense) | 2 GB | 3 GB | 4 GB | Low-end | Great for integrated GPUs (Intel/AMD iGPU). |

### Inference Modes

- **GPU offload (VRAM ≥ model size):** Full speed. NVIDIA CUDA or AMD ROCm.
- **Partial GPU offload:** Some layers on GPU, rest on CPU. Slower but works.
- **CPU-only (no discrete GPU):** Possible with 3B–4B models. Expect 2–5 tokens/sec on modern CPUs.

### How Ollama Uses Your Hardware

Ollama automatically manages GPU/CPU split. If your VRAM is insufficient for the full model, it offloads layers to CPU RAM. No manual configuration needed. Relic sets `num_ctx=8192` to keep memory within bounds.

---

## Configuration

### Config File

```bash
# Copy default config
mkdir -p ~/.relic
cp config.default.yaml ~/.relic/config.yaml
```

Key settings in `~/.relic/config.yaml`:

```yaml
llm:
  provider: ollama
  base_url: "http://localhost:11434"
  model: "glm4-flash"         # Ollama model name
  temperature: 0.7             # Lower = more deterministic
  max_tokens: 8192             # Max output tokens per LLM call
  num_ctx: 8192                # Context window (raise if >32GB RAM)
  timeout: 300                 # Seconds before LLM timeout
  fallback_model: "gemma3:12b" # Used if primary model unavailable

vm:
  provider: vagrant
  base_image: "kalilinux/rolling"
  memory: 4096                 # VM RAM in MB
  cpus: 2
  snapshot_on_start: true      # Auto-snapshot for easy rollback
  privileged: true             # Root access inside VM
  unrestricted_network: true   # No network restrictions in VM

scope:
  authorized_targets:
    - "example.com"            # ONLY these targets will be tested
  strict: true                 # Block commands outside scope
  authorization_url: "https://example.com/pentest-auth"

session:
  workspace_dir: "~/.relic/sessions"
  auto_save: true
  save_interval: 60

ui:
  theme: "relic-dark"
  log_level: "INFO"
  max_output_lines: 5000
```

### Environment Variable Overrides

Prefix `RELIC_` with `__` as section separator:

```bash
export RELIC_LLM__MODEL=qwen2.5:7b
export RELIC_VM__MEMORY=8192
export RELIC_SCOPE__STRICT=true
```

---

## Scope Enforcement & Safety

**Relic will never execute commands against unauthorized targets.**

### How Scope Enforcement Works

The engine checks every command — both LLM-generated and user-entered — before execution:

```
Command received
      │
      ▼
┌─────────────┐     ┌──────────────┐
│ Is scope     │──▶  │ Local-only?  │──▶ ALLOW
│ strict=true? │     │ (cat, ls,    │    (no external target)
│              │     │  echo, grep) │
└──────┬──────┘     └──────────────┘
       │ yes
       ▼
┌──────────────────┐
│ References an     │──▶ ALLOW
│ authorized target │
│ or localhost?     │
└──────┬───────────┘
       │ no
       ▼
┌──────────────────┐
│ Contains any      │──▶ BLOCK ✗
│ domain, IP, or    │    "BLOCKED — outside authorized scope"
│ URL pattern?      │
└──────┬───────────┘
       │ no (purely local)
       ▼
      ALLOW
```

### What Gets Blocked

- Commands with domains outside `authorized_targets` (e.g., `nmap google.com`)
- Commands with IPs not in scope (e.g., `curl 192.168.1.1`)
- LLM-generated plans that reference external hosts
- Manual `/cmd` inputs through both web and terminal interfaces

### What Does NOT Get Blocked

- Local utilities (`cat`, `ls`, `grep`, `python`, `jq`, etc.)
- Commands referencing `localhost`, `127.0.0.1`, `::1`
- Commands with no host/domain/IP pattern (e.g., `sleep 5`)
- In-scope targets (exact match in `authorized_targets`)

### LLM System Prompt

The LLM itself is instructed via system prompt to respect scope:

> *"You MUST confine ALL commands to the target above. Do NOT scan, enumerate, or interact with any other host, path, or subdomain — even on the same domain. Anything outside the exact target URL is OUT OF SCOPE and must be refused."*

This is defense-in-depth: even if the LLM ignores the instruction, the engine scope check blocks execution.

---

## Detection Considerations

**This section exists for transparency. Understanding detection helps operators work within approved Rules of Engagement.**

### Network-Level Detection

| Activity | Detection Risk | Notes |
|----------|---------------|-------|
| **Port scanning (nmap, masscan)** | **High** | SYN scans, service probing, and OS fingerprinting generate distinctive traffic patterns. IDS/IPS systems (Snort, Suricata) will flag these. Rate-limited `-T2` or `-T3` reduces but doesn't eliminate detection. |
| **Directory brute-force (gobuster, ffuf)** | **High** | Hundreds/thousands of HTTP 404 responses in rapid succession. WAFs and log analysis tools flag this trivially. |
| **SQL injection testing (sqlmap)** | **High** | Malformed queries with `UNION SELECT`, `OR 1=1`, `SLEEP()` payloads. Any decent WAF (ModSecurity, Cloudflare) will detect and block. |
| **Credential brute-force (hydra)** | **High** | Rapid failed login attempts trigger account lockouts and alerts. |
| **Vulnerability scanning (nuclei)** | **Medium–High** | Template payloads are well-known. WAF signature databases specifically cover nuclei templates. |
| **DNS enumeration** | **Low–Medium** | High volume of DNS queries for non-existent subdomains is detectable via DNS monitoring but rarely alerted on in practice. |
| **OSINT / passive recon** | **Very Low** | WHOIS lookups, cert transparency, Google dorking, Shodan queries generate no traffic to the target. |
| **TLS/SSL scanning (sslyze, testssl)** | **Low** | Multiple TLS handshakes with different cipher offers. Unusual but rarely triggers alerts. |
| **Web crawling (gospider)** | **Medium** | Systematic crawling patterns differ from organic browser traffic. Rate limiting and User-Agent rotation help. |

### Host-Level Detection

| Activity | Detection Risk | Notes |
|----------|---------------|-------|
| **LinPEAS/WinPEAS** | **High** | Reads hundreds of sensitive files, checks SUID bits, enumerates running processes. EDR agents (CrowdStrike, Defender for Endpoint, SentinelOne) will flag this. |
| **Mimikatz** | **Very High** | Detected by virtually every AV/EDR. Signature-detected, behavior-detected, and AMSI-detected on Windows. |
| **Metasploit modules** | **High** | Well-known exploit payloads, Meterpreter beacons, and post-exploitation modules are heavily signatured. |
| **Persistence mechanisms** | **High** | Cron jobs, registry keys, service installations trigger change monitoring. |
| **ARP spoofing / Responder** | **Medium–High** | ARP anomalies detected by monitoring tools. Responder poisoning detected by honeypot/decoy systems. |

### Reducing Detection Footprint

These are **not evasion techniques** — they're operational best practices for authorized testing:

1. **Throttle scan speed** — Use `nmap -T2`, add delays between requests
2. **Target specifically** — Avoid broad /16 scans; test exactly what's in scope
3. **Time your tests** — Coordinate with the blue team during maintenance windows
4. **Use established channels** — Prefer the target's standard ports and protocols
5. **Monitor your impact** — Watch for service degradation and stop if detected
6. **Document everything** — Session JSON logs every command for your report

### Relic's Detection Profile

Relic itself doesn't add obfuscation or evasion features by design. The traffic generated is **identical to running the underlying tools manually** (nmap, sqlmap, etc.). The LLM adds no stealth layer — it simply automates what a human pentester would type.

**What creates network traffic:**
- The VM executing tools against the target (nmap, curl, sqlmap, etc.)

**What does NOT create network traffic:**
- LLM inference — fully local via Ollama (`127.0.0.1:11434`)
- Web UI ↔ API communication — local only (`127.0.0.1:8746`)
- Session management — local disk I/O only

---

## How the Engine Works (Deep Dive)

### The Objective Loop

```python
# Simplified pseudocode of engine.run_objective()

async def run_objective(objective):
    session = get_or_create_session()

    for iteration in range(50):              # Safety cap
        messages = build_chat_context(session, objective)
        llm_response = await llm.chat(messages)

        plan = parse_json_array(llm_response)
        # plan = [{"command": "nmap -sV 10.0.0.5", "description": "..."}]

        if plan is empty:
            break  # LLM says objective is complete

        for task in plan:
            if not is_in_scope(task.command):
                emit(BLOCKED)
                continue

            output = await vm.execute(task.command)  # SSH into VM
            emit(output)
            session.record(task.command, output)

    session.save()
```

### LLM Communication

The client supports two Ollama endpoints:

1. **Chat endpoint** (`/api/chat`) — Used by the engine for multi-turn conversations. Supports `think` mode for enhanced reasoning.
2. **Generate endpoint** (`/api/generate`) — Used for single-shot tasks (reports, error explanations).

If the chat endpoint returns empty content (a known Ollama quirk with some models), Relic automatically falls back to `_chat_via_generate()` which reconstructs the conversation as a flat prompt.

### Thinking Mode

GLM-4.7-Flash and some other models support a `think` parameter that enables chain-of-thought reasoning in a separate field. Relic enables this by default for the planning loop. The thinking output is logged at debug level but not displayed to the user — only the final plan commands are shown.

If thinking mode fails (e.g., on an older Ollama version), the client silently retries without it.

### Event System

The engine broadcasts 5 event types via callbacks (consumed by both the TUI and WebSocket):

| Event | Fields | Purpose |
|-------|--------|---------|
| `LogEvent` | level, message | General status messages |
| `CommandEvent` | command, source | When a command is about to execute (source: `llm` or `user`) |
| `OutputEvent` | text, stream | Command output from the VM |
| `PlanEvent` | tasks[] | LLM's proposed plan for the current iteration |
| `FindingEvent` | finding{} | A discovered vulnerability or noteworthy result |

### Session Persistence

Sessions are stored as JSON files in `~/.relic/sessions/`:

```json
{
  "meta": {
    "id": "a1b2c3d4e5f6",
    "name": "prod-webapp-test",
    "created_at": "2026-03-01T10:00:00Z",
    "target": "example.com",
    "status": "active"
  },
  "history": [
    {
      "timestamp": "2026-03-01T10:01:23Z",
      "source": "llm",
      "command": "nmap -sV -sC example.com",
      "output": "PORT   STATE SERVICE VERSION\n22/tcp open  ssh ...",
      "exit_code": 0,
      "module": "port-scan"
    }
  ],
  "findings": [
    {
      "severity": "medium",
      "title": "SSH version disclosure",
      "description": "OpenSSH 8.9p1 running on port 22",
      "module": "port-scan"
    }
  ]
}
```

---

## API Reference

The FastAPI backend runs on `http://127.0.0.1:8746` with full CORS support.

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/status` | Server status, active model, module count |
| `GET` | `/api/modules` | All 86 modules grouped by category |
| `GET` | `/api/scope` | Current authorized targets and scope config |
| `PUT` | `/api/scope` | Update authorized targets |
| `GET` | `/api/sessions` | List all saved sessions |
| `GET` | `/api/models` | List model presets with installed/active status |
| `PUT` | `/api/model` | Switch the active LLM model |
| `POST` | `/api/objective` | Submit an objective for autonomous execution |
| `POST` | `/api/command` | Execute a single command in the VM |
| `POST` | `/api/scan` | Run a specific module against a target |
| `POST` | `/api/report` | Generate an LLM-written report from findings |
| `POST` | `/api/explain` | Get LLM explanation for an error message |
| `POST` | `/api/stop` | Stop the current objective loop |

### WebSocket

```
ws://127.0.0.1:8746/ws
```

Streams engine events as JSON in real-time. Also accepts `/cmd <command>` messages for direct command execution.

### Example Usage

```bash
# Check status
curl http://127.0.0.1:8746/api/status

# Set target scope
curl -X PUT http://127.0.0.1:8746/api/scope \
  -H "Content-Type: application/json" \
  -d '{"authorized_targets": ["example.com"], "authorization_url": "https://example.com/auth"}'

# Submit objective
curl -X POST http://127.0.0.1:8746/api/objective \
  -H "Content-Type: application/json" \
  -d '{"objective": "Enumerate open ports and services on example.com"}'

# Run a specific module
curl -X POST http://127.0.0.1:8746/api/scan \
  -H "Content-Type: application/json" \
  -d '{"module": "port-scan", "target": "example.com"}'

# Switch model
curl -X PUT http://127.0.0.1:8746/api/model \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5-7b"}'

# Generate report
curl -X POST http://127.0.0.1:8746/api/report
```

---

## Project Structure

```
relic/
├── relic-setup.bat              # One-click Windows setup wizard
├── pyproject.toml               # Package metadata & dependencies
├── config.default.yaml          # Default configuration
├── LICENSE                      # MIT License + security disclaimer
├── README.md                    # This file
├── SECURITY.md                  # Security policy & vulnerability reporting
├── CONTRIBUTING.md              # Contributor guidelines
├── CHANGELOG.md                 # Version history
│
├── docs/                        # Web UI (GitHub Pages)
│   ├── index.html               # Main HTML
│   ├── style.css                # Black & white theme
│   ├── app.js                   # Client-side JavaScript
│   ├── _config.yml              # Jekyll config
│   └── .nojekyll                # Disable Jekyll processing
│
├── src/relic/
│   ├── __init__.py              # Banner, version, disclaimer
│   ├── cli.py                   # Click CLI (relic command)
│   │
│   ├── core/
│   │   ├── config.py            # Pydantic config (YAML + env + defaults)
│   │   ├── session.py           # Session persistence (JSON)
│   │   └── engine.py            # Orchestration loop + scope enforcement
│   │
│   ├── llm/
│   │   ├── ollama_client.py     # Async Ollama client (chat, generate, stream)
│   │   └── prompts.py           # Jinja2 prompt templates
│   │
│   ├── vm/
│   │   └── manager.py           # VM provisioning + SSH execution
│   │
│   ├── modules/
│   │   ├── __init__.py          # Unified module registry (86 modules, 9 categories)
│   │   ├── base.py              # BaseModule abstract class + ModuleResult
│   │   ├── recon.py             # 9 reconnaissance modules
│   │   ├── exploit.py           # 8 exploitation modules
│   │   ├── web.py               # 22 web testing modules
│   │   ├── network.py           # 13 network modules
│   │   ├── osint.py             # 11 OSINT modules
│   │   ├── crypto_ssl.py        # 6 crypto/SSL modules
│   │   ├── post_exploit.py      # 8 post-exploitation modules
│   │   ├── api_testing.py       # 8 API testing modules
│   │   └── reporting.py         # 1 report generation module
│   │
│   ├── ui/
│   │   ├── app.py               # Textual TUI application
│   │   └── theme.py             # Dark theme CSS
│   │
│   └── web/
│       └── api.py               # FastAPI server (port 8746)
│
└── tests/
    ├── test_e2e.py              # End-to-end tests
    ├── test_integration.py      # Integration tests
    ├── test_system.py           # System-level tests
    └── test_tui.py              # TUI interface tests
```

---

## FAQ

### Do I need a GPU?

No. Ollama can run models on CPU-only. With 3B models (Qwen 2.5 3B, Llama 3.2 3B), expect 2–5 tokens/sec on a modern CPU with 8+ GB RAM. A discrete GPU with 4+ GB VRAM dramatically improves speed.

### Does any data leave my machine?

**Only traffic to your authorized targets.** LLM inference is 100% local via Ollama. The Web UI communicates with the local FastAPI server at `127.0.0.1:8746`. No telemetry, no cloud APIs, no analytics.

### Can I use OpenAI / Anthropic / other cloud LLMs?

Not currently. Relic is designed for local-only inference. This is intentional — pentest data (credentials, vulnerabilities, command output) should never leave your machine.

### What operating systems are supported?

- **Windows 10/11** — Full support. One-click setup wizard included.
- **Linux** — Full support via manual installation.
- **macOS** — Works with Ollama for Mac. Use manual installation.

### Is this a replacement for professional pentesting?

No. Relic is an automation tool to assist qualified security professionals. It does not replace human judgment, creative thinking, or deep technical expertise. Always review findings manually and validate results.

### Can the LLM hallucinate commands?

Yes. LLMs can generate incorrect, non-existent, or inappropriate commands. This is mitigated by:
1. **Scope enforcement** — blocks any command targeting unauthorized hosts
2. **VM isolation** — commands run in a throwaway VM, not your host
3. **Human oversight** — all commands and output are logged and visible in real-time
4. **Safety cap** — maximum 50 iterations per objective

### Will the target know they're being scanned?

Almost certainly yes for active scanning (nmap, sqlmap, gobuster, etc.). See the [Detection Considerations](#detection-considerations) section for a detailed breakdown of what is and isn't detectable. Passive OSINT activities (WHOIS, cert transparency, Shodan lookups) do not generate traffic to the target.

### How do I add my own modules?

1. Create a class inheriting from `BaseModule` in the appropriate file under `src/relic/modules/`
2. Implement `run()` (async execution) and `get_commands()` (command list)
3. Add it to the category registry dict at the bottom of that file
4. It's automatically available in both the TUI and Web UI

---

## License

MIT License — see [LICENSE](LICENSE) for full text.

**Additional disclaimer:** This software is intended for authorized security testing and educational purposes only. The authors and contributors accept no responsibility or liability for any misuse.

---

<p align="center">
<b>USE RESPONSIBLY · HACK ETHICALLY · RESPECT THE LAW</b>
</p>
