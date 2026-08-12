from __future__ import annotations

from argparse import Namespace
import json
import sqlite3
import sys

import pytest

from conftest import git
from seh.capability_cli import cmd_validate
from seh.cli import build_parser, cmd_index, cmd_init, cmd_inspect, cmd_neighbors, main
from seh.errors import IndexingError, StateError


def test_read_command_does_not_create_state(committed_repo):
    with pytest.raises(StateError):
        cmd_inspect(Namespace(repo=str(committed_repo), query="anything"))

    assert not (committed_repo / ".seh").exists()


def test_index_works_in_unborn_repository_and_detects_staleness(git_repo, capsys):
    source = git_repo / "thing.py"
    source.write_text("class Thing:\n    pass\n", encoding="utf-8")
    git(git_repo, "add", "thing.py")

    assert cmd_index(Namespace(repo=str(git_repo))) == 0
    assert "@ unborn" in capsys.readouterr().out
    assert cmd_inspect(Namespace(repo=str(git_repo), query="Thing")) == 0
    source.write_text("class Thing:\n    changed = True\n", encoding="utf-8")
    with pytest.raises(StateError, match="stale"):
        cmd_inspect(Namespace(repo=str(git_repo), query="Thing"))


def test_neighbors_fails_on_ambiguity_and_supports_id(git_repo, capsys):
    first = git_repo / "a" / "service.py"
    second = git_repo / "b" / "service.py"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("class Service:\n    pass\n", encoding="utf-8")
    second.write_text("class Service:\n    pass\n", encoding="utf-8")
    git(git_repo, "add", ".")
    cmd_index(Namespace(repo=str(git_repo)))
    capsys.readouterr()

    args = Namespace(repo=str(git_repo), query="Service", node_id=None)
    assert cmd_neighbors(args) == 2
    candidates = capsys.readouterr().err
    assert "a.service.Service" in candidates and "b.service.Service" in candidates

    from seh.config import SehConfig
    from seh.storage import GraphStore

    store = GraphStore(SehConfig.for_repo(git_repo).db_path)
    node_id = next(
        row["id"]
        for row in store.search_nodes("a.service.Service")
        if row["qualified_name"] == "a.service.Service"
    )
    assert cmd_neighbors(Namespace(repo=str(git_repo), query=None, node_id=node_id)) == 0


def test_init_is_idempotent_and_uses_canonical_root(committed_repo, capsys):
    nested = committed_repo / "nested"
    nested.mkdir()

    args = Namespace(repo=str(nested))
    assert cmd_init(args) == 0
    assert cmd_init(args) == 0
    config_path = committed_repo / ".seh" / "config.json"
    assert json.loads(config_path.read_text(encoding="utf-8"))["repository"] == committed_repo.name
    assert "Initialized SEH" in capsys.readouterr().out


def test_inspect_and_neighbors_report_missing_matches(git_repo, capsys):
    source = git_repo / "unique.py"
    source.write_text("class Unique:\n    pass\n", encoding="utf-8")
    git(git_repo, "add", "unique.py")
    cmd_index(Namespace(repo=str(git_repo)))
    capsys.readouterr()

    assert cmd_inspect(Namespace(repo=str(git_repo), query="Absent")) == 1
    assert cmd_neighbors(Namespace(repo=str(git_repo), query="Absent", node_id=None)) == 1
    assert cmd_neighbors(Namespace(repo=str(git_repo), query=None, node_id="missing")) == 1
    assert "No matching" in capsys.readouterr().out


def test_index_reports_parser_diagnostics(git_repo, capsys):
    source = git_repo / "broken.py"
    source.write_text("def broken(:\n", encoding="utf-8")
    git(git_repo, "add", "broken.py")

    assert cmd_index(Namespace(repo=str(git_repo))) == 0
    assert "syntax_error=1" in capsys.readouterr().err


def test_read_rejects_index_created_by_another_indexer_version(git_repo, capsys):
    source = git_repo / "thing.py"
    source.write_text("class Thing:\n    pass\n", encoding="utf-8")
    git(git_repo, "add", "thing.py")
    cmd_index(Namespace(repo=str(git_repo)))
    capsys.readouterr()

    from seh.config import SehConfig

    with sqlite3.connect(SehConfig.for_repo(git_repo).db_path) as connection:
        connection.execute("UPDATE metadata SET indexer_version = '0.0.0'")

    with pytest.raises(StateError, match="indexer version"):
        cmd_inspect(Namespace(repo=str(git_repo), query="Thing"))


def test_index_aborts_if_repository_changes_during_scan(git_repo, monkeypatch):
    fingerprints = iter(["before", "after"])
    monkeypatch.setattr("seh.cli.state_fingerprint", lambda root: next(fingerprints))
    monkeypatch.setattr(
        "seh.cli.index_repository",
        lambda root: type("Result", (), {"nodes": [], "edges": [], "diagnostics": []})(),
    )

    with pytest.raises(IndexingError, match="changed while indexing"):
        cmd_index(Namespace(repo=str(git_repo)))


def test_argument_parser_requires_deterministic_neighbor_selection():
    parser = build_parser()

    by_query = parser.parse_args(["neighbors", "Thing"])
    by_id = parser.parse_args(["neighbors", "--id", "class:123"])

    assert by_query.query == "Thing" and by_query.node_id is None
    assert by_id.query is None and by_id.node_id == "class:123"


def test_argument_parser_exposes_nested_capability_validate():
    parser = build_parser()
    args = parser.parse_args(["capability", "validate", "./candidate"])
    allowed = parser.parse_args(
        ["capability", "validate", "./candidate", "--allow-verification"]
    )

    assert args.candidate == "./candidate"
    assert args.allow_verification is False
    assert allowed.allow_verification is True
    assert args.handler is cmd_validate


def test_main_converts_expected_errors_to_exit_code_two(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["seh", "inspect", "Thing", "--repo", "/not/a/repository"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 2
    assert "error:" in capsys.readouterr().err
