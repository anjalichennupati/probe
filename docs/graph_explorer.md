# Graph Explorer

The Probe Graph Explorer is a developer-facing visualization for inspecting a persisted Probe graph. It is intentionally small: the UI is a view over Probe's existing graph, not a replacement graph model and not a second parser.

## What It Does

The explorer:

- Loads one named project from `.probe/<project_name>/graph.json`.
- Displays semantic code entities such as files, classes, functions, and methods.
- Draws directed relationships such as `CONTAINS`, `CALLS`, `IMPORTS`, and `INHERITS`.
- Shows unresolved references as clearly marked reference endpoints.
- Exposes node source location, metadata, docstring, hash, and relationships on selection.
- Provides search, node filtering, relationship filtering, pan, zoom, dragging, and local focus.

The UI does not turn the graph into a tree. File and module context remains available through node labels and source paths, while semantic edges connect the actual code entities.

## Data Flow

```text
.probe/<project_name>/graph.json
                ↓
        GraphExplorer
                ↓
       visualization adapter
                ↓
       interactive browser view
```

The explorer reads the current persisted graph through the existing `FileStorage` and `Graph` APIs. It does not duplicate parser or builder logic.

## Starting the Explorer

The project name is configured in `scripts/run_graph_explorer.py`. Running that script loads the corresponding project storage:

```text
project name: probe
storage: /Users/anjalichennupati/ML/probe/.probe/probe/
```

The script starts the explorer at:

```text
http://127.0.0.1:8000
```

The explorer must be built from the project before it can display current data. The normal sequence is:

1. Define a project name and repository root.
2. Build the target file or repository into `.probe/<project_name>/`.
3. Run the explorer script for that same project name.
4. Open the local browser URL.

## Graph Surface

The main canvas shows:

- Colored entity points for classes, functions, methods, files, and modules.
- Dashed reference points for unresolved targets.
- Directed lines with arrowheads.
- Relationship labels when a selected node is involved.
- Faded unrelated nodes when a node is selected.

The initial view is intentionally dense for repository inspection, but the controls make a smaller local view easy to create.

## Search Controls

The search field is shared by two independent filters:

### Nodes

With **Nodes** enabled, the query matches:

- Entity name
- Qualified name
- Source file path

For example, searching `pyth` with Nodes enabled isolates Python-related entities such as `PythonParser` and `python_parser.py`.

### Relationships

With **Relationships** enabled, the query matches:

- Relationship type
- Unresolved target reference

For example:

```text
inh
```

shows inheritance relationships, including:

```text
PythonParser ──INHERITS──> BaseParser
```

The `BaseParser` endpoint is visually marked as unresolved because the current parser has a symbolic reference rather than a resolved internal node ID. This is a UI representation only; the underlying edge remains unchanged.

### Combining Filters

The two buttons can be used in four modes:

| Nodes | Relationships | Result |
| --- | --- | --- |
| off | off | Full graph |
| on | off | Node search |
| off | on | Relationship search |
| on | on | Combined node and relationship search |

The **Reset view** button clears the query, filters, selection, pan, and zoom.

## Interaction

- Drag a node or its label to move it.
- Drag empty canvas space to pan the graph.
- Use the wheel or trackpad to zoom.
- Select a node to highlight immediate relationships.
- Use **Focus selection** to show the selected node's local neighborhood.
- Select a node to open the bottom inspection drawer.

The inspection drawer stays hidden until a node is selected, so it does not compress the graph during normal exploration.

## Node Inspection

Selecting a node exposes:

- Entity kind
- Qualified name
- Source file
- Source span
- Deterministic content hash
- Docstring, when available
- Incoming relationships
- Outgoing relationships
- Metadata

Hashes are the same values used by storage for node-version tracking. They are not generated separately by the UI.

## Screenshots

### Main Explorer View

![Main Probe Graph Explorer view](assets/graph-explorer/image%20copy%203.png)

### Node Filtering

![Probe Graph Explorer node filtering](assets/graph-explorer/image%20copy.png)

### Relationship Filtering

![Probe Graph Explorer contains relationship filtering](assets/graph-explorer/image%20copy%202.png)

### Inheritance Filtering

![Probe Graph Explorer inheritance filtering](assets/graph-explorer/image.png)

The inheritance view makes the `PythonParser` to `BaseParser` relationship directly visible.