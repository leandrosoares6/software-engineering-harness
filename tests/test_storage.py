from pathlib import Path

from seh.models import Edge, EdgeKind, Node, NodeKind
from seh.storage import GraphStore


def test_store_roundtrip(tmp_path: Path):
    store = GraphStore(tmp_path / "seh.db")
    store.init()
    nodes = [
        Node("f1", NodeKind.FILE, "UserService.java", "src/UserService.java"),
        Node("c1", NodeKind.CLASS, "UserService", "src/UserService.java", 3),
    ]
    edges = [Edge("f1", "c1", EdgeKind.DECLARES)]
    store.replace_graph(nodes, edges)

    matches = store.search_nodes("UserService")
    assert len(matches) == 2
    neighbors = store.neighbors("f1")
    assert len(neighbors) == 1
    assert neighbors[0]["name"] == "UserService"
