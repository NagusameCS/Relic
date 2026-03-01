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

> **Automated penetration testing powered by local LLMs, executed within isolated virtual machines.**

---

## ⚠ IMPORTANT — RESPONSIBLE USE DISCLAIMER

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
║     laws worldwide. Violations carry severe criminal penalties including     ║
║     imprisonment and substantial fines.                                      ║
║                                                                              ║
║  3. You accept FULL RESPONSIBILITY for your actions. The developers and     ║
║     contributors of Relic bear NO LIABILITY for any misuse of this tool.    ║
║                                                                              ║
║  4. This tool should ONLY be used against systems you OWN or have explicit  ║
║     written permission to test, such as personal lab environments, CTF      ║
║     challenges, bug bounty programs, or contracted pentest engagements.     ║
║                                                                              ║
║  5. All testing must be conducted within ISOLATED, VIRTUALIZED              ║
║     ENVIRONMENTS to prevent unintended impact on production systems.        ║
║                                                                              ║
║  USE RESPONSIBLY  ·  HACK ETHICALLY  ·  RESPECT THE LAW                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

**By downloading, installing, or using Relic, you agree to these terms.**

---

## What is Relic?

Relic is a terminal-based penetration testing automation framework that combines:

- **Local LLMs** (via [Ollama](https://ollama.com)) — for intelligent planning, command generation, output analysis, and adaptive strategy
- **Virtualized environments** (Vagrant/VirtualBox) — all commands execute inside isolated VMs, never on your host
- **Modular pentesting workflows** — recon, exploitation, and reporting modules that can be run standalone or orchestrated by the LLM
- **Dark-themed TUI** — a pure black terminal interface built with [Textual](https://textual.textualize.io) and [Rich](https://rich.readthedocs.io)

The LLM operates as an autonomous pentesting assistant: you provide a high-level objective (e.g., *"enumerate and exploit vulnerabilities on 10.0.0.5"*), and Relic iteratively plans commands, executes them in the VM, analyses the output, and adapts its approach.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    RELIC TUI (Textual)                   │
│  ┌──────────┐  ┌──────────────────────────────────────┐ │
│  │ Sidebar  │  │           Output Log                 │ │
│  │ ──────── │  │  $ nmap -sV 10.0.0.5                │ │
│  │ Session  │  │  PORT   STATE SERVICE VERSION        │ │
│  │ VM: ● ON │  │  22/tcp open  ssh     OpenSSH 8.9   │ │
│  │ LLM: ● ON│  │  80/tcp open  http    Apache 2.4    │ │
│  │ ──────── │  │  ◆ FINDING [INFO]: open_port 22/tcp │ │
│  │ Modules  │  │  🤖 Analyzing output...              │ │
│  │  recon   │  └──────────────────────────────────────┘ │
│  │  exploit │  ┌──────────────────────────────────────┐ │
│  │  report  │  │ > Enter objective or /help ...       │ │
│  └──────────┘  └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   ┌──────────┐     ┌──────────────┐     ┌──────────────┐
   │ Sessions │     │  LLM Engine  │     │  VM Manager  │
   │  (JSON)  │     │  (Ollama)    │     │  (Vagrant)   │
   └──────────┘     └──────────────┘     └──────┬───────┘
                                                 │ SSH
                                          ┌──────▼───────┐
                                          │  Target VM   │
                                          │ (Kali Linux) │
                                          │  nmap, sqlmap│
                                          │  hydra, msf  │
                                          └──────────────┘
```

---

## Prerequisites

- **Python 3.10+**
- **[Ollama](https://ollama.com)** — running locally with at least one model pulled
- **[Vagrant](https://www.vagrantup.com/)** + **[VirtualBox](https://www.virtualbox.org/)** — for VM provisioning
- A pentesting VM image (default: `kalilinux/rolling`)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/relic.git
cd relic

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate       # Windows

# Install Relic
pip install -e .

# Pull a model in Ollama
ollama pull mistral
```

---

## Quick Start

```bash
# Launch Relic (shows disclaimer, then TUI)
relic

# Skip disclaimer (for scripted use — you still accept responsibility)
relic --no-disclaimer

# Show version
relic --version

# View current configuration
relic config --show
```

### Inside the TUI

| Action | Command |
|--------|---------|
| Get help | `/help` |
| Start a VM | `/vm start` |
| New session | `/session my-pentest` |
| Run recon module | `/module port-scan 10.0.0.5` |
| Execute command in VM | `!nmap -sV 10.0.0.5` |
| Send objective to LLM | `Enumerate all services on 10.0.0.5 and identify vulnerabilities` |
| Generate report | `/report` |
| Stop LLM execution | `Escape` |
| Quit | `Ctrl+C` |

---

## Configuration

Copy the default config and customize:

```bash
mkdir -p ~/.relic
cp config.default.yaml ~/.relic/config.yaml
```

Key settings in `~/.relic/config.yaml`:

```yaml
llm:
  provider: ollama
  base_url: "http://localhost:11434"
  model: "mistral"            # or any model you've pulled
  temperature: 0.7

vm:
  provider: vagrant
  base_image: "kalilinux/rolling"
  memory: 4096
  cpus: 2
  snapshot_on_start: true     # auto-snapshot for easy reset
```

Environment variable overrides use `RELIC_` prefix with `__` as separator:

```bash
export RELIC_LLM__MODEL=llama3
export RELIC_VM__MEMORY=8192
```

---

## Modules

### Reconnaissance
| Module | Description |
|--------|-------------|
| `port-scan` | Nmap service/version/OS detection |
| `subdomain-enum` | Subdomain discovery + HTTP probing |
| `dns-recon` | DNS enumeration + zone transfer attempts |
| `web-recon` | Directory brute-force, tech detection, Nikto |

### Exploitation
| Module | Description |
|--------|-------------|
| `sqli` | SQL injection via sqlmap |
| `brute-force` | Credential brute-forcing via Hydra |
| `metasploit` | MSF exploit automation |
| `password-crack` | Offline hash cracking with John |

### Reporting
| Module | Description |
|--------|-------------|
| `report` | Generate Markdown pentest report |

---

## Project Structure

```
relic/
├── pyproject.toml              # Project metadata & dependencies
├── requirements.txt
├── config.default.yaml         # Default configuration
├── README.md
└── src/
    └── relic/
        ├── __init__.py         # Banner, version, disclaimer
        ├── cli.py              # Click CLI entry point
        ├── core/
        │   ├── config.py       # Pydantic config with YAML + env loading
        │   ├── session.py      # Session & history management
        │   └── engine.py       # LLM ↔ VM orchestration loop
        ├── llm/
        │   ├── ollama_client.py  # Async Ollama HTTP client
        │   └── prompts.py      # Jinja2 prompt templates
        ├── vm/
        │   └── manager.py      # VM provisioning + SSH execution
        ├── modules/
        │   ├── base.py         # Abstract module interface
        │   ├── recon.py        # Reconnaissance modules
        │   ├── exploit.py      # Exploitation modules
        │   └── reporting.py    # Report generation
        └── ui/
            ├── theme.py        # RELIC_CSS dark theme
            └── app.py          # Textual TUI application
```

---

## How the Engine Works

1. **User provides objective** → e.g., *"Find and exploit vulnerabilities on 10.0.0.5"*
2. **Engine sends context + objective to LLM** → using structured prompt templates
3. **LLM returns a plan** → JSON array of `{command, description}` steps
4. **Engine executes each command in the VM** → via SSH (Paramiko)
5. **Output is captured and fed back to the LLM** → for analysis and next-step planning
6. **Loop repeats** → until the LLM returns an empty plan (objective complete) or the user stops
7. **Findings are recorded** → in the session JSON, available for report generation

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Reminder

**This tool exists for authorized security testing and education only.** Always obtain written permission before testing any system. Always work within isolated environments. Always respect the law.
