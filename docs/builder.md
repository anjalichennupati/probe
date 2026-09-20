# Builder

The builder turns normalized parser output into the in-memory knowledge graph.

## Flow

1. A parser produces a `ParseResult`.
2. `GraphBuilder` adds every `Node`, keyed by its stable `node.id`.
3. The builder calculates a deterministic content hash for every node.
4. The builder validates and adds every `Edge`.
5. The graph creates outgoing and incoming adjacency indexes.
6. The resulting `Graph` is returned to the project facade and storage layer.

```text
ParseResult
   ↓
GraphBuilder
   ↓
Graph
   ├── nodes
   ├── edges
   ├── outgoing index
   ├── incoming index
   └── node hashes
```

## Graph API

```python
graph.get_node(node_id)
graph.get_nodes()
graph.get_edges()
graph.get_outgoing(node_id)
graph.get_incoming(node_id)
graph.get_node_hashes()
```

The graph stores unresolved references on their edge without creating fake nodes. For example, a call to `print` has `target_id=None` and `target_ref="print"`.

## Validation

The builder rejects:

- Duplicate node IDs
- Edges whose `source_id` is not present
- Edges whose non-null `target_id` is not present

Unresolved edges are valid when they use `target_ref`.

## Node Hashing

`NodeContent` represents the meaningful persisted state of a node. Its deterministic hash includes identity, type, names, file path, parent, source span, docstring, and metadata.

It does not include timestamps, commit IDs, or other run-specific values. Unchanged node content therefore produces the same hash across runs.

## End-to-End Build

```python
import probe

project = probe.init("hello", root="/path/to/repository")
graph = project.build("/path/to/repository/src/module.py")
```

Passing a directory makes the project walk supported files beneath that directory, combine their parse results, and build one current graph.
