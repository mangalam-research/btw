import os

import requests
from django.conf import settings
from eulexistdb.db import ExistDB
from eulexistdb import patch
from eulexistdb.exceptions import ExistDBException
from . import xquery

patch.request_patching(patch.XMLRpcLibPatch)

def running():
    try:
        # We use the admin to check if the server responds.
        r = requests.get(
            os.path.join(settings.EXISTDB_SERVER_URL, "rest/"),
            auth=(settings.BTW_EXISTDB_SERVER_ADMIN_USER,
                  settings.BTW_EXISTDB_SERVER_ADMIN_PASSWORD))
    except requests.ConnectionError:
        return False
    return r.status_code == 200

def get_admin_db():
    return ExistDB(server_url=settings.EXISTDB_SERVER_URL,
                   username=settings.BTW_EXISTDB_SERVER_ADMIN_USER,
                   password=settings.BTW_EXISTDB_SERVER_ADMIN_PASSWORD)

def get_chunk_collection_path():
    return os.path.join(settings.EXISTDB_ROOT_COLLECTION, "chunks")

def is_lucene_query_clean(db, query):
    """
    Use a cost-effective way to determine whether a Lucene query has a
    syntax error.

    :param: The Lucene query to check.

    :returns: ``True`` if the query has no syntax error, ``False`` if
    it does have syntax errors.
    """
    try:
        # This appears to be as cost-effective as it gets. We run a
        # query on a bogus document. Either nothing will be returned
        # but without error, or a parsing error will occur.
        db.query(xquery.format("ft:query(<doc/>, {search_text})",
                               search_text=query))
    except ExistDBException as ex:
        # The query is faulty.
        if ex.message().startswith(
                "exerr:ERROR Syntax error in Lucene query string"):
            return False

        # Reraise anything we're not testing for.
        raise ex

    # No error, the query string was good...
    return True

def query_iterator(db, xquery, **kwargs):
    # Copy it because we're going to change it.
    kwargs = dict(kwargs)

    if "how_many" not in kwargs:
        kwargs["how_many"] = 1000

    release = kwargs.get("release", None)
    # When release is true it means that we want to release the xquery
    # when we are done. However, we do not want to release the
    # *individual* queries made to eXist.
    if release:
        del kwargs["release"]

    done = 0 if "start" not in kwargs else kwargs["start"] - 1
    query = None
    session = None
    hits = None
    try:
        while query is None or done < hits:
            kwargs["start"] = done + 1
            kwargs["cache"] = True if query is None else session

            query = db.query(xquery, **kwargs)

            # We grab everything we need before we pass it to the caller
            # through yield. This way if the caller messes with these
            # values, we're still safe.
            session = query.session
            hits = query.hits
            done += query.count

            yield query
    finally:
        if session is not None and release:
            db.query(release=session)
