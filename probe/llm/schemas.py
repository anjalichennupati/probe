from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from typing import Any, Union, get_args, get_origin, get_type_hints


@dataclass(frozen=True)
class CandidateRanking:
    """Single ranking for one candidate identifier."""

    candidate_id: str = field(metadata={"enum_from": "allowed_ids"})
    score: float = field(metadata={"minimum": 0, "maximum": 1})
    rationale: str

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id).strip()
        if not candidate_id:
            raise ValueError("candidate_id must be a non-empty string.")
        if not 0.0 <= float(self.score) <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0.")
        rationale = str(self.rationale).strip()
        if not rationale:
            raise ValueError("rationale must be a non-empty string.")
        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "score", float(self.score))
        object.__setattr__(self, "rationale", rationale)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> CandidateRanking:
        if not isinstance(payload, Mapping):
            raise ValueError("Candidate entry must be a mapping.")
        if "candidate_id" not in payload:
            raise ValueError("Candidate entry is missing 'candidate_id'.")
        if "score" not in payload:
            raise ValueError("Candidate entry is missing 'score'.")
        if "rationale" not in payload:
            raise ValueError("Candidate entry is missing 'rationale'.")
        return cls(
            candidate_id=str(payload["candidate_id"]),
            score=float(payload["score"]),
            rationale=str(payload["rationale"]),
        )


@dataclass(frozen=True)
class RankingResult:
    """Structured output for future relevance-ranking tasks."""

    candidates: list[CandidateRanking] = field(
        default_factory=list,
        metadata={"required": True},
    )
    missing_candidates: list[str] = field(
        default_factory=list,
        metadata={"exclude_from_schema": True},
    )

    @classmethod
    def json_schema(cls, *, allowed_ids: Iterable[str] = ()) -> dict[str, Any]:
        """Build the provider response schema from this model's dataclass fields."""
        return _dataclass_json_schema(cls, context={"allowed_ids": list(allowed_ids)})

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        allowed_ids: Iterable[str] | None = None,
    ) -> RankingResult:
        if not isinstance(payload, Mapping):
            raise ValueError("Ranking payload must be a mapping.")

        raw_candidates = payload.get("candidates")
        if not isinstance(raw_candidates, list):
            raise ValueError("Ranking payload must include a 'candidates' list.")

        validated: list[CandidateRanking] = []
        seen_ids: set[str] = set()
        allowed = {str(candidate_id) for candidate_id in (allowed_ids or [])}

        for item in raw_candidates:
            candidate = CandidateRanking.from_mapping(item)
            if allowed and candidate.candidate_id not in allowed:
                raise ValueError(f"Unknown candidate ID: {candidate.candidate_id}")
            if candidate.candidate_id in seen_ids:
                raise ValueError(f"Duplicate candidate ID: {candidate.candidate_id}")
            seen_ids.add(candidate.candidate_id)
            validated.append(candidate)

        missing = sorted(allowed - seen_ids) if allowed else []
        if missing:
            raise ValueError(f"missing required candidate IDs: {missing}")

        return cls(candidates=validated, missing_candidates=missing)

    def __iter__(self):
        return iter(self.candidates)


def _dataclass_json_schema(
    model: type[Any],
    *,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    if not is_dataclass(model):
        raise TypeError(f"{model.__name__} must be a dataclass to generate a JSON schema.")

    properties: dict[str, Any] = {}
    required: list[str] = []
    type_hints = get_type_hints(model)
    for model_field in fields(model):
        metadata = model_field.metadata
        if metadata.get("exclude_from_schema"):
            continue

        field_type = type_hints[model_field.name]
        origin = get_origin(field_type)
        args = get_args(field_type)
        if origin is list:
            item_type = args[0]
            item_schema = _type_json_schema(item_type, context=context)
            property_schema = {"type": "array", "items": item_schema}
        else:
            property_schema = _type_json_schema(field_type, context=context)

        if "minimum" in metadata:
            property_schema["minimum"] = metadata["minimum"]
        if "maximum" in metadata:
            property_schema["maximum"] = metadata["maximum"]
        enum_from = metadata.get("enum_from")
        if enum_from:
            property_schema["enum"] = list(context[enum_from])
        properties[model_field.name] = property_schema

        is_required = (
            metadata.get("required", False)
            or model_field.default is MISSING
            and model_field.default_factory is MISSING
        )
        if is_required:
            required.append(model_field.name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _type_json_schema(value_type: Any, *, context: Mapping[str, Any]) -> dict[str, Any]:
    origin = get_origin(value_type)
    args = get_args(value_type)
    if origin is Union and type(None) in args:
        non_null_type = next(arg for arg in args if arg is not type(None))
        return _type_json_schema(non_null_type, context=context)
    if value_type is str:
        return {"type": "string"}
    if value_type is float or value_type is int:
        return {"type": "number" if value_type is float else "integer"}
    if value_type is bool:
        return {"type": "boolean"}
    if is_dataclass(value_type):
        return _dataclass_json_schema(value_type, context=context)
    raise TypeError(f"Unsupported JSON schema type: {value_type!r}")


__all__ = ["CandidateRanking", "RankingResult"]
