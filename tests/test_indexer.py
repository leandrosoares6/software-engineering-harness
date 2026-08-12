from __future__ import annotations

from pathlib import Path

from conftest import git
from seh.indexer import index_repository
from seh.models import EdgeKind, NodeKind


def write_python(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_indexes_python_modules_symbols_signatures_and_nested_classes(git_repo: Path):
    write_python(git_repo, "src/app/__init__.py", "")
    write_python(git_repo, "src/app/services/__init__.py", "")
    write_python(
        git_repo,
        "src/app/services/users.py",
        '''"class Phantom: pass"
# def also_phantom(): pass
CONSTANT = "def hidden(): pass"

class UserService:
    class State:
        pass

    def find(self, user_id: str, *, active: bool = True) -> str | None:
        return user_id

    async def refresh(self, *names: str) -> None:
        return None

def build_service(name: str = "default") -> UserService:
    return UserService()
''',
    )
    git(git_repo, "add", ".")

    result = index_repository(git_repo)
    symbols = {(node.kind, node.qualified_name, node.signature) for node in result.nodes}

    assert (NodeKind.MODULE, "app.services.users", None) in symbols
    assert (NodeKind.CLASS, "app.services.users.UserService", None) in symbols
    assert (NodeKind.CLASS, "app.services.users.UserService.State", None) in symbols
    assert (
        NodeKind.METHOD,
        "app.services.users.UserService.find",
        "(self, user_id: str, *, active: bool=True) -> str | None",
    ) in symbols
    assert (
        NodeKind.METHOD,
        "app.services.users.UserService.refresh",
        "(self, *names: str) -> None",
    ) in symbols
    assert (
        NodeKind.FUNCTION,
        "app.services.users.build_service",
        "(name: str='default') -> UserService",
    ) in symbols
    assert all("Phantom" not in (node.qualified_name or "") for node in result.nodes)


def test_resolves_aliased_import_for_inheritance_without_picking_homonym(git_repo: Path):
    write_python(git_repo, "src/app/__init__.py", "")
    write_python(git_repo, "src/app/a.py", "class Service: pass\n")
    write_python(git_repo, "src/app/b.py", "class Service: pass\n")
    write_python(
        git_repo,
        "src/app/client.py",
        "from app.a import Service as BaseService\nclass Client(BaseService): pass\n",
    )
    git(git_repo, "add", ".")

    result = index_repository(git_repo)
    nodes = {node.qualified_name: node for node in result.nodes}
    extends = [edge for edge in result.edges if edge.kind == EdgeKind.EXTENDS]

    assert any(
        edge.source == nodes["app.client.Client"].id
        and edge.target == nodes["app.a.Service"].id
        for edge in extends
    )
    assert not any(edge.target == nodes["app.b.Service"].id for edge in extends)


def test_resolves_relative_imports_and_records_internal_module_imports(git_repo: Path):
    write_python(git_repo, "pkg/__init__.py", "")
    write_python(git_repo, "pkg/base.py", "class Base: pass\n")
    write_python(git_repo, "pkg/helpers.py", "def help_me(): pass\n")
    write_python(
        git_repo,
        "pkg/child.py",
        "from .base import Base\nimport pkg.helpers as helpers\nclass Child(Base): pass\n",
    )
    git(git_repo, "add", ".")

    result = index_repository(git_repo)
    nodes = {node.qualified_name: node for node in result.nodes}
    imports = [edge for edge in result.edges if edge.kind == EdgeKind.IMPORTS]

    child_file = next(node for node in result.nodes if node.path == "pkg/child.py" and node.kind == NodeKind.FILE)
    assert {edge.target for edge in imports if edge.source == child_file.id} == {
        nodes["pkg.base"].id,
        nodes["pkg.helpers"].id,
    }
    assert any(
        edge.kind == EdgeKind.EXTENDS
        and edge.source == nodes["pkg.child.Child"].id
        and edge.target == nodes["pkg.base.Base"].id
        for edge in result.edges
    )


def test_resolves_relative_submodule_import_from_package_initializer(git_repo: Path):
    write_python(git_repo, "pkg/__init__.py", "from . import helpers\n")
    write_python(git_repo, "pkg/helpers.py", "def help_me(): pass\n")
    git(git_repo, "add", ".")

    result = index_repository(git_repo)
    nodes = {node.qualified_name: node for node in result.nodes}
    package_file = next(
        node
        for node in result.nodes
        if node.path == "pkg/__init__.py" and node.kind == NodeKind.FILE
    )

    assert any(
        edge.kind == EdgeKind.IMPORTS
        and edge.source == package_file.id
        and edge.target == nodes["pkg.helpers"].id
        for edge in result.edges
    )


def test_invalid_python_keeps_file_node_and_omits_semantics(git_repo: Path):
    write_python(git_repo, "broken.py", "def broken(:\n")
    git(git_repo, "add", ".")

    result = index_repository(git_repo)

    assert any(node.path == "broken.py" and node.kind == NodeKind.FILE for node in result.nodes)
    assert not any(node.qualified_name == "broken" and node.kind == NodeKind.MODULE for node in result.nodes)
    assert [(item.kind, item.path, item.line) for item in result.diagnostics] == [
        ("syntax_error", "broken.py", 1)
    ]


def test_reports_unreadable_python_as_diagnostic(git_repo: Path):
    path = git_repo / "invalid.py"
    path.write_bytes(b"\xff\xfe")
    git(git_repo, "add", "invalid.py")

    result = index_repository(git_repo)

    assert result.diagnostics[0].kind == "read_error"


def test_external_and_wildcard_imports_never_create_speculative_edges(git_repo: Path):
    write_python(
        git_repo,
        "uses_external.py",
        "import unavailable\nfrom external import Missing\nfrom somewhere import *\nclass Local(Missing): pass\n",
    )
    git(git_repo, "add", ".")

    result = index_repository(git_repo)

    assert {diagnostic.kind for diagnostic in result.diagnostics} == {
        "unresolved_import",
        "unsupported_import",
        "unresolved_reference",
    }
    assert not any(edge.kind in {EdgeKind.IMPORTS, EdgeKind.EXTENDS} for edge in result.edges)


def test_test_file_is_classified_without_changing_module_identity(git_repo: Path):
    write_python(git_repo, "tests/test_users.py", "def test_user(): pass\n")
    git(git_repo, "add", ".")

    result = index_repository(git_repo)

    assert any(node.kind == NodeKind.TEST and node.path == "tests/test_users.py" for node in result.nodes)
    assert any(node.kind == NodeKind.MODULE and node.qualified_name == "tests.test_users" for node in result.nodes)
