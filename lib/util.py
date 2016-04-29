import re
import operator
import datetime
import tempfile
import os
import subprocess
from contextlib import contextmanager
from StringIO import StringIO
import lxml.etree
import logging
import functools32
from functools import wraps

import semver
from django.db.models import Q
from django.utils.timezone import utc
from django.conf import settings
from django.core.cache import caches
from django.core.exceptions import PermissionDenied
import django_redis

# We effectively reexport this function here.
from .settings import join_prefix  # pylint: disable=unused-import

class WithTmpFiles(object):

    def __init__(self, input_data=None):
        self._input_data = input_data
        self._tmpinput_path = None
        self._tmpoutput_path = None

    def __enter__(self):
        (tmpinput_file, tmpinput_path) = tempfile.mkstemp(prefix='btwtmp')
        if self._input_data is not None:
            with os.fdopen(tmpinput_file, 'w') as f:
                f.write(self._input_data.encode("utf-8"))

        (tmpoutput_file, tmpoutput_path) = tempfile.mkstemp(prefix='btwtmp')

        self._tmpinput_path = tmpinput_path
        self._tmpoutput_path = tmpoutput_path

        return (tmpinput_file, tmpinput_path, tmpoutput_file, tmpoutput_path)

    def __exit__(self, exc_type, exc_value, traceback):
        os.unlink(self._tmpinput_path)
        os.unlink(self._tmpoutput_path)


def run_saxon(xsl_path, input_data):
    with WithTmpFiles(input_data) as (_, tmpinput_path,
                                      tmpoutput_file, tmpoutput_path):
        subprocess.check_call(["saxon", "-s:" + tmpinput_path, "-xsl:" +
                               xsl_path, "-o:" + tmpoutput_path])
        out = os.fdopen(tmpoutput_file, 'r')
        ret = out.read().decode('utf-8')
        out.close()
        return ret


def run_xsltproc(xsl_path, input_data):
    with WithTmpFiles(input_data) as (_, tmpinput_path,
                                      tmpoutput_file, tmpoutput_path):
        subprocess.check_call(["xsltproc", "-o", tmpoutput_path, xsl_path,
                               tmpinput_path])

        out = os.fdopen(tmpoutput_file, 'r')
        ret = out.read().decode('utf-8')
        out.close()
        return ret


# We use a LRU cache so that we don't keep loading the same data over
# and over. BTW uses a limited number of schemas.
@functools32.lru_cache(maxsize=10)
def rng_path_to_schema(path):
    with open(path) as f:
        schema_doc = lxml.etree.parse(f)
    return lxml.etree.RelaxNG(schema_doc)


def validate_with_rng(rng_path, input_data, silent=True):
    schema = rng_path_to_schema(rng_path)

    try:
        doc = lxml.etree.fromstring(input_data.encode("utf8"))
    except lxml.etree.XMLSyntaxError:
        # The document is not even well-formed.
        return False

    return schema(doc)


# We use a LRU cache so that we don't keep loading the same data over
# and over. BTW uses a limited number of schemas.
@functools32.lru_cache(maxsize=10)
def xmlschema_path_to_schema(path):
    with open(path) as f:
        schema_doc = lxml.etree.parse(f)
    return lxml.etree.XMLSchema(schema_doc)


def validate_with_xmlschema(schema_path, input_data, silent=True):
    schema = xmlschema_path_to_schema(schema_path)

    try:
        doc = lxml.etree.fromstring(input_data.encode("utf8"))
    except lxml.etree.XMLSyntaxError:
        # The document is not even well-formed.
        return False

    return schema(doc)

@functools32.lru_cache(maxsize=10)
def transform_path_to_transform(path):
    with open(path) as f:
        doc = lxml.etree.parse(f)
    return lxml.etree.XSLT(doc)

def transform_with_xslt(xslt_path, input_data):
    transform = transform_path_to_transform(xslt_path)
    doc = lxml.etree.fromstring(input_data.encode("utf8"))
    ret = unicode(transform(doc))
    # We first check that what we are going to alter is what we expect.
    assert ret.startswith(u'<?xml version="1.0"?>\n')
    # Add the encoding for consistency with the rest of BTW. Yes, we
    # put utf8 here even though the string is unicode.
    ret = ret.replace(u'?>', u' encoding="UTF-8"?>', 1)
    return ret

def schematron(xsl, input_data):
    """
    Runs the XSL file (which **must** have been produced from a
    schematron schema) against the data and reports whether there was
    any error.
    """
    # The schematron transformation to XSL generates xslt 2. So we
    # cannot use lxml to run the xslt script.
    output = run_saxon(xsl, input_data)
    tree = lxml.etree.fromstring(output.encode("utf-8"))
    found = tree.xpath("//svrl:failed-assert",
                       namespaces={
                           'svrl': 'http://purl.oclc.org/dsdl/svrl'
                       })
    return len(found) == 0

def utcnow():
    """
:returns: The date and time now with the timezone information set
          to UTC. This avoids warnings about naive times.

:rtype: :class:`datetime.datetime`
"""
    return datetime.datetime.utcnow().replace(tzinfo=utc)


# normalize_query and get_query adapted from code on Julien Phalip's
# site.
def normalize_query(query_string,
                    findterms=re.compile(r'"(?:[^"]+)"|(?:\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    '''
Splits the query string in invidual keywords, getting rid of
unecessary spaces and grouping quoted words together.  Example:

>>> normalize_query('  some random  words "with   quotes  " and   spaces')
['some', 'random', 'words', 'with quotes', 'and', 'spaces']
'''
    return [normspace(' ', t.strip()) for t in findterms(query_string)]


def get_query(query_string, search_fields):
    '''
Returns a query, that is a combination of Q objects. That
combination aims to search keywords within a model by testing the
given search fields.
'''
    terms = normalize_query(query_string)
    # What this does is create a field_icontains query for each field.
    # Each of these queries are ORed together so that a given term
    # will generate a hit if it appears in ANY of the fields. Then
    # these ORed queries are ANDed together so that ALL terms must be
    # present somewhere.
    return reduce(operator.and_,
                  [reduce(operator.or_,
                          [Q(**{"%s__icontains" % field_name: term})
                           for field_name in search_fields]
                          )
                   for term in terms]
                  )


def nice_name(user):
    """
    Formats a user's username nicely so that someone can determine who
    the user is. If the user has both a first name and last name, the
    return value will be "username (first name last name)". If the
    user has only a first name or a last name, then the return value
    will be the same as above except that the parentheses will contain
    only whichever of the first name or last name is set. If the user
    has neither a first nor last name then just returns "username".

    A first name or last name is considered to be set when it is set to
    something else than an empty string.

    :param user:
    :type user: The value of :attr:`settings.AUTH_USER_MODEL`
                determines the class.
    :returns: A nicely formatted user name.
    :rtype: :class:`str`
    """
    first_name = user.first_name.strip()
    last_name = user.last_name.strip()

    if len(first_name) and len(last_name):
        return "{0} ({1} {2})".format(user.username, first_name,
                                      last_name)

    if len(first_name) or len(last_name):
        return "{0} ({1})".format(user.username,
                                  first_name if len(first_name) else last_name)

    return user.username

_cached_version = None


def version():
    """
    Returns the version of BTW. This value is computed once and then
    cached.
    """
    global _cached_version  # pylint: disable-msg=global-statement
    if _cached_version is not None:
        return _cached_version

    # We have to be running from a git tree.
    unclean = subprocess.check_output(["git", "status", "--porcelain"])

    if not (settings.DEBUG or settings.BTW_TESTING) and unclean:
        raise Exception("running with unclean tree while DEBUG is false")

    describe = subprocess.check_output(["git", "describe", "--match",
                                        "v*"]).strip()

    if unclean:
        describe += "-unclean"

    sep = describe.find("-")
    semver.parse(describe[1:len(describe) if sep == -1 else sep])

    _cached_version = describe

    return describe

class DirectCons(object):

    def __init__(self):
        self.map = {}

    def __getitem__(self, key):
        try:
            return self.map[key]
        except KeyError:
            con = django_redis.get_redis_connection()
            self.map[key] = con
            return con

con_by_name = DirectCons()

def delete_own_keys(name):
    """
    Deletes the keys that are prefixed with the cache's prefix.

    .. warning:: This method is Redis-specific and will fail if used
                 on a cache that is not backed by redis.
    """
    cache = caches[name]
    prefix = cache.key_prefix
    con = con_by_name[name]
    keys = con.keys(prefix + ':*')
    if keys:
        con.delete(*keys)


def add_to_set(name, key, member):
    cache = caches[name]
    con = con_by_name[name]
    con.sadd(cache.make_key(key), member)

def remove_from_set(name, key, member):
    cache = caches[name]
    con = con_by_name[name]
    con.srem(cache.make_key(key), member)

def get_set(name, key):
    cache = caches[name]
    con = con_by_name[name]
    return con.smembers(cache.make_key(key))

def get_set_union(name, iterator):
    cache = caches[name]
    con = con_by_name[name]
    return con.sunion([cache.make_key(i) for i in iterator])

@contextmanager
def WithStringIO(logger):
    """
Add a :class:`logging.StreamHandler` to the logger so that it
outputs to a :class:`StringIO` object.

:param logger: The logger to manipulate.

:type logger: :class:`str` or :class:`logging.Logger`.

:return: The StringIO object and the handler that were created.

:rtype: (:class:`StringIO`, :class:`logging.StreamHandler`)
"""
    if type(logger) is str:
        logger = logging.getLogger(logger)
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    yield stream, handler
    logger.removeHandler(handler)

class PermissionResolver(object):

    def __init__(self, Permission, ContentType):
        """
        A ``PermissionResolver`` object is used to get permission objects
        from ``(permission name, app name, model name)`` sequences. We
        pass models to it so that it can be used in migrations.

        :param Permission: The model for auth permission objects.
        :param ContentType: The model for content type objects.
        """
        self.Permission = Permission
        self.ContentType = ContentType
        self.ct_cache = {}
        self.p_cache = {}

    def resolve(self, p):
        perm, app, model = p
        p_key = tuple(p)
        p = self.p_cache.get(p_key)
        if p is not None:
            return p

        ct = self.resolve_ct(app, model)
        p = self.Permission.objects.get(codename=perm, content_type=ct)
        self.p_cache[p_key] = p
        return p

    def resolve_ct(self, app, model):
        ct_key = (app, model)
        ct = self.ct_cache.get(ct_key)
        if ct is not None:
            return ct

        ct = self.ContentType.objects.get(app_label=app, model=model)
        self.ct_cache[ct_key] = ct
        return ct

class DisableMigrationsTransactionMixin(object):
    """
    This is a mixin that provides the glue necessary for
    TransactionTestCase tests to work if BTW_DISABLE_MIGRATIONS is
    ``True``. Use ``DisableMigrationsMixin`` for ``TestCase``.
    """

    def _fixture_setup(self):
        # We have to create the permissions before fixtures are loaded.
        from django.conf import settings
        if settings.BTW_DISABLE_MIGRATIONS:
            from btw_management.management.commands.btwdb import create_perms
            create_perms()
        return super(DisableMigrationsTransactionMixin, self)._fixture_setup()

class DisableMigrationsMixin(object):
    """
    This is a mixin that provides the glue necessary for TestCase
    tests to work if BTW_DISABLE_MIGRATIONS is ``True``. Use
    ``DisableMigrationsTransactionMixin`` for ``TransactionTestCase``.
    """

    @classmethod
    def setUpClass(cls):
        from django.conf import settings

        # If we disable migrations, we swallow fixtures under
        # my_fixtures.  This is so that we can perform our loading
        # operations in the proper order.
        if settings.BTW_DISABLE_MIGRATIONS:
            if cls.fixtures:
                cls.my_fixtures = cls.fixtures
                cls.fixtures = None
            else:
                cls.my_fixtures = None
        return super(DisableMigrationsMixin, cls).setUpClass()

    @classmethod
    def setUpTestData(cls):
        # We have to create the permissions before fixtures are loaded.
        from django.conf import settings
        if settings.BTW_DISABLE_MIGRATIONS:
            from btw_management.management.commands.btwdb import create_perms
            create_perms()

            fixtures = cls.my_fixtures
            if fixtures:
                from django.core.management import call_command
                for db_name in cls._databases_names(include_mirrors=False):
                    try:
                        call_command('loaddata', *fixtures, **{
                            'verbosity': 0,
                            'commit': False,
                            'database': db_name,
                        })
                    except Exception:
                        cls._rollback_atomics(cls.cls_atomics)
                        raise

        return super(DisableMigrationsMixin, cls).setUpTestData()

class NoPostMigrateMixin(object):

    def _fixture_teardown(self):
        # This is a terrible hack to get proper behavior for
        # serialized_rollbacks in a TransactionTestCase. The problem
        # is as follows:
        #
        # 1. serialized_rollbacks is necessary to reload the data that
        # is generated from data migrations.
        #
        # 2. Reloading the serialized data causes integrity failures
        # with Django apps like django.contrib.contenttypes and
        # django.contrib.auth. The problem is that upon flushing the
        # database, Django emits a post migrate signal which causes
        # content types and default permissions associated with models
        # to be recreated. Then, when the data is deserialized, some
        # records are created twice.
        #
        # 3. Using the available_apps field *would* be an option but
        # a) it is part of the private API and can change at any
        # moment, b) tracing the dependencies among apps is a harduous
        # task, which is not helped by the way the available_apps code
        # in Django's testcases.py file handles exceptions. (When an
        # exception occurs while setting the apps that are going to be
        # available, this exception may get swallowed in the error
        # handling code if another exception happens there.)
        #
        # So the strategy here is to temporarily set available_apps to
        # a non-None value, which causes the stock _fixture_teardown()
        # to not generate a post migrate signal.
        #
        saved_aa = self.available_apps
        try:
            self.available_apps = []
            super(NoPostMigrateMixin, self)._fixture_teardown()
        finally:
            self.available_apps = saved_aa

def ajax_login_required(view):
    """
    This is the AJAX-y version of @login_required. If the user is not
    authenticated, this will raise ``PermissionDenied`` rather than
    redirect to the login page.
    """
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated():
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper
