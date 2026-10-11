import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_every_runtime_and_dev_dependency_is_pinned_exactly() -> None:
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    requirements = list(config["project"]["dependencies"])
    for group in config["dependency-groups"].values():
        requirements.extend(group)
    assert requirements
    unpinned = [r for r in requirements if "==" not in r]
    assert unpinned == []
