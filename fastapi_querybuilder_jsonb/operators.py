# app/filters/operators.py

from sqlalchemy import and_, or_, JSON, cast, Integer, DateTime
from sqlalchemy.sql import operators
from sqlalchemy.dialects.postgresql import JSONB
from .utils import _adjust_date_range

LOGICAL_OPERATORS = {
    "$and": and_,
    "$or": or_
}


def _eq_operator(column, value):
    if value == "":
        return column.is_(None)
    adjusted_value, is_range = _adjust_date_range(column, value, "$eq")
    if adjusted_value is not None and is_range is not None:
        return adjusted_value if is_range else column == adjusted_value
    return column == value


def _ne_operator(column, value):
    if value == "":
        return column.is_not(None)
    adjusted_value, is_range = _adjust_date_range(column, value, "$ne")
    if adjusted_value is not None and is_range is not None:
        return adjusted_value if is_range else column != adjusted_value
    return column != value


def _gt_operator(column, value):
    return operators.gt(column, _adjust_date_range(column, value, "$gt")[0])


def _gte_operator(column, value):
    return operators.ge(column, _adjust_date_range(column, value, "$gte")[0])


def _lt_operator(column, value):
    return operators.lt(column, _adjust_date_range(column, value, "$lt")[0])


def _lte_operator(column, value):
    return operators.le(column, _adjust_date_range(column, value, "$lte")[0])

def _json_path_filter(column, path: str, value, op: str, cast_to=None):
    expr = column
    for key in path.split("."):
        expr = expr[key]
    leaf = expr.astext

    # 2) cast if needed (e.g. Integer, DateTime)
    if cast_to is not None:
        leaf = cast(leaf, cast_to)

    # 3) map op string to SQLA operator
    op_map = {
        "==": operators.eq,
        "!=": operators.ne,
        "<":  operators.lt,
        "<=": operators.le,
        ">":  operators.gt,
        ">=": operators.ge,
        "in": operators.in_op,
    }
    fn = op_map.get(op)
    if not fn:
        raise ValueError(f"Unsupported operator {op!r}")

    # 4) return the binary expression
    return fn(leaf, value)

def _range_operator(column, low, high, sql_type):
    """
    Casts column.astext to sql_type and applies BETWEEN low AND high.
    sql_type should be a SQLAlchemy type (Integer or DateTime).
    """
    return cast(column.astext, sql_type).between(low, high)


def _isanyof_operator(column, value):
    return or_(*[
        _adjust_date_range(column, v, "$eq")[
            0] if isinstance(v, str) else column == v
        for v in value
    ])

def _contains_operator(column, value):
    # if JSON/JSONB column, use JSONB.contains()
    if isinstance(column.type, (JSON, JSONB)):
        return column.contains(cast(value, JSONB))
    # else fall back to substring search
    return column.ilike(f"%{value}%")

def _has_key_operator(column, key):
    if not isinstance(column.type, (JSON, JSONB)):
        raise TypeError("$has_key is only supported on JSON/JSONB columns")
    # maps to the SQL '?' operator
    return column.has_key(key)

# array‐of‐keys operators: ?| and ?&
def _has_any_operator(column, keys):
    if not isinstance(column.type, (JSON, JSONB)):
        raise TypeError("$has_any is only supported on JSON/JSONB columns")
    return column.has_any(keys)

def _has_all_operator(column, keys):
    if not isinstance(column.type, (JSON, JSONB)):
        raise TypeError("$has_all is only supported on JSON/JSONB columns")
    return column.has_all(keys)

def _contained_by_operator(column, value):
    if not isinstance(column.type, (JSON, JSONB)):
        raise TypeError("$contained_by is only supported on JSON/JSONB columns")
    return column.contained_by(cast(value, JSONB))

COMPARISON_OPERATORS = {
    "$eq": _eq_operator,
    "$ne": _ne_operator,
    "$gt": _gt_operator,
    "$gte": _gte_operator,
    "$lt": _lt_operator,
    "$lte": _lte_operator,
    "$in": lambda col, v: col.in_(v),
    # replace the old `$contains`:
    "$contains": _contains_operator,
    # JSONB‐specific:
    "$has_key": _has_key_operator,
    "$has_any": _has_any_operator,
    "$has_all": _has_all_operator,
    "$contained_by": _contained_by_operator,
    # your existing string‐based operators:
    "$ncontains": lambda col, v: ~col.ilike(f"%{v}%"),
    "$startswith": lambda col, v: col.ilike(f"{v}%"),
    "$endswith": lambda col, v: col.ilike(f"{v}"),
    "$isnotempty": lambda col: col.is_not(None),
    "$isempty": lambda col: col.is_(None),
    "$isanyof": _isanyof_operator,

    "$int_between": lambda col, bounds: _range_operator(col, bounds[0], bounds[1], Integer),
    "$dt_between" : lambda col, bounds: _range_operator(col, bounds[0], bounds[1], DateTime),

    "$path_eq": lambda col, v: _json_path_filter(col, list(v.items())[0][0], list(v.items())[0][1], "=="),
    "$path_gt": lambda col, v: cast(_json_path_filter(col, v["path"], v["value"], "==").astext, Integer) > v["value"],
    "$path_gte": lambda col, v: cast(_json_path_filter(col, v["path"], v["value"], "==").astext, Integer) >= v["value"],
    "$path_lt": lambda col, v: cast(_json_path_filter(col, v["path"], v["value"], "==").astext, Integer) < v["value"],
    "$path_lte": lambda col, v: cast(_json_path_filter(col, v["path"], v["value"], "==").astext, Integer) <= v["value"],
    "$path_in": lambda col, v: _json_path_filter(col, v["path"], v["values"], "in"),

}