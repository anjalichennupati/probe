# Storage

Probe uses `FileStorage` for human-readable, file-based persistence. It does not use SQLite, Neo4j, or a server.

## Location

Storage is scoped by project name:

```text
/path/to/repository/.probe/<project_name>/
├── graph.json
├── metadata.json
└── history/
    ├── <node_id>.json
    └── ...
```

This means two project names in the same repository have separate state:

```text
.probe/hello/
.probe/trial1/
```

## Files

### `graph.json`

Contains the latest graph state:

```json
{
  "nodes": [],
  "edges": []
}
```

### `metadata.json`

Contains storage metadata, including the integer `schema_version`.

### `history/<node_id>.json`

Contains chronological versions for one node:

```json
{
  "node_id": "abc123",
  "versions": [
    {
      "hash": "H1",
      "commit_id": "<git commit or null>",
      "probed_at": "2026-09-21T12:00:00+00:00",
      "previous_hash": null
    }
  ]
}
```

## Versioning Steps

1. The builder computes the current node hash.
2. Storage loads the node's latest history.
3. If the latest hash is unchanged, no version is added.
4. If the hash changed, storage appends a new version.
5. The new version's `previous_hash` points to the immediately previous hash.
6. `commit_id` comes from `git rev-parse HEAD`, or is `null` outside Git.
7. `probed_at` is the current UTC timestamp.

## Atomic Writes

Important JSON files are written using this sequence:

```text
temporary file in the same directory
   ↓
write JSON
   ↓
flush and fsync
   ↓
atomic replace
```

This applies to graph, metadata, and node history files.

## Loading and Errors

- Missing storage can be initialized with `FileStorage.initialize()`.
- Missing history for a node returns an empty `NodeHistory`.
- Malformed JSON raises `CorruptStorageError`.
- `load_graph()` reconstructs `Node`, `Edge`, and `Graph` objects through explicit serializers.

The normal application entry point is:

```python
project = probe.init("hello", root="/path/to/repository")
graph = project.build("/path/to/file.py")
```
