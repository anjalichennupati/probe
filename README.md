# Probe

Probe is a language-agnostic code intelligence SDK whose central goal is to turn source code into a persistent knowledge graph.

## Goal

Probe creates a structured view of a codebase so that files, classes, functions, methods, relationships, and source changes can be understood as connected data. The graph is designed to become the foundation for future code navigation, dependency analysis, and impact analysis.

## Architecture Flow

```text
project definition
   ↓
source file or repository path
   ↓
language detection and parser
   ↓
normalized nodes, edges, and parse results
   ↓
graph builder
   ↓
current in-memory knowledge graph
   ↓
project-scoped file storage
   ↓
current graph plus node history
```

Project initialization defines the repository root and a project name. The project name creates an isolated storage area below the repository's `.probe` directory. Building is a separate operation that receives the exact file or repository path to analyze.

## Main Responsibilities

### Parser

The parser reads source code and identifies meaningful program structures and relationships. Its output is normalized so the rest of Probe does not need to know the details of a particular language parser.

### Builder

The builder turns normalized parser output into the current knowledge graph. It keeps stable node IDs, validates relationships, maintains graph indexes, and calculates deterministic node hashes.

### Storage

Storage writes the latest graph and node history as human-readable JSON. Each project has its own storage directory. A node receives a new history entry only when its meaningful content changes. Git commit identifiers and UTC timestamps provide the context for each recorded version.

### Graph Explorer

The Graph Explorer is a small interactive view over a named project's persisted graph. It shows semantic entities and relationships, supports node and relationship filtering, and exposes unresolved references such as `BaseParser` without changing the underlying graph.

<img width="1280" height="638" alt="image" src="https://github.com/user-attachments/assets/9744d126-affc-47f9-8c27-ea754d438222" />

The explorer reads `.probe/<project_name>/graph.json`; it does not rebuild a second graph for the UI.

## Uses

Probe is intended to support:

- Codebase structure mapping
- Dependency and relationship inspection
- Source-level knowledge graph construction
- Change tracking through node versions
- Future impact analysis and code navigation
- Language-specific parsing behind a language-agnostic graph model

## Example Output

Running the current first example builds the project named `hello` from its configured target file. The resulting data is stored at:

```text
/Users/anjalichennupati/ML/probe/.probe/hello/
```

Representative output:

```text
Built graph: 5 nodes, 9 edges
Input path: /Users/anjalichennupati/ML/probe/tests/test_setup.py
Probe storage: /Users/anjalichennupati/ML/probe/.probe/hello
```

Changing the project name creates a separate project directory under `.probe`, keeping each project's graph and history isolated.

## Documentation

- [Initialization and setup](docs/init_and_setup.md)
- [Parser](docs/parser.md)
- [Builder](docs/builder.md)
- [Storage](docs/storage.md)
- [Graph Explorer](docs/graph_explorer.md)
