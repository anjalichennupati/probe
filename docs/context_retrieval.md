# Context Retrieval and LLM Ranking

Probe context retrieval turns a target entity or a set of changed entities into relevant source context. `ContextEngine` resolves the seed entities in a saved graph, traverses graph relationships, ranks the resulting candidates, and assembles source snippets within the requested limits.

## Request and response

Create a `ContextRequest` with `retrieval_mode="target"` and `target_id`, or use `retrieval_mode="change"` with `changed_entity_ids`. `depth` and `max_candidates` limit graph traversal; `max_snippets` and `context_budget` limit assembled source text. The current budget is measured by snippet characters, not model tokens. Set `semantic_ranking=True` to ask the configured LLM to rank candidates; otherwise Probe uses structural fallback scores.

The engine returns a `ContextPackage`. Call `to_response()` to access the typed `ContextResponse`, or `to_json()` to serialize it for a CLI or downstream consumer. Nested response models represent the request, summary, candidates, source locations, and snippet line ranges. The LLM ranking schema is derived from the `CandidateRanking` and `RankingResult` models rather than separately maintained.

The response includes:

- `status`: whether retrieval completed fully or partially.
- `summary`: candidate/snippet counts, budget usage, and whether fallback ranking was used.
- `candidates`: graph entities with distance, discovery path, score, rationale, and source location.
- `snippets`: source text and its line range for selected candidates.
- `omissions`, `unresolved`, and `errors`: entities that could not be included or resolved, and retrieval errors.

## OpenRouter configuration

OpenRouter is the currently supported provider. Provider, model, enabled state, timeout, and retry count are read from `[tool.probe.llm]` in `pyproject.toml`; `PROBE_LLM_PROVIDER`, `PROBE_LLM_MODEL`, `PROBE_LLM_ENABLED`, `PROBE_LLM_TIMEOUT`, and `PROBE_LLM_RETRIES` override those settings. `OPENROUTER_API_KEY` must be set in the environment when LLM ranking is enabled; do not commit the key or put it in `pyproject.toml`.

The default model is `openai/gpt-4o-mini`. The `PROBE_LLM_MODEL` environment variable or the `model` setting selects another OpenRouter model. Timeout, retries, and enabled state can also be configured in the project settings or environment.

## Run the retrieval example

The script loads an **existing saved graph** (by default `.probe/probe/graph.json`) and resolves the target `PythonParser.parse_file`. Build or refresh that graph first if it does not exist or source locations are stale.

```bash
# Structural ranking; does not call OpenRouter.
python scripts/test_context_e2e.py

# LLM ranking; requires OPENROUTER_API_KEY and makes a live request.
python scripts/test_context_e2e.py --semantic-ranking
```

The script prints the serialized response as JSON. With `--semantic-ranking`, it exits unsuccessfully if the request or response validation fails and structural fallback is used; check the warning for the failure type.

This feature ranks context candidates for a retrieval request. It does not yet analyze a Git diff, produce PR review findings, or run as a pre-push hook.
