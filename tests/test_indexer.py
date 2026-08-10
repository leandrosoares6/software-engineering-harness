from __future__ import annotations

from pathlib import Path

from conftest import git
from seh.indexer import index_repository
from seh.models import EdgeKind, NodeKind


def write_java(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_indexes_modern_java_symbols_without_comments_or_strings(git_repo: Path):
    write_java(
        git_repo,
        "src/main/java/example/UserService.java",
        """package example;
// public class Phantom {}
public record User(String id) {}
public class UserService {
  String text = "class AlsoPhantom {}";
  public UserService() {}
  @Deprecated public String findUser(String id) { return id; }
  public String findUser(long id) { return Long.toString(id); }
  enum Status { ACTIVE }
}
""",
    )
    git(git_repo, "add", ".")

    result = index_repository(git_repo)
    symbols = {(node.kind, node.qualified_name, node.signature) for node in result.nodes}

    assert (NodeKind.RECORD, "example.User", None) in symbols
    assert (NodeKind.CLASS, "example.UserService", None) in symbols
    assert (NodeKind.ENUM, "example.UserService.Status", None) in symbols
    assert (NodeKind.CONSTRUCTOR, "example.UserService#<init>()", "()") in symbols
    assert (NodeKind.METHOD, "example.UserService#findUser(String)", "(String)") in symbols
    assert (NodeKind.METHOD, "example.UserService#findUser(long)", "(long)") in symbols
    assert all("Phantom" not in (node.qualified_name or "") for node in result.nodes)


def test_resolves_same_named_types_by_package_and_explicit_import(git_repo: Path):
    write_java(git_repo, "src/a/Service.java", "package a; public class Service {}\n")
    write_java(git_repo, "src/b/Service.java", "package b; public class Service {}\n")
    write_java(
        git_repo,
        "src/client/Client.java",
        "package client; import a.Service; public class Client extends Service {}\n",
    )
    git(git_repo, "add", ".")

    result = index_repository(git_repo)
    nodes = {node.qualified_name: node for node in result.nodes}
    extends = [edge for edge in result.edges if edge.kind == EdgeKind.EXTENDS]

    assert any(
        edge.source == nodes["client.Client"].id and edge.target == nodes["a.Service"].id
        for edge in extends
    )
    assert not any(
        edge.source == nodes["client.Client"].id and edge.target == nodes["b.Service"].id
        for edge in extends
    )


def test_explicit_import_precedes_same_package_candidate(git_repo: Path):
    write_java(git_repo, "src/a/Service.java", "package a; public class Service {}\n")
    write_java(git_repo, "src/client/Service.java", "package client; public class Service {}\n")
    write_java(
        git_repo,
        "src/client/Client.java",
        "package client; import a.Service; public class Client extends Service {}\n",
    )
    git(git_repo, "add", ".")

    result = index_repository(git_repo)
    nodes = {node.qualified_name: node for node in result.nodes}
    extends = [edge for edge in result.edges if edge.kind == EdgeKind.EXTENDS]

    assert any(
        edge.source == nodes["client.Client"].id and edge.target == nodes["a.Service"].id
        for edge in extends
    )


def test_skips_semantics_and_reports_invalid_java(git_repo: Path):
    write_java(git_repo, "src/Broken.java", "public class Broken { public void nope( { }\n")
    git(git_repo, "add", ".")

    result = index_repository(git_repo)

    assert any(node.path == "src/Broken.java" and node.kind == NodeKind.FILE for node in result.nodes)
    assert not any(node.qualified_name == "Broken" for node in result.nodes)
    assert result.diagnostics


def test_resolves_interfaces_and_wildcard_imports(git_repo: Path):
    write_java(git_repo, "src/api/Base.java", "package api; public interface Base {}\n")
    write_java(git_repo, "src/api/Marker.java", "package api; public interface Marker {}\n")
    write_java(
        git_repo,
        "src/impl/Implementation.java",
        "package impl; import api.*; public class Implementation implements Base, Marker {}\n",
    )
    git(git_repo, "add", ".")

    result = index_repository(git_repo)
    nodes = {node.qualified_name: node for node in result.nodes}
    implementations = [edge for edge in result.edges if edge.kind == EdgeKind.IMPLEMENTS]

    assert {edge.target for edge in implementations} == {
        nodes["api.Base"].id,
        nodes["api.Marker"].id,
    }


def test_reports_unreadable_java_as_diagnostic(git_repo: Path):
    path = git_repo / "InvalidUtf8.java"
    path.write_bytes(b"\xff\xfe")
    git(git_repo, "add", "InvalidUtf8.java")

    result = index_repository(git_repo)

    assert result.diagnostics[0].kind == "read_error"


def test_reports_external_and_static_imports_without_speculative_edges(git_repo: Path):
    write_java(
        git_repo,
        "src/UsesExternal.java",
        """import java.util.List;
import static java.util.Collections.emptyList;
public class UsesExternal {}
""",
    )
    git(git_repo, "add", ".")

    result = index_repository(git_repo)

    assert {diagnostic.kind for diagnostic in result.diagnostics} == {
        "unresolved_import",
        "unsupported_import",
    }
    assert not any(edge.kind == EdgeKind.IMPORTS for edge in result.edges)
