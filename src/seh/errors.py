from __future__ import annotations


class SehError(RuntimeError):
    """Base class for expected, user-facing SEH failures."""


class GitError(SehError):
    """Raised when repository discovery or a Git operation fails."""


class StorageError(SehError):
    """Raised when the graph store cannot be read or updated."""


class StateError(StorageError):
    """Raised when the index is absent, stale, or belongs to another repository."""


class SchemaError(StorageError):
    """Raised when a graph database uses an unsupported schema."""


class IndexingError(SehError):
    """Raised when a language adapter cannot build a reliable index."""
