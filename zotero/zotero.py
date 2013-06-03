import urllib2
import urllib
import logging

logger = logging.getLogger(__name__)

class Query(object):
    """
    The Query class models objects encapsulating the information that is
    needed to perform a Zotero query. For the purpose of this class, a
    Zotero Query query is analyzed as follows:

    https://<server info>/<user or group prefix>/<fragment>?<parameters>

    <server info> is not recorded in this object.
    
    <user or group prefix> is created from tparams.uid or tparams.gid.

    <fragment> comes from the fragment attribute of the Query object.

    <parameters> is built from the following sources:
    
    * tparams.key

    * tparams.params

    * the additional_params attribute of the Query object. These override the previous sources.
    """

    #
    # Obfuscating code. We use this to avoid outputting API keys in
    # logs.
    #
    __obfuscator = {}
    __count = 1

    @classmethod
    def __obfuscate(cls, token, prefix):
        """
        Given an token, this function guaratees that:
        
        * If the function has already been called with token, then the
          value returned will be the same as the one previously
          returned. (In this case, prefix is ignored.)
          
        * Otherwise, the value returned is created from the prefix
          parameter plus a numeric suffix. The numeric suffix is
          shared among prefixes.

        >>> __obfuscate(cls, "blah", "KEY"):
        ...KEY1
        >>> __obfuscate(cls, "blah", "KEY"):
        ...KEY1
        >>> __obfuscate(cls, "toto", "UID"):
        ...UID2

        Note how the number 2 is added to UID. Because 1 was already
        used for obfuscating "blah" there won't be a UID1 during this
        run.
        """
        ret =  cls.__obfuscator.get(token, None)
        if ret is None:
            ret = prefix + str(cls.__count)
            cls.__obfuscator[token] = ret
            cls.__count += 1
        return ret

    def __init__(self, fragment, tparams, additional_params = None):
        """
        See the class documentation for the meaning of the parameters.
        
        fragment and tparams may not be None.
        """
        self._fragment = fragment
        self._tparams = tparams
        self._additional_params = additional_params
        self._str = None
        self._safe = None

        if self._fragment is None:
            raise ValueError("fragment cannot be None")

        if self._tparams is None:
            raise ValueError("tparams cannot be None")

    @property
    def fragment(self):
        return self._fragment
    
    @property
    def tparams(self):
        return self._tparams

    @property
    def additional_params(self):
        return self._additional_params

    def __str__(self):
        "Returns a string representation of the object. The returned value contains the part of a Zotero query URL which follows the slash that appears after the hostname of the query. That is, assuming a query to the Zotero server at zotero.org, it contains everything after https://api.zotero.org/ "
        if self._str is not None:
            return self._str

        self._str = self._build_url()
        return self._str

    def safe_str(self):
        "Returns a safe string representation. This is the same as what is returned by __str__ but with the uid or gid and the API key obfuscated."
        if self._safe is not None:
            return self._safe
        
        self._safe = self._build_url(safe = True)
        return self._safe
        
    def _build_url(self, safe = False):
        "Utility function which does the work of building URLs. If safe is True, then obfuscate uid, gid and API key."
        url = None
        if self.tparams.uid is not None:
            url = ["users/", self.__obfuscate(self.tparams.uid, "USER") if safe else self.tparams.uid]
        elif self.tparams.gid is not None:
            url = ["groups/", self.__obfuscate(self.tparams.gid, "GROUP") if safe else self.tparams.gid]
        else:
            raise ValueError("tparams must have uid or gid set")

        url.append("/%s?key=%s" % (self.fragment, self.__obfuscate(self.tparams.key, "KEY") if safe else self.tparams.key))

        if self.tparams.encoded_params:
            url += ("&", self.tparams.encoded_params)

        if self.additional_params:
            url += ("&", urllib.urlencode(self.additional_params, True))

        return ''.join(url)

class Server(object):
    """
    This class models objects able to resolve a URL representing a Zotero query.
    """
    def __init__(self, hostname = "api.zotero.org"):
        "By default our hostname is the Zotero server hosted by the folks at zotero.org."
        self.hostname = hostname

    def resolve(self, query, data = None, headers = None):
        """
        The query parameter would typically be a Query object encoding
        a specific query.

        Sends the query to the host specified when the object was
        created and returns a urllib2 object representing the result.
        """
        return urllib2.urlopen(
            urllib2.Request(url = self._make_url(query), 
                            data = data, 
                            headers = headers))

    def _make_url(self, query):
        return ''.join(("https://", self.hostname, "/", str(query)))



class Cache(object):
    def __init__(self, server = Server()):
        "The server parameter is the server to use to get results from when the cache misses."
        self.server = server

    def resolve(self, query, data = None, headers = None):
        """
        The query parameter would typically be a Query object encoding
        a specific query.

        This default implementation is stupid: the cache passes all
        queries to the server without actually caching anything.
        """
        return self.server.resolve(query, data, headers)

class TransactionParameters(object):
    """
    This class models the transaction parameters which are unlikely to
    change across transactions to a Zotero server. For instance, a
    user making mutiple queries is unlikely to need a different uid
    and API key across these queries.

    The properties of objects of this class are for the most part
    self-explanatory. The key parameter is the Zotero API key. The
    encoded_params parameter is the params parameter encoded to be
    integrated into a URL.

    Apart from being required to have a uid or a gid and having a key
    parameter set, this class does not distinguish between parameters
    that are *likely* to change and those *unlikely* to change.
    """
    def __init__(self, **kwargs):
        self._uid = kwargs.get("uid")
        self._gid = kwargs.get("gid")
        self._key = kwargs.get("key")
        self._params = kwargs.get("params")
        self._encoded_params = None

        if self._uid is not None and self._gid is not None:
            raise ValueError("cannot instanciate TransactionParameters object with both uid and gid.")
        
        if self._uid is None and self._gid is None:
            raise ValueError("one of uid or gid must be set.")

        if self._key is None:
            raise ValueError("key must be set.")

    @property
    def uid(self):
        return self._uid

    @property
    def gid(self):
        return self._gid

    @property
    def key(self):
        return self._key

    @property
    def params(self):
        return self._params

    @property
    def encoded_params(self):
        if self._params is None:
            return None

        if self._encoded_params is None:
            self._encoded_params = urllib.urlencode(self._params, True)

        return self._encoded_params
        

class Zotero(object):
    """
    This class modelizes a Zotero query engine. This engine expect to
    talk to a cache, which would in turn presumably talk to a Zotero
    server to resolve cache misses.
    """ 
    def __init__(self, cache = Cache()):
        self.cache = cache

    def search(self, q, tparams, **kwargs):
        """
        Performs a search in a Zotero library. The parameter q
        corresponds to those parameters described in the Zotero server
        API documentation. See that documentation for details.

        Additional parameters may be specified with kwargs.

        The library in which the search is performed is determined by
        tparams.uid or tparam.gui and tparams.key.
        """

        kwargs["q"] = q
        return self.resolve(Query("items", tparams, kwargs))

    def get_item(self, item_key, tparams, **kwargs):
        return self.resolve(Query("items/" + item_key, tparams, kwargs))

    def create_item(self, tparams, data, zotero_write_token, **kwargs):
        headers = {"Content-Type": "application/json"}
        if zotero_write_token is not None:
            header["X-Zotero-Write-Token"] = zotero_write_token
        return self.resolve(Query("items", tparams, kwargs), data, 
                            headers)

    def resolve(self, query, data, headers):
        return self.cache.resolve(query, data, headers)
        

