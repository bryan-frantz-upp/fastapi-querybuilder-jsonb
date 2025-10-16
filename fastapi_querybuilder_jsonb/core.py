# app/filters/core.py

from fastapi import HTTPException
from sqlalchemy.orm import RelationshipProperty, aliased
from sqlalchemy.sql import Select, and_
from sqlalchemy import cast, Integer, DateTime, String
from typing import Any, Optional, Dict, Tuple
import json
from .operators import LOGICAL_OPERATORS, COMPARISON_OPERATORS
from .utils import is_jsonb_column


def apply_jsonb_path_filter(column, path: str, operator: str, operand: Any) -> Any:
    """
    Apply a filter to a JSONB column using path notation.

    Args:
        column: The JSONB column
        path: Dot-separated path (e.g., "address.city")
        operator: The operator (e.g., "$eq", "$gt")
        operand: The value to compare against

    Returns:
        SQLAlchemy expression
    """
    from sqlalchemy.sql import operators as sql_operators
    from sqlalchemy.dialects.postgresql import JSONB

    # Navigate the path
    expr = column
    for key in path.split("."):
        expr = expr[key]

    # Get the text value - handle both JSONB and JSON
    # For JSONB (PostgreSQL), use .astext
    # For JSON (SQLite, MySQL), the subscript already returns a scalar-like expression
    if isinstance(column.type, JSONB):
        leaf = expr.astext
    else:
        # For regular JSON columns, we need to extract as text
        # SQLite JSON uses json_extract which returns text by default
        leaf = expr

    # Map operators to their functions
    operator_map = {
        "$eq": lambda leaf, val: sql_operators.eq(leaf, str(val)),
        "$ne": lambda leaf, val: sql_operators.ne(leaf, str(val)),
        "$gt": lambda leaf, val: sql_operators.gt(cast(leaf, Integer), val),
        "$gte": lambda leaf, val: sql_operators.ge(cast(leaf, Integer), val),
        "$lt": lambda leaf, val: sql_operators.lt(cast(leaf, Integer), val),
        "$lte": lambda leaf, val: sql_operators.le(cast(leaf, Integer), val),
        "$in": lambda leaf, val: sql_operators.in_op(leaf, [str(v) for v in val]),
        "$contains": lambda leaf, val: cast(leaf, String).ilike(f"%{val}%"),
        "$startswith": lambda leaf, val: cast(leaf, String).ilike(f"{val}%"),
        "$endswith": lambda leaf, val: cast(leaf, String).ilike(f"%{val}"),
        "$isempty": lambda leaf, val: leaf.is_(None),
        "$isnotempty": lambda leaf, val: leaf.is_not(None),
    }

    if operator not in operator_map:
        raise HTTPException(
            status_code=400,
            detail=f"Operator '{operator}' is not supported for JSONB path filtering"
        )

    # Apply the operator (some operators don't use operand)
    if operator in ["$isempty", "$isnotempty"]:
        return operator_map[operator](leaf, None)
    else:
        return operator_map[operator](leaf, operand)


def resolve_and_join_column(model, nested_keys: list[str], query: Select, joins: dict) -> Tuple[Any, Select]:
    current_model = model
    alias = None

    for i, attr in enumerate(nested_keys):
        relationship = getattr(current_model, attr, None)

        if relationship is not None and isinstance(relationship.property, RelationshipProperty):
            related_model = relationship.property.mapper.class_
            if related_model not in joins:
                alias = aliased(related_model)
                joins[related_model] = alias
                query = query.outerjoin(alias, getattr(current_model, attr))
            else:
                alias = joins[related_model]

            current_model = alias
        else:
            if hasattr(current_model, attr):
                return getattr(current_model, attr), query
            raise HTTPException(
                status_code=400,
                detail=f"Invalid filter key: {'.'.join(nested_keys)}. "
                f"Could not resolve attribute '{attr}' in model '{current_model.__name__}'."
            )
    raise HTTPException(
        status_code=400,
        detail=f"Could not resolve relationship for {'.'.join(nested_keys)}."
    )


def parse_filters(model, filters: dict, query: Select) -> Tuple[Optional[Any], Select]:
    expressions = []
    joins = {}

    if not isinstance(filters, dict):
        raise HTTPException(
            status_code=400, detail="Filters must be a dictionary")

    for key, value in filters.items():
        if key in LOGICAL_OPERATORS:
            if not isinstance(value, list):
                raise HTTPException(
                    status_code=400, detail=f"Logical operator '{key}' must be a list")
            sub_expressions = []
            for sub_filter in value:
                sub_expr, query = parse_filters(model, sub_filter, query)
                if sub_expr is not None:
                    sub_expressions.append(sub_expr)
            if sub_expressions:
                expressions.append(LOGICAL_OPERATORS[key](*sub_expressions))

        elif isinstance(value, dict):
            nested_keys = key.split(".")

            # Check if the first key is a JSONB column
            first_attr = nested_keys[0]
            if hasattr(model, first_attr):
                first_column = getattr(model, first_attr)
                # Check if it's a JSONB column and we have a nested path
                if len(nested_keys) > 1 and hasattr(first_column, 'type') and is_jsonb_column(first_column):
                    # This is a JSONB path query (e.g., "metadata.key")
                    jsonb_column = first_column
                    jsonb_path = ".".join(nested_keys[1:])  # Everything after the column name

                    for operator, operand in value.items():
                        try:
                            expressions.append(
                                apply_jsonb_path_filter(jsonb_column, jsonb_path, operator, operand)
                            )
                        except Exception as e:
                            raise HTTPException(
                                status_code=400, detail=f"Error filtering JSONB path '{key}': {e}")
                    continue  # Skip the normal resolution logic

            # Normal column or relationship resolution
            column, query = resolve_and_join_column(
                model, nested_keys, query, joins)
            for operator, operand in value.items():
                if operator not in COMPARISON_OPERATORS:
                    raise HTTPException(
                        status_code=400, detail=f"Unknown operator '{operator}' for field '{key}'")
                try:
                    if operator in ["$isempty", "$isnotempty"]:
                        expressions.append(
                            COMPARISON_OPERATORS[operator](column))
                    else:
                        expressions.append(
                            COMPARISON_OPERATORS[operator](column, operand))
                except Exception as e:
                    raise HTTPException(
                        status_code=400, detail=f"Error filtering '{key}': {e}")
        else:
            raise HTTPException(
                status_code=400, detail=f"Invalid filter format for key '{key}': {value}")

    return and_(*expressions) if expressions else None, query


def parse_filter_query(filters: Optional[str]) -> Optional[Dict]:
    if not filters:
        return None
    try:
        parsed = json.loads(filters)
        if not isinstance(parsed, dict):
            raise ValueError("Filters must be a JSON object")
        return parsed
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid filter JSON: {e}")
