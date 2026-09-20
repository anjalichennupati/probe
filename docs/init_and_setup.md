# Initialization and Setup

This guide explains how a project is defined, where Probe stores its data, and how the setup and build examples fit together.

## 1. Define the Project

Probe starts with two pieces of information:

- `project_name`: the name of the Probe project and its storage folder.
- `root`: the repository or project directory being analyzed.

The project name does not replace the repository root. It selects an isolated storage directory beneath it:

```text
<repository-root>/.probe/<project_name>/
```

For example:

```text
/Users/anjalichennupati/ML/probe/.probe/trial1/
```

A different project name creates a different storage area in the same repository:

```text
/Users/anjalichennupati/ML/probe/.probe/trial1/
/Users/anjalichennupati/ML/probe/.probe/hello/
```

## 2. Run the First Example

From the repository root, run:

```bash
python3 examples/01_probe_build.py
```

The example defines the project name as `hello`, uses the repository root as the project root, builds its configured target file, and prints the final locations.

Representative output:

```text
Built graph: 5 nodes, 9 edges
Input path: /Users/anjalichennupati/ML/probe/tests/test_setup.py
Probe storage: /Users/anjalichennupati/ML/probe/.probe/hello
```

The first example initializes the project and builds the configured source file.

## 3. Build a Graph Separately

After initialization, the build step receives the exact file or repository directory to analyze:

```bash
python3 examples/01_probe_build.py
```

The build flow is:

1. Resolve the requested input path.
2. Detect the language from the file extension.
3. Parse the file or supported files below the directory.
4. Normalize parser output into nodes and edges.
5. Build the in-memory knowledge graph.
6. Persist the latest graph under the project's `.probe` directory.
7. Record node hashes, the current Git commit when available, and the current UTC timestamp.

## 4. Storage Result

After a project has been initialized and built, its storage has this shape:

```text
<repository-root>/.probe/<project_name>/
├── graph.json
├── metadata.json
└── history/
    ├── <node_id>.json
    └── ...
```

The storage is project-scoped. Running the same build with a different project name writes to that name's directory instead of overwriting the existing project's state.

## 5. Run the Flow

The intended sequence is:

```text
initialize project
        ↓
build an explicit file or repository path
        ↓
inspect the current graph
        ↓
read the persisted graph and node history
```

Initialization and graph building are separate on purpose. Defining a project should not decide which source path is analyzed.
