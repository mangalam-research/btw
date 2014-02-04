# django imports
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.cache import get_cache

# python core imports
from base64 import urlsafe_b64encode
import json
import re
import urllib
import urllib2
import logging
from json.encoder import JSONEncoder
from xml.dom import minidom

logger = logging.getLogger(__name__)

CACHED_DATA_VERSION = 1

cache = get_cache('bibliography')

_cached_details = None


# Check if BTW project settings are available
# if not raise exception.
def zotero_settings():
    """Function for retrieving organization-wide zotero account details."""
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

    _cached_details = details
    return _cached_details


class Zotero(object):
    """ Class to provide utility functions for zotero API """

    def __init__(self, api_dict, object_type='local'):
        """ initialize api details from the api_dict """
        try:
            self.full_uid = api_dict['uid']
            self.apikey = api_dict['api_key']
        except KeyError:
            raise ImproperlyConfigured("ZOTERO_SETTINGS improperly set")

        if re.search("^u:", self.full_uid):
            # create the user prefix
            self.prefix = "https://api.zotero.org/users/"
        elif re.search("^g:", self.full_uid):
            # create the group prefix
            self.prefix = "https://api.zotero.org/groups/"
        else:
            raise ImproperlyConfigured("ZOTERO_SETTINGS['uid'] is of "
                                       "the wrong format")
        # use regular expression to strip the uid prefix u:, g:
        self.userid = re.sub("^u:|^g:", "", self.full_uid)
        self.object_type = object_type

    def get_item(self, itemKey):
        # As of 2013/08/28 the server at api.zotero.org does not
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

        search_url = self.prefix + \
            "%s/items?key=%s&format=atom&content=json&itemKey=%s" % \
            (self.userid, self.apikey, itemKey)
        logger.debug("getting item %s", search_url)

        results_list, extra_data_dict = self.get_search_results(search_url)
        assert len(results_list) <= 1
        return results_list[0] if len(results_list) > 0 else None

    def get_search_url(self, field):
        """ Creates the search api url"""
        search_field = urllib.quote(field.lower().strip())
        search_url_template = self.prefix + "%s/items/top?key=%s&format=" + \
            "atom&content=json&q=%s"
        search_url = search_url_template % (self.userid, self.apikey,
                                            search_field)
        return search_url

    def dup_search_url(self, title, item_type):
        """ Creates the search url for identifying duplicates"""
        search_url_template = self.prefix + "%s/items/top?key=%s&format=" + \
            "atom&content=json&itemType=%s&q=%s"
        search_url = search_url_template % (self.userid, self.apikey,
                                            item_type, title)
        return search_url

    def get_search_results(self, url_string):
        """Gets all json objects from the given search url"""
        # 2. perform search
        # a. if result does not exist in cache forcefully fetch from zotero.
        # b. if available in cache, check if got modified for the field.
        # b. if not modified display from cache.
        # c. if modified fetch from zotero, reset key in cache.

        cache_key = urlsafe_b64encode(url_string)

        results_list = version = extras = None

        if cache_key in cache:
            logger.debug("cache hit for key: %s", cache_key)
            cached_data = cache.get(cache_key)

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
            else:
                logger.debug("cache corrupted for key: %s", cache_key)
                logger.debug("deleting key: %s", cache_key)
                cache.delete(cache_key)

        # alway search the modification status.
        headers = {'If-Modified-Since-Version': version}

        err, res = self.__create_request(url=url_string, headers=headers)

        if err == 1:
            logger.debug('search url not working')
            # return a empty search result for error in fetching url.
            if results_list:
                logger.debug('serving cached')
                return results_list, extras
            logger.debug('serving empty')
            return [], {}

        elif res.code == 304:
            logger.debug("got 'not modified' for key: %s", cache_key)
            if results_list:
                logger.debug('serving cached')
                return results_list, extras
            logger.debug('serving empty')
            return [], {}

        elif res.code != 200:
            # return a empty search result for error in fetching url.
            return []

        logger.debug('serving latest (cache stale or cache miss) for key: %s',
                     cache_key)
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
        if version_key:
            # cache the results before returning.
            cache.set(cache_key,
                      (CACHED_DATA_VERSION, results_list, version_key,
                       extra_data_dict))
            logger.debug("cache set for key: %s", cache_key)

        return results_list, extra_data_dict

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

        #remove unwanted extras
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

        err, res = self.__create_request(template_url)

        if err == 1:
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

        err, res = self.__create_request(post_url, 'POST', header, json_string)

        if err == 1:
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

        #remove unwanted extras, read utility data
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

        err, res = self.__create_request(olditem_download_url)

        if err == 1 or res.code != 200:
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

        err, res = self.__create_request(get_url)

        if err == 1:
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

        err, res = self.__create_request(post_url, 'POST', header, json_string)

        if err == 1:
            return "cannot create item:error in url: %s" % res

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

        err, res = self.__create_request(auth_post_url, 'POST',
                                         auth_headers, post_data)
        if err == 1:
            return "cannot sync attachment:error in authorization: %s" % res

        if res.code == 200 and err == 0:
            auth_data = json.loads(res.read())

        # if the entry doesnot exist, upload the file.
        if 'exists' in auth_data and auth_data['exists'] == 1:
            return("OK")
        else:
            return ("cannot sync attachment: API error.")

    def __create_request(self, url, rtype="GET", headers=None, data=None):
        """ creates a http request to zotero website and gets response """
        if headers is None:
            headers = {}

        handler = urllib2.HTTPSHandler
        opener = urllib2.build_opener(handler)
        if re.search("zotero.org", url):
            # url must be for zotero api interactions, add header
            headers['Zotero-API-Version'] = '2'

        try:
            if rtype == 'POST':
                post_data = data
                req = urllib2.Request(url, post_data, headers)
            else:
                req = urllib2.Request(url, None, headers)

            response = opener.open(req)

        except urllib2.HTTPError, e:
            return 0, e
        except urllib2.URLError, e:
            return 1, e
        return 0, response

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
        search_url = self.get_search_url("")
        status, response = self.__create_request(search_url)
        return status, response
