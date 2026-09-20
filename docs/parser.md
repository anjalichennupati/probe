# Parser

The parser converts source code into normalized Probe models. It does not build or persist the graph.

## Flow

1. `ProbeProject` owns a `ParserRegistry`.
2. The registry maps a language name to a parser implementation.
3. `detect_language()` determines a language from the file extension.
4. The matching parser returns a `ParseResult`.
5. A `ParseResult` contains nodes, edges, and parse errors.

```text
file path
   ↓
detect_language()
   ↓
ParserRegistry
   ↓
PythonParser
   ↓
ParseResult
```

## Current Python Parser

`PythonParser` uses Python's standard-library `ast` module. No `ast` dependency is required because it ships with Python.

It currently extracts:

- File nodes
- Class nodes
- Function and method nodes
- Containment edges
- Inheritance edges
- Import edges
- Call edges
- Source locations and docstrings where available

## Target Semantics

Edges distinguish resolved graph nodes from symbolic references:

```text
resolved:
target_id = <internal node id>
target_ref = None

unresolved:
target_id = None
target_ref = "sqrt"
```

The parser does not attempt full symbol resolution. That is a separate concern for future work.

## Using the Parser Through Probe

For a single file:

```python
project = probe.init("hello", root="/path/to/repository")
parse_result = project.parse("src/module.py")
```

For the normal end-to-end workflow, use `project.build(path)`. It parses the target and continues into graph building and storage.

## Errors

Syntax and file-read errors are returned in `ParseResult.errors`. The parser logs the file being processed and the resulting node and edge counts.
