# Contributing to Relic

Thanks for your interest in contributing. Relic is an open-source pentesting automation framework — contributions that improve its reliability, safety, and module coverage are welcome.

## Code of Conduct

- Be respectful and constructive
- This project is for **authorized security testing only** — do not submit contributions designed to bypass scope enforcement or enable unauthorized access
- Follow responsible disclosure practices for any vulnerabilities found

## Getting Started

### Development Setup

```bash
git clone https://github.com/NagusameCS/Relic.git
cd Relic

python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows

# Install with dev + web dependencies
pip install -e ".[dev,web]"

# Verify
python -c "from relic.modules import module_count; print(module_count())"
```

### Running Tests

```bash
pytest -v
```

## How to Contribute

### Adding a New Module

1. Identify which category your module belongs to (`recon`, `exploit`, `web`, `network`, `osint`, `crypto`, `post-exploit`, `api`, `reporting`)
2. Open the corresponding file in `src/relic/modules/` (e.g., `recon.py` for reconnaissance)
3. Create a class inheriting from `BaseModule`:

```python
class MyNewModule(BaseModule):
    name = "my-new-module"
    description = "What this module does"
    category = "recon"

    async def run(self, engine: "Engine", **kwargs) -> ModuleResult:
        target = kwargs.get("target", "")
        commands = self.get_commands(target=target)

        output_parts = []
        for cmd_info in commands:
            result = await engine.run_single_command(cmd_info["command"])
            output_parts.append(result)

        return ModuleResult(
            module=self.name,
            success=True,
            output="\n".join(output_parts),
            findings=self._parse_findings(output_parts),
        )

    def get_commands(self, **kwargs) -> list[dict[str, str]]:
        target = kwargs.get("target", "")
        return [
            {"command": f"tool --option {target}", "description": "Run the tool"},
        ]
```

4. Add it to the registry dict at the bottom of the file:

```python
RECON_MODULES["my-new-module"] = MyNewModule
```

5. It will automatically appear in the Web UI, TUI, and API.

### Bug Fixes

- Open an issue first describing the bug
- Reference the issue number in your PR
- Include a test case if applicable

### Documentation

- README improvements, typo fixes, and clarifications are always welcome
- If you add a module, update the module table in README.md

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes
4. Run tests (`pytest -v`)
5. Commit with a descriptive message (`git commit -m "feat: add XYZ module"`)
6. Push and open a PR

### Commit Message Format

```
type: short description

Longer explanation if needed.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## What We're Looking For

- New modules for tools not yet covered
- Improved finding extraction / parsing in existing modules
- Better error handling
- Test coverage improvements
- Documentation
- Performance optimizations for the LLM client

## What We Will NOT Accept

- Features designed to bypass scope enforcement
- Evasion or anti-detection capabilities
- Cloud LLM integrations (the tool is local-only by design)
- Obfuscation of network traffic
- Anything that facilitates unauthorized access to systems
