"""
Prompt templates for Relic's LLM interactions.

Uses Jinja2 for flexible templating. Each template is designed to guide
the local LLM into producing structured, actionable pentesting output.
"""

from __future__ import annotations

from jinja2 import Environment, BaseLoader

_env = Environment(loader=BaseLoader(), autoescape=False)

# ---------------------------------------------------------------------------
# System prompt — sets the persona for the entire session
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = _env.from_string("""\
You are Relic, an expert penetration testing AI assistant operating inside an \
isolated virtual machine. You have full access to the VM and all installed \
security tools. Your role is to assist a licensed penetration tester in \
conducting an authorized security assessment.

AUTHORIZED SCOPE (STRICT):
  Target: {{ scope }}
  Authorization: {{ authorization_url }}
  You MUST confine ALL commands to the exact target above.
  Do NOT scan, enumerate, or interact with any other host, path, or subdomain
  — even on the same domain. Anything outside the exact target URL is
  OUT OF SCOPE and must be refused.

Rules:
- Always output your next actions as a JSON array of objects: \
[{"command": "...", "description": "..."}]
- If the objective is complete, return an empty array: []
- Be precise and methodical. Prefer targeted commands over broad scans.
- Interpret tool output carefully and adapt your strategy.
- Note any findings (open ports, vulnerabilities, credentials, etc.) clearly.
- When uncertain, explain your reasoning before proposing commands.
- NEVER target hosts or paths outside the authorized scope above.

Operating system: {{ os }}
Available tools: {{ tools | join(', ') }}
""")


# ---------------------------------------------------------------------------
# Objective planning
# ---------------------------------------------------------------------------

OBJECTIVE_PLAN = _env.from_string("""\
OBJECTIVE: {{ objective }}

{% if context -%}
CONTEXT FROM PREVIOUS WORK:
{{ context }}
{% endif -%}

Based on the objective above, provide a structured penetration testing plan \
as a JSON array. Each step should contain a "command" to execute and a \
"description" explaining why.

Respond ONLY with the JSON array.
""")


# ---------------------------------------------------------------------------
# Output analysis
# ---------------------------------------------------------------------------

ANALYZE_OUTPUT = _env.from_string("""\
The following command was executed in the target VM:

COMMAND: {{ command }}
EXIT CODE: {{ exit_code }}

OUTPUT:
```
{{ output | truncate(4000) }}
```

Analyze this output in the context of our objective: {{ objective }}

Provide:
1. Key findings (if any)
2. Next recommended commands as a JSON array [{"command": "...", "description": "..."}]
   OR an empty array [] if the objective is met.
""")


# ---------------------------------------------------------------------------
# Recon summary
# ---------------------------------------------------------------------------

RECON_SUMMARY = _env.from_string("""\
Summarize the reconnaissance data collected so far:

{% for entry in history -%}
[{{ entry.source }}] $ {{ entry.command }}
{{ entry.output | truncate(1000) }}
---
{% endfor %}

Provide a concise summary listing:
- Discovered hosts and services
- Open ports and versions
- Potential attack vectors
- Recommended next steps

Format your response as structured text, NOT JSON.
""")


# ---------------------------------------------------------------------------
# Exploit suggestion
# ---------------------------------------------------------------------------

EXPLOIT_SUGGEST = _env.from_string("""\
Based on the following findings, suggest possible exploits:

FINDINGS:
{{ findings }}

Available exploit tools: {{ tools | join(', ') }}

Return a JSON array of exploit attempts: \
[{"command": "...", "description": "...", "risk": "low|medium|high"}]
Only suggest exploits appropriate for the identified services and versions.
""")


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

REPORT_GENERATE = _env.from_string("""\
Generate a professional penetration testing report based on the session data.

TARGET: {{ target }}
SCOPE: {{ scope }}
SESSION DURATION: {{ duration }}

FINDINGS:
{% for f in findings -%}
- {{ f.title }}: {{ f.description }} (severity: {{ f.severity }})
{% endfor %}

COMMAND HISTORY ({{ history | length }} commands executed):
{% for entry in history[:50] -%}
$ {{ entry.command }}
{% endfor %}

Write the report in Markdown format with these sections:
1. Executive Summary
2. Scope & Methodology
3. Findings (sorted by severity)
4. Recommendations
5. Technical Details
""")


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def render(template, **kwargs: object) -> str:
    """Render a Jinja2 template with the given variables."""
    return template.render(**kwargs).strip()
