# Contributing to Cyberfox

Thank you for your interest in contributing to Cyberfox! This guide covers everything you need to know.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- pip or uv

### Development Setup

```bash
# Clone the repository
git clone https://github.com/Sarthak5-t/Cyberfox.git
cd Cyberfox

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/
```

---

## Project Structure

```
cyberfox/
├── agent/              # Core agent logic
├── cyberfox_cli/       # CLI interface
├── plugins/
│   └── ares/           # Cybersecurity plugin
├── skills/             # Agent skills
├── tests/              # Test suite
├── website/            # Documentation site (Docusaurus)
└── web/                # Web dashboard frontend
```

---

## Domain Guides (`project_info/`)

The project is divided into three contribution domains, each with a detailed
implementation guide under [`project_info/`](./project_info/):

| Domain | Guide | What it covers |
|---|---|---|
| **Web Development** | [`project_info/web_development.md`](./project_info/web_development.md) | `web/` SPA, `ui-tui/`, `cyberfox_cli/web_server.py`, themes, i18n, dashboard auth |
| **AI / ML** | [`project_info/ai_ml.md`](./project_info/ai_ml.md) | `run_agent.py`, `agent/` runtime, `plugins/model-providers/`, tool-use, context/memory, delegation |
| **Cybersecurity** | [`project_info/cybersec.md`](./project_info/cybersec.md) | `plugins/ares/` (Ares pentest plugin), safety layer, gateway adapters, MCP server |

Pick the guide that matches the area you are working in before you start.

---

## Team Workflow (Fork & Pull Request)

This repository uses a **fork-and-PR** model. The `main` branch is
**protected** — no one (including the owner) can push directly to it. All
changes land via Pull Requests that require at least one approving review.

### For team members

1. **Fork** the repo on GitHub (button at `https://github.com/Sarthak5-t/Cyberfox`).
2. **Clone your fork:**
   ```bash
   git clone https://github.com/<your-username>/Cyberfox.git
   cd Cyberfox
   ```
3. **Link the upstream repo** so you can stay in sync:
   ```bash
   git remote add upstream https://github.com/Sarthak5-t/Cyberfox.git
   ```
4. **Create a feature branch** off `main`:
   ```bash
   git checkout -b feature/my-change
   ```
5. **Make your changes**, then sync with upstream before pushing:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
6. **Commit** (see Commit Messages below) and **push to your fork:**
   ```bash
   git push origin feature/my-change
   ```
7. **Open a Pull Request** on GitHub:
   - base = `Sarthak5-t/Cyberfox:main`
   - compare = `<your-username>:feature/my-change`
   - Fill in the PR template.
8. **Address review comments**, then the maintainer merges.

### Staying in sync

```bash
git fetch upstream
git rebase upstream/main        # or: git merge upstream/main
```

### Notes

- Keep PRs small and focused (one logical change per PR).
- Rebase onto the latest `main` before requesting review to avoid conflicts.
- The maintainer (`Sarthak5-t`) is the only one who can merge to `main`.
- Never commit to `main` on your fork and open a PR from it — always use a
  feature branch.

---

## Contribution Guidelines

### 1. Code Style

- Follow PEP 8 for Python code
- Use type hints
- Write docstrings for public functions
- Keep functions focused and small

### 2. Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for good test coverage

```bash
pytest tests/                    # Run all tests
pytest tests/test_specific.py    # Run specific test
pytest --cov=cyberfox            # Check coverage
```

### 3. Commit Messages

Use clear, descriptive commit messages:

```
feat: add new SQLMap integration
fix: resolve scope validation bug
docs: update installation guide
refactor: simplify tool registration
```

### 4. Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Adding New Tools

### 1. Create Tool Module

```python
# plugins/ares/tools/scanning/my_tool.py

from plugins.ares.tools.base import check_binary, run_command, json_result

TOOLSET = "ares_scanning"

def _handle(args: dict, **kw) -> str:
    target = args.get("target", "")
    if not check_binary("my_tool"):
        return json_result(False, error="my_tool not found on PATH")
    
    result = run_command(f"my_tool {target}")
    return json_result(True, data={"output": result.stdout})

SCHEMA = {
    "name": "my_tool_scan",
    "description": "Description of what the tool does",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Target to scan"},
        },
        "required": ["target"],
    },
}

def register_tools(ctx) -> None:
    ctx.register_tool(
        name="my_tool_scan",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🔍",
    )
```

### 2. Register in `__init__.py`

```python
# plugins/ares/__init__.py

from plugins.ares.tools.scanning import my_tool

# Add to _TOOL_MODULES list
_TOOL_MODULES = [
    # ... existing tools ...
    my_tool,
]
```

### 3. Update plugin.yaml

```yaml
# plugins/ares/plugin.yaml
provides_tools:
  # ... existing tools ...
  - my_tool_scan
```

---

## Adding New Skills

### 1. Create Skill Directory

```bash
mkdir -p skills/ares/my_skill
```

### 2. Create SKILL.md

```markdown
# My Skill

## Objective
Description of what this skill accomplishes.

## Methodology
1. Step one
2. Step two
3. Step three

## Tools Used
- tool1: Purpose
- tool2: Purpose

## References
- Reference material
```

---

## Security Considerations

### Scope Validation

All tools must validate targets against the authorized scope:

```python
from plugins.ares.safety.scope_validator import check_scope

if not check_scope(target):
    return json_result(False, error="Target not in authorized scope")
```

### Approval Gates

Dangerous operations require user approval:

```python
# The approval gate automatically prompts for:
# - Exploitation tools
# - Credential attacks
# - Lateral movement
```

### Audit Trail

All actions are logged automatically via the audit trail hook.

---

## Reporting Issues

### Bug Reports

Use the GitHub issue template with:

- Description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details

### Feature Requests

Open an issue with:

- Description of the feature
- Use case
- Proposed implementation (optional)

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

Open an issue or reach out to the maintainers.
