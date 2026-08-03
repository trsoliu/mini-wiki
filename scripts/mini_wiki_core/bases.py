"""Deterministic native Obsidian Bases views over Mini-Wiki Properties."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from mini_wiki_core.validation import ValidationIssue

SUPPORTED_VIEW_TYPES = frozenset({"table", "cards", "list", "map"})
SUPPORTED_ROOT_KEYS = frozenset({"filters", "formulas", "properties", "summaries", "views"})
SUPPORTED_VIEW_KEYS = frozenset(
    {
        "type",
        "name",
        "limit",
        "groupBy",
        "filters",
        "order",
        "summaries",
    }
)

PROPERTY_LABELS = {
    "file.name": "Document",
    "note.type": "Type",
    "note.domain": "Domain",
    "note.status": "Status",
    "note.sources": "Sources",
    "note.source_count": "Source count",
    "note.freshness": "Freshness",
    "note.quality": "Quality",
    "note.backlink_count": "Backlinks",
    "note.orphan": "Orphan",
}


def _table(name: str, filters: list[str], order: list[str]) -> dict[str, Any]:
    properties = {
        property_name: {"displayName": PROPERTY_LABELS[property_name]}
        for property_name in order
        if property_name in PROPERTY_LABELS
    }
    return {
        "filters": {"and": ['file.ext == "md"', *filters]},
        "properties": properties,
        "views": [{"type": "table", "name": name, "order": order}],
    }


def render_default_bases() -> dict[Path, str]:
    """Render the four official-shape Base files shipped with every v3 Vault."""
    definitions = {
        "modules.base": _table(
            "Modules",
            ['type == "module"'],
            [
                "file.name",
                "note.domain",
                "note.status",
                "note.freshness",
                "note.quality",
                "note.backlink_count",
            ],
        ),
        "sources.base": _table(
            "Sources",
            ["source_count > 0"],
            [
                "file.name",
                "note.sources",
                "note.source_count",
                "note.freshness",
            ],
        ),
        "quality.base": _table(
            "Quality",
            ["quality != null"],
            [
                "file.name",
                "note.type",
                "note.quality",
                "note.freshness",
                "note.backlink_count",
            ],
        ),
        "orphans.base": _table(
            "Orphans",
            ["orphan == true"],
            [
                "file.name",
                "note.type",
                "note.domain",
                "note.sources",
                "note.orphan",
            ],
        ),
    }
    return {
        Path("wiki/views") / name: yaml.safe_dump(definition, allow_unicode=True, sort_keys=False)
        for name, definition in sorted(definitions.items())
    }


def _filter_errors(value: Any, location: str) -> list[str]:
    if isinstance(value, str):
        return [] if value.strip() else [f"{location} filter expression must not be empty"]
    if not isinstance(value, dict) or len(value) != 1:
        return [f"{location} filters must be a string or one and/or/not mapping"]
    operator, children = next(iter(value.items()))
    if operator not in {"and", "or", "not"}:
        return [f"{location} uses unsupported filter operator: {operator}"]
    if not isinstance(children, list) or not children:
        return [f"{location}.{operator} must be a non-empty list"]
    errors: list[str] = []
    for index, child in enumerate(children):
        errors.extend(_filter_errors(child, f"{location}.{operator}[{index}]"))
    return errors


def _mapping_of_strings(value: Any, location: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, dict):
        return [f"{location} must be a mapping"]
    errors: list[str] = []
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            errors.append(f"{location} keys and values must be strings")
    return errors


def validate_base(path: Path, text: str) -> list[ValidationIssue]:
    """Validate the shared official Base schema used by Mini-Wiki."""
    from mini_wiki_core.validation import ValidationIssue

    location = path.as_posix()
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [ValidationIssue("INVALID_BASE", "error", location, f"Base YAML is invalid: {exc}")]
    errors: list[str] = []
    if not isinstance(value, dict):
        errors.append("Base root must be a mapping")
    else:
        unknown = sorted(set(value) - SUPPORTED_ROOT_KEYS)
        if unknown:
            errors.append(f"Base root has unsupported fields: {', '.join(unknown)}")
        if "filters" in value:
            errors.extend(_filter_errors(value["filters"], "filters"))
        errors.extend(_mapping_of_strings(value.get("formulas"), "formulas"))
        errors.extend(_mapping_of_strings(value.get("summaries"), "summaries"))

        properties = value.get("properties")
        if properties is not None:
            if not isinstance(properties, dict):
                errors.append("properties must be a mapping")
            else:
                for property_name, settings in properties.items():
                    if not isinstance(property_name, str) or not isinstance(settings, dict):
                        errors.append("properties entries must map string names to settings")
                    elif "displayName" in settings and not isinstance(settings["displayName"], str):
                        errors.append(f"properties.{property_name}.displayName must be a string")

        views = value.get("views")
        if not isinstance(views, list) or not views:
            errors.append("views must be a non-empty list")
        else:
            for index, view in enumerate(views):
                if not isinstance(view, dict):
                    errors.append(f"views[{index}] must be a mapping")
                    continue
                unknown_view = sorted(set(view) - SUPPORTED_VIEW_KEYS)
                if unknown_view:
                    errors.append(f"views[{index}] has unsupported fields: {', '.join(unknown_view)}")
                if view.get("type") not in SUPPORTED_VIEW_TYPES:
                    errors.append(f"views[{index}].type is unsupported: {view.get('type')}")
                if not isinstance(view.get("name"), str) or not view["name"].strip():
                    errors.append(f"views[{index}].name must be a non-empty string")
                order = view.get("order")
                if order is not None and (
                    not isinstance(order, list) or not all(isinstance(item, str) for item in order)
                ):
                    errors.append(f"views[{index}].order must be a list of property names")
                if "filters" in view:
                    errors.extend(_filter_errors(view["filters"], f"views[{index}].filters"))
                limit = view.get("limit")
                if limit is not None and (not isinstance(limit, int) or limit < 1):
                    errors.append(f"views[{index}].limit must be a positive integer")
                errors.extend(_mapping_of_strings(view.get("summaries"), f"views[{index}].summaries"))
                group_by = view.get("groupBy")
                if group_by is not None:
                    if not isinstance(group_by, dict) or not isinstance(group_by.get("property"), str):
                        errors.append(f"views[{index}].groupBy requires a string property")
                    elif group_by.get("direction") not in {None, "ASC", "DESC"}:
                        errors.append(f"views[{index}].groupBy direction must be ASC or DESC")

    return [ValidationIssue("INVALID_BASE", "error", location, error) for error in errors]
