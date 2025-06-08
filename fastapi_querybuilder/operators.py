# app/filters/operators.py

from sqlalchemy import and_, or_
from sqlalchemy.sql import operators
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


def _isanyof_operator(column, value):
    return or_(*[
        _adjust_date_range(column, v, "$eq")[
            0] if isinstance(v, str) else column == v
        for v in value
    ])


COMPARISON_OPERATORS = {
    "$eq": _eq_operator,
    "$ne": _ne_operator,
    "$gt": _gt_operator,
    "$gte": _gte_operator,
    "$lt": _lt_operator,
    "$lte": _lte_operator,
    "$in": lambda column, value: column.in_(value),
    "$contains": lambda column, value: column.ilike(f"%{value}%"),
    "$ncontains": lambda column, value: ~column.ilike(f"%{value}%"),
    "$startswith": lambda column, value: column.ilike(f"{value}%"),
    "$endswith": lambda column, value: column.ilike(f"%{value}"),
    "$isnotempty": lambda column: column.is_not(None),
    "$isempty": lambda column: column.is_(None),
    "$isanyof": _isanyof_operator,
}
