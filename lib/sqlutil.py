from django.db.models.sql.datastructures import EmptyResultSet

def select_for_share(queryset, nowait=False):
    """
    This is a hacky way to get a SELECT FOR SHARE. This merely slaps a
    "FOR SHARE" or "FOR SHARE NOWAIT" a the end of the query. On
    complex queries (joins, subqueries) it may break, but it
    works on simple queries.

    It is definitely possible to create nonsensical queries with it.

    The strategy is to get the sql and the parameter list of the query
    set passed as argument, modify the SQL and then issue a new query
    on the default manager for the model for which the query set was
    created.
    """
    manager = queryset.model.objects
    try:
        (sql, params) = queryset.query.sql_with_params()
    except EmptyResultSet:
        return manager.none()

    sql += " FOR SHARE"
    if nowait:
        sql += " NOWAIT"
    return manager.raw(sql, params)
