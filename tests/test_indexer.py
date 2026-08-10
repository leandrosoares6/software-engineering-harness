import subprocess
from pathlib import Path

from seh.indexer import index_repository
from seh.models import EdgeKind, NodeKind


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_indexes_java_symbols(tmp_path: Path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    source = tmp_path / "src/main/java/example"
    source.mkdir(parents=True)
    (source / "UserService.java").write_text(
        """package example;\npublic class UserService {\n  public String findUser(String id) { return id; }\n}\n""",
        encoding="utf-8",
    )
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "init")

    nodes, edges = index_repository(tmp_path)
    assert any(n.kind == NodeKind.CLASS and n.name == "UserService" for n in nodes)
    assert any(n.kind == NodeKind.METHOD and n.name == "findUser" for n in nodes)
    assert any(e.kind == EdgeKind.DECLARES for e in edges)
