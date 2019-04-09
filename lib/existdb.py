import os

import requests
from django.conf import settings
import pyexistdb.db
from pyexistdb import patch
from pyexistdb.exceptions import ExistDBException
from . import xquery

patch.request_patching(patch.XMLRpcLibPatch)

class ExistDB(pyexistdb.db.ExistDB):

    def getDocument(self, name):
        # This does pretty much what the default getDocument does
        # but it adds the _indent=no parameter.
        pyexistdb.db.logger.debug('getDocument %s' % self.restapi_path(name))
        response = self.session.get(self.restapi_path(name), stream=False,
                                    params={"_indent": "no"},
                                    **self.session_opts)
        if response.status_code == requests.codes.ok:
            return response.content
        if response.status_code == requests.codes.not_found:
            raise ExistDBException('%s not found' % name)

    # Note that there is no atomicity here. It would be possible for
    # removeCollection to fail because the collection does not exist
    # and then hasCollection to succeed because another process
    # created the collection in-between.
    def removeCollection(self, collection_name, ignore_nonexistent=False):
        try:
            return super(ExistDB, self).removeCollection(collection_name)
        except ExistDBException:
            if not ignore_nonexistent or self.hasCollection(collection_name):
                raise

    # See comment above regarding atomicity. It applies here too.
    def removeDocument(self, name, ignore_nonexistent=False):
        try:
            return super(ExistDB, self).removeDocument(name)
        except ExistDBException:
            if not ignore_nonexistent or self.hasDocument(name):
                raise

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

def get_collection_path(what):
    if what not in ("chunks", "display", "util", None):
        raise ValueError("unknown value for what: " + what)

    if what is None:
        return settings.EXISTDB_ROOT_COLLECTION

    return "/".join([settings.EXISTDB_ROOT_COLLECTION, what])

def get_path_for_chunk_hash(kind, c_hash):
    return "/".join([get_collection_path(kind), c_hash])


def is_lucene_query_clean(db, query):
    """
    Use a cost-effective way to determine whether a Lucene query has a
    syntax error.

    :param: The Lucene query to check.

    :returns: ``True`` if the query has no syntax error, ``False`` if
    it does have syntax errors.
    """
    try:
        #
        # This appears to be as cost-effective as it gets. We run a query on a
        # empty document. With eXist-db 2.x we were using ``ft:query(<doc/>,
        # ...`` but in eXist-db 4.x something is not happy with the document
        # being anonymous ("name is empty"). So for 4.x we require that the db
        # be created with an empty document which we then use.
        #
        # Ultimately, either nothing will be returned but without error, or a
        # parsing error will occur.
        #
        db.query(xquery.format("doc('/btw/util/empty.xml')/doc/ft:query(., "
                               "{search_text})",
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

def list_collection(db, path):
    items = set()
    for query_chunk in query_iterator(db, xquery.format("""\
for $x in collection({path}) return document-uri($x)""", path=path)):
        items |= set(str(value) for value in query_chunk.values)
    return items
