# fastapi_querybuilder/builder.py

from sqlalchemy import select, or_, asc, desc, String, Enum
from fastapi import HTTPException
from .core import parse_filter_query, parse_filters, resolve_and_join_column


def build_query(cls, params):
    if hasattr(cls, 'deleted_at'):
        query = select(cls).where(cls.deleted_at.is_(None))
    else:
        query = select(cls)

    # Filters
    parsed_filters = parse_filter_query(params.filters)
    if parsed_filters:
        filter_expr, query = parse_filters(cls, parsed_filters, query)
        if filter_expr is not None:
            query = query.where(filter_expr)

    # Search
    if params.search:
        search_expr = []
        for column in cls.__table__.columns:
            if isinstance(column.type, String):
                # Search in string columns using ilike
                search_expr.append(column.ilike(f"%{params.search}%"))
            elif isinstance(column.type, Enum):
                # Search in enum columns by checking if search term matches any enum value
                enum_matches = []
                if hasattr(column.type, 'enums'):
                    for enum_value in column.type.enums:
                        if params.search.lower() in enum_value.lower():
                            enum_matches.append(column == enum_value)
                if enum_matches:
                    search_expr.extend(enum_matches)
            # Optionally, search in integer columns if the search is a digit
            elif hasattr(column.type, "python_type") and column.type.python_type is int:
                if params.search.isdigit():
                    search_expr.append(column == int(params.search))
            # Optionally, search in boolean columns
            elif hasattr(column.type, "python_type") and column.type.python_type is bool:
                if params.search.lower() in ("true", "false"):
                    search_expr.append(column == (params.search.lower() == "true"))

        if search_expr:
            query = query.where(or_(*search_expr))

    # Sorting
    if params.sort:
        try:
            sort_field, sort_dir = params.sort.split(":")
        except ValueError:
            sort_field, sort_dir = params.sort, "asc"

        column = getattr(cls, sort_field, None)
        if column is None:
            nested_keys = sort_field.split("__")
            if len(nested_keys) > 1:
                joins = {}
                column, query = resolve_and_join_column(
                    cls, nested_keys, query, joins)
            else:
                raise HTTPException(
                    status_code=400, detail=f"Invalid sort field: {sort_field}")

        query = query.order_by(
            asc(column) if sort_dir.lower() == "asc" else desc(column))

    return query
