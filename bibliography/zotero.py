from base64 import urlsafe_b64encode
import json
import re
import urllib
import urllib2
import logging
from json.encoder import JSONEncoder
from xml.dom import minidom

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.cache import get_cache

logger = logging.getLogger(__name__)

CACHED_DATA_VERSION = 2

cache = get_cache('bibliography')

_cached_details = None


def zotero_settings():
    """
    Function for retrieving project-wide zotero account details.

    :returns: A dictionary containing two keys. The ``uid`` key has a
              value which corresponds to the user id of the
              project-wide Zotero account. The ``api_key`` key has a
              value which corresponds to the Zotero API key to use to
              access the project-wide account.
    :rtype: :class:`dict`
    :raises ImproperlyConfigured: If ``ZOTERO_SETTINGS`` is undefined
             or not of the right format.

    """
    # pylint: disable=W0603
    global _cached_details

    if _cached_details is not None:
        return _cached_details

    details = getattr(settings, "ZOTERO_SETTINGS")

    if details is None:
        raise ImproperlyConfigured("ZOTERO_SETTINGS is undefined")

    if type(details) != dict:
        raise ImproperlyConfigured("ZOTERO_SETTINGS is must be a dictionary")

    if 'uid' not in details or 'api_key' not in details:
        raise ImproperlyConfigured(
            "ZOTERO_SETTINGS does not have all fields required")

    if 'server' not in details:
        details['server'] = "https://api.zotero.org/"

    _cached_details = details
    return _cached_details

key_re = re.compile(r"([&?]key=)[^&]+")


def _sanitize_url(url):
    """
    Removes they `key=` parameter from a URL.
    """
    return key_re.sub("", url)


_UNSAFE = False


def _url_for_logging(url):
    """
    Modifies a URL for logging to as to remove sensitive
    information. This is a seprate function from `_sanitize_url`
    because we may want to turn this transformation off for
    debugging. Whereas some operations that need sanitized URLs
    *always* need sanitized URLs.
    """

    #
    # We perform this check here because it is not okay to probe
    # settings at the top level (see Django documentation).
    #
    if _UNSAFE and not settings.DEBUG:
        raise ImproperlyConfigured(
            "_UNSAFE cannot be used unless you are in debugging mode")

    return _sanitize_url(url) if not _UNSAFE else url


def _make_cache_key(url):
    """
    Creates a cache key. One of the things this function does is
    remove the `key=` parameter. As of version 2 of the Zotero API,
    given the way Zotero works, and given the way we use Zotero for
    BTW, the results returned from a query *cannot* vary depending on
    they key used. So if a key is changed because the previous key was
    accidentally leaked, then queries with the new key should still be
    hits.

    This also has for advantage keeping keys out of the cache, and
    out of the cache logs.

    :param url: The URL of the query.
    :type url: :class:`str`
    :returns: The cache key.
    :rtype: :class:`str`
    """
    return urlsafe_b64encode(_sanitize_url(url))


class Zotero(object):

    """
    This class manages accesses to a Zotero database.

    """

    def __init__(self, api_dict, object_type='local'):
        """
        Initialize api details from `api_dict`.
        """
        try:
            self.full_uid = api_dict['uid']
            self.apikey = api_dict['api_key']
        except KeyError:
            raise ImproperlyConfigured("ZOTERO_SETTINGS improperly set")

        if re.search("^u:", self.full_uid):
            # create the user prefix
            self.prefix = api_dict['server'] + "users/"
        elif re.search("^g:", self.full_uid):
            # create the group prefix
            self.prefix = api_dict['server'] + "groups/"
        else:
            raise ImproperlyConfigured("ZOTERO_SETTINGS['uid'] is of "
                                       "the wrong format")
        # use regular expression to strip the uid prefix u:, g:
        self.userid = re.sub("^u:|^g:", "", self.full_uid)
        self.object_type = object_type

        # This is the appropriate URL to get a single item.
        self.basic_item_url = self.prefix + \
            "%s/items?key=%s&format=atom&content=json" % \
            (self.userid, self.apikey)

        # For everything else, we want to use the /top version of the
        # URL. If not, we'll *also* get items that are in the trash.
        self.basic_top_url = self.prefix + \
            "%s/items/top?key=%s&format=atom&content=json" % \
            (self.userid, self.apikey)

    def get_item(self, itemKey):
        # As of 2014/02/10 the server at api.zotero.org does not
        # handle If-Modified-Since-Version at all for individual
        # items, but it does for collections. (When requesting
        # individual items, the field is ignored and the request
        # always returns 200, never 304.)
        #
        # So here, instead of asking for an individual item, we ask
        # for a collection of one item, so that we can use
        # If-Modified-Since-Version.
        #
        # This is less optimal than what the documentation suggests
        # but more optimal than the alternative of never being able to
        # benefit from 304.
        #

        search_url = self.__build_item_search_url(itemKey)
        logger.debug("getting item: %s", _url_for_logging(search_url))

        results_list, _extra_data_dict = self.__get_search_results(search_url)
        assert len(results_list) <= 1
        return results_list[0] if len(results_list) > 0 else None

    def __build_item_search_url(self, itemKey):
        return self.basic_item_url + "&itemKey=" + itemKey

    def __build_search_url(self, keyword):
        """
        Builds the URL to search for a keyword.
        """
        search_field = urllib.quote(keyword.lower().strip())
        return self.basic_top_url + "&q=" + search_field

    def search(self, keyword):
        """
        Performs a keyword search.
        """
        return self.__get_search_results(self.__build_search_url(keyword))

    def duplicate_search(self, title, item_type):
        """
        Performs a duplicate search.
        """
        url = self.basic_top_url + "&itemType=%s&q=%s" % (item_type, title)
        return self.__get_search_results(url)

    def get_all(self):
        """
        Gets all records in the Zotero Library.
        """
        return self.__get_search_results(self.basic_top_url)

    def __get_search_results(self, url):
        """
        Gets all JSON objects for the given search URL.

        :param url: The URL to use for the request.
        :type url: :class:`str`
        :returns: A tuple of the form `(list, extras)` the list is the
                  list of entries returned by the server as Python
                  dictionaries converted from JSON. The extras is a
                  dictionary whose keys are item keys and values are a
                  dictionary of information not present at the server
                  but added by this library.

        """
        # 2. perform search
        # a. if result does not exist in cache forcefully fetch from zotero.
        # b. if available in cache, check if got modified for the field.
        # b. if not modified display from cache.
        # c. if modified fetch from zotero, reset key in cache.

        # It is safe to search for a parameter like this. (For
        # instance, if the user were to search for an ampersand, this
        # ampersand would not appear as a literal in the URL.)
        for_single_item = url.find("&itemKey=") != -1

        logger.debug("searching url: %s", _url_for_logging(url))

        cache_key = _make_cache_key(url)

        results_list = version = extras = None

        reason = "cache miss"
        if cache_key in cache:
            logger.debug("cache hit for key: %s", cache_key)
            cached_data = cache.get(cache_key)
            reason = "cache stale"

            if type(cached_data) == tuple:
                cached_data_version, results_list, version, extras = \
                    cached_data
                if cached_data_version != CACHED_DATA_VERSION:
                    logger.debug("old data format for key: %s", cache_key)
                    logger.debug("deleting key: %s", cache_key)

                    cache.delete(cache_key)
                    results_list = None
                    version = None
                    extras = None
                    reason = "cache held obsolete format"
            else:
                # Corrupt data in the cache is an error.
                logger.error("cache corrupted for key: %s", cache_key)
                logger.debug("deleting key: %s", cache_key)
                cache.delete(cache_key)
                reason = "cache is corrupt"

        # alway search the modification status.
        headers = {'If-Modified-Since-Version': version}

        fetch_from_cache = False
        res = None
        try:
            res = self.__request(url=url, headers=headers)
        except urllib2.URLError as e:
            logger.debug('search url not working: ' + str(e))
            fetch_from_cache = True

        if res is not None and res.code == 304:
            logger.debug("got 'not modified' for key: %s", cache_key)
            fetch_from_cache = True

        if fetch_from_cache:
            if results_list:
                logger.debug('serving cached')
                return results_list, extras
            logger.debug('serving empty')
            return [], {}

        #
        # Run-of-the-mill connection errors should have been taken
        # care of much earlier. So if we get something else than 200
        # here, then, in all likelihood, there is a bug in this code
        # or on the server side, so we must fail, and fail hard.
        #
        if res.code != 200:
            raise Exception("communication error with Zotero server")

        logger.debug('serving latest (%s) for key: %s',
                     reason, cache_key)

        data = res.read()
        dom_object = minidom.parseString(data)
        json_list = []
        version_key = None
        if 'Last-Modified-Version' in res.headers:
            version_key = res.headers['Last-Modified-Version']

        # retrieve the entry/content tags that contain the item json string
        # for safe playing also keep the entry/published tags
        # for overriding access date if not available in json.

        for entry in dom_object.getElementsByTagName('entry'):
            content_node = entry.getElementsByTagName('content')[0]
            updated_node = entry.getElementsByTagName('updated')[0]

            json_string_tuple = (content_node.childNodes[0].data,
                                 updated_node.childNodes[0].data,)

            json_list.append(json_string_tuple)

        # return list of json string objects
        results_list, extra_data_dict = self.__process_data(json_list)

        # We cache the result of the query in a single cache entry.
        if version_key:
            cache.set(cache_key,
                      (CACHED_DATA_VERSION, results_list, version_key,
                       extra_data_dict))
            logger.debug("cache set for key: %s", cache_key)

        if not for_single_item:
            # Also take care to update the per-item entries in the cache.
            self.__cache_items(results_list, extra_data_dict, version_key)

        return results_list, extra_data_dict

    def __cache_items(self, results_list, extra_data_dict, version_key):
        """
        This method takes the results obtained when performing any request
        that returns a collection of items and unpacks these results
        so as to cache each individual item.

        For instance, if the user searches for keyword ``foo`` and
        gets items ``A, B, C``, then we can proactively cache a result
        for the query that would ask for A, for a query that would ask
        for B and for a query that would ask for C.
        """
        for item in results_list:
            key = item["itemKey"]
            url = self.__build_item_search_url(key)
            cache_key = _make_cache_key(url)
            new_results_list = [item]
            new_extra_data_dict = {key: extra_data_dict[key]}
            cache.set(cache_key, (CACHED_DATA_VERSION,
                                  new_results_list,
                                  version_key,
                                  new_extra_data_dict))
            logger.debug("cache set for key: %s", cache_key)

    def __process_data(self, json_list):
        """Utility function to iterate over raw results to:

        1) Add the scope of search results ( coming from which account ?)
        2) Add published date as it is not available in raw json.
        3) Add additional helpful data to the cache."""
        processed_json_list = []
        extra_data_dict = {}

        for list_item in json_list:

            # model to store the item json for a particular user
            # only a subset of returned json items are being stored

            json_dict = json.loads(list_item[0])

            # REMEMBER TO INCREMENT CACHED_DATA_VERSION WHENEVER YOU
            # CHANGE THIS DICTIONARY.
            #
            # extra_data_dict contains additional data missing from
            # the JSON object: 1. object_type: the scope of the search
            # result ( global/ local)
            #
            # 2. sync_status: the sync status:
            #  -1 means no operation performed (default),
            #  0 means copy successful
            #  1 means duplicate
            extra_data_dict[json_dict['itemKey']] = {
                'object_type': self.object_type,
                'sync_status': -1,
            }

            processed_json_list.append(json_dict)

        return processed_json_list, extra_data_dict

    def set_item(self, data_dict):
        """ Saves the data_dict of local item to BTW account

        Uses the zotero write API """

        # remove unwanted extras
        try:
            item_type = data_dict.pop('itemType')
        except KeyError:
            pass
        # prepare json
        # 1. get template dict
        # 2. populate it with data dict
        # 3. create the json message

        item_tmplate_url = "https://api.zotero.org/items/new?" + \
                           "itemType=%s"
        template_url = item_tmplate_url % (item_type)

        try:
            res = self.__request(template_url)
        except urllib2.URLError:
            return "cannot create item:error in fetching item template."

        item_template = res.read()

        template_dict = json.loads(item_template)

        if type(template_dict) is dict:
            # copy all mandatory data
            for k in template_dict:
                if k in data_dict:
                    template_dict[k] = data_dict[k]
        else:
            return "cannot create item:error in parsing item template."

        # remove 'notes', 'attachments' they have been deprecated
        # api error response is like:
        # '{"success":{},"unchanged":{},"failed":{"0":{"code":400,"message":
        # "\'notes\' property is no longer supported"}}}'

        if 'notes' in template_dict:
            template_dict.pop('notes')
        if 'attachments' in template_dict:
            template_dict.pop('attachments')

        json_string = JSONEncoder().encode({'items': [template_dict]})

        # prepare url to copy item metadata to BTW account.
        post_url = self.prefix + "%s/items?key=%s" % (self.userid, self.apikey)

        # create the POST using urllib2
        header = {'Content-Type': 'application/json'}

        try:
            res = self.__request(post_url, 'POST', header, json_string)
        except urllib2.URLError:
            return "cannot create item:error in post url: %s" % res

        err, msg = self.__parse_json_response(res.read())

        if err == 0 and res.code == 200:  # item created
            return "OK"
        elif err == 1:
            return msg
        else:
            return "cannot create item:Error: %s, Return Code: %s" % (err, msg)

    def set_attachment(self, data_dict, local_profile_object):
        """ Saves attachment from local account to BTW account

        Uses the zotero write API """

        # 1. download file from the local account.
        # 2. upload the attachment as an item.

        # remove unwanted extras, read utility data
        try:
            file_md5 = data_dict.pop('md5')
            mtime = data_dict.pop('mtime')
            contentType = data_dict.pop('contentType')
            charset = data_dict.pop('charset')
            filename = data_dict.pop('filename')
        except KeyError:
            pass

        if file_md5 is None or mtime is None:
            return "cannot sync attachment: source file missing."

        # replicate the file data from local account

        local_uid = re.sub("^u:|^g:", "", local_profile_object.uid)
        if re.search("^u", local_profile_object.uid):
            prefix = "https://api.zotero.org/users/"
        else:
            prefix = "https://api.zotero.org/groups/"
        file_url_template = prefix + "%s/items/%s/file?key=%s"
        olditem_download_url = file_url_template % (
            local_uid,
            data_dict['itemKey'],
            local_profile_object.api_key)

        res = None
        try:
            res = self.__request(olditem_download_url)
        except urllib2.URLError:
            pass  # res remains None

        if res is None or res.code != 200:
            return("cannot sync attachment: Source file read error.")

        # downloaded file data or
        # alternatively we can get file size from the s3 response headers.
        # 'content-length' header is cost effective.
        else:
            if 'content-length' in res.headers.dict:
                filesize = res.headers.dict['content-length']
            else:
                filesize = len(res.read())

        # from zotero write api:
        # http://www.zotero.org/support/dev/server_api/v2/file_upload
        # 1a) Create a new attachment
        # 2) Get upload authorization

        link_mode = data_dict['linkMode']

        item_tmplate_url = "https://api.zotero.org/items/new?" + \
            "itemType=attachment&linkMode=%s"

        get_url = item_tmplate_url % (link_mode)

        try:
            res = self.__request(get_url)
        except urllib2.URLError:
            return "cannot create attachment:error in fetching item template."

        item_template = res.read()

        template_dict = json.loads(item_template)

        if type(template_dict) is dict:
            # copy all mandatory data
            for k in template_dict:
                if k in data_dict:
                    template_dict[k] = data_dict[k]
        else:
            return "cannot create item:error in parsing item template."

        json_string = JSONEncoder().encode({'items': [template_dict]})

        # prepare url to copy item metadata to BTW account.
        post_url = self.prefix + "%s/items?key=%s" % (self.userid, self.apikey)

        # create the POST using urllib2
        header = {'Content-Type': 'application/json'}

        try:
            res = self.__request(post_url, 'POST', header, json_string)
        except urllib2.URLError:
            return "cannot create item:error in url: %s" % post_url

        err, msg = self.__parse_json_response(res.read())

        if err != 0:
            return "cannot create attachment: Error: %s, Code: %s" % (err,
                                                                      res.code)

        # parse the response to create the atomic upload authorization url

        newitem_key = msg

        auth_url_template = self.prefix + "%s/items/%s/file?key=%s"

        auth_post_url = auth_url_template % (self.userid, newitem_key,
                                             self.apikey)

        auth_form_data_template = "md5=%s&filename=%s&filesize=%s&mtime=%s" + \
            "&contentType=%s&charset=%s"

        post_data = auth_form_data_template % (file_md5, filename, filesize,
                                               mtime, contentType, charset)

        # create the auth POST using urllib2
        auth_headers = {'Content-Type': 'application/x-www-form-urlencoded',
                        'If-None-Match': '*'}

        try:
            res = self.__request(auth_post_url, 'POST', auth_headers,
                                 post_data)
        except urllib2.URLError:
            return "cannot sync attachment: error in authorization: %s" % \
                auth_post_url

        if res.code == 200 and err == 0:
            auth_data = json.loads(res.read())

        # if the entry doesnot exist, upload the file.
        if 'exists' in auth_data and auth_data['exists'] == 1:
            return("OK")
        else:
            return ("cannot sync attachment: API error.")

    def __request(self, url, rtype="GET", headers=None, data=None):
        """
        Issues a HTTP request to zotero website and gets the response.
        """
        if headers is None:
            headers = {}

        headers['Zotero-API-Version'] = '2'

        req = urllib2.Request(url, data if rtype == 'POST' else None,
                              headers)
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            return e

        return response

    def duplicate_drill_down(self, results_dict, source_dict):
        """ drills down the resuls to identify exact duplicates """

        # define other keys apart author, itemType
        # that when equal defines the duplicate
        # there are 3 types of date keys in the item JSON
        # a)date b)accessDate c) pub_date (added by us)
        # this algorithm is set to use the 'date' as the other
        # two are set automatically for each account.

        duplicate_attributes = ['date', 'creators']

        matched_list = []

        for result in results_dict:
            matched_count = 0
            for each in duplicate_attributes:
                if each in result:
                    if result[each] == source_dict[each]:
                        matched_count += 1
                # for non existant keys assume the match to be perfect.
                else:
                    matched_count += 1
            if matched_count == len(duplicate_attributes):
                matched_list.append(result)

        return matched_list

    def __parse_json_response(self, data):
        """ parser for the api response """
        response_dict = json.loads(data)
        keys = response_dict.keys()
        for k in keys:
            if not len(response_dict[k]):
                response_dict.pop(k)

        if 'failed' in response_dict:
            return (response_dict['failed']['0']['code'],
                    response_dict['failed']['0']['message'])

        elif 'success' in response_dict:
            return 0, response_dict['success']['0']

        else:
            return 1, 'internal error'

    def test_keys(self):
        """ tests the zotero keys explicitly """
        search_url = self.__build_search_url("")
        status, response = self.__request(search_url)
        return status, response
