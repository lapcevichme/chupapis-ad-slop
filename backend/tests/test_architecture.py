import ast
from pathlib import Path


def test_layer_dependencies_do_not_cross_boundaries():
    root = Path(__file__).resolve().parents[1] / "app"
    forbidden = {
        "domain": (
            "fastapi",
            "sqlalchemy",
            "pydantic",
            "app.db",
            "app.api",
            "app.service",
            "app.infra",
        ),
        "service": ("fastapi", "app.api"),
        "infra": ("fastapi", "app.api", "app.service", "app.db"),
        "db": ("fastapi", "app.api", "app.service", "app.infra"),
    }
    violations = []
    for layer, prefixes in forbidden.items():
        for path in (root / layer).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                imports = []
                if isinstance(node, ast.ImportFrom):
                    imports = [node.module or ""]
                elif isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                for module in imports:
                    if any(
                        module == prefix or module.startswith(prefix + ".") for prefix in prefixes
                    ):
                        violations.append(f"{path.relative_to(root)}:{node.lineno}: {module}")
    for path in (root / "api").rglob("*.py"):
        text = path.read_text()
        assert "from sqlalchemy" not in text
        assert "app.db.models" not in text
    assert violations == []
