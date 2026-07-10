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
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

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
└── docs/               # Documentation
```

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
