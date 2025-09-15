"""Schema validation helpers for API responses.

Implements T027: simple validation pipeline that
- validates lists of raw items against Pydantic response models
- performs light extra range/cross-field checks

Keep it small and easy to read.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from dvol_data_ingest.models.api_responses import (
    DVOLApiResponse,
    FundingRatesApiResponse,
    FuturesOHLCVApiResponse,
    OnChainDataApiResponse,
    OptionsSummaryApiResponse,
)

T = TypeVar("T", bound=BaseModel)


@dataclass
class ValidationIssue:
    index: int
    message: str


def _summarize_error(e: ValidationError) -> str:
    parts: list[str] = []
    for err in e.errors():
        loc = ".".join(str(x) for x in err.get("loc", ()))
        msg = err.get("msg", "validation error")
        parts.append(f"{loc}: {msg}")
    return "; ".join(parts) or str(e)


def _extra_checks(model: BaseModel) -> str | None:
    """Return an error message string if an extra check fails, else None."""
    if isinstance(model, OptionsSummaryApiResponse):
        # Keep IV within a sensible range [0, 5] if provided by API docs
        if model.avg_iv > 5:
            return "avg_iv must be <= 5"
    return None


def validate_items(
    items: Iterable[Any], model_type: type[T]
) -> tuple[list[T], list[ValidationIssue]]:
    """Validate a list of raw items against a Pydantic model.

    Returns (valid_models, issues). If an item fails validation or extra
    checks, it is omitted from the valid_models list and an issue is recorded.
    """
    valid: list[T] = []
    issues: list[ValidationIssue] = []
    for idx, item in enumerate(items):
        try:
            model = model_type.model_validate(item)
        except ValidationError as e:
            issues.append(ValidationIssue(index=idx, message=_summarize_error(e)))
            continue
        msg = _extra_checks(model)
        if msg:
            issues.append(ValidationIssue(index=idx, message=msg))
            continue
        valid.append(model)
    return valid, issues


# Convenience wrappers per endpoint -----------------------------------------


def validate_dvol(
    items: Iterable[Any],
) -> tuple[list[DVOLApiResponse], list[ValidationIssue]]:
    return validate_items(items, DVOLApiResponse)


def validate_options(
    items: Iterable[Any],
) -> tuple[list[OptionsSummaryApiResponse], list[ValidationIssue]]:
    return validate_items(items, OptionsSummaryApiResponse)


def validate_futures(
    items: Iterable[Any],
) -> tuple[list[FuturesOHLCVApiResponse], list[ValidationIssue]]:
    return validate_items(items, FuturesOHLCVApiResponse)


def validate_funding(
    items: Iterable[Any],
) -> tuple[list[FundingRatesApiResponse], list[ValidationIssue]]:
    return validate_items(items, FundingRatesApiResponse)


def validate_onchain(
    items: Iterable[Any],
) -> tuple[list[OnChainDataApiResponse], list[ValidationIssue]]:
    return validate_items(items, OnChainDataApiResponse)


__all__ = [
    "ValidationIssue",
    "validate_items",
    "validate_dvol",
    "validate_options",
    "validate_futures",
    "validate_funding",
    "validate_onchain",
]
