# python imports
import urllib

# django imports
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseServerError
from django.template import Context, loader, RequestContext
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# module imports
from .utils import Zotero, btwZoteroDetails
from .models import ZoteroUser
from .forms import SearchForm

# CONSTANTS
try:
    PAGINATION_SIZE = getattr(settings, "SEARCH_PAGINATION_SIZE")
except AttributeError:
    PAGINATION_SIZE = 10

from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
def search(request):
    """ dashboard home view, in case user is not logged in

    present login required error """

    if request.user.is_authenticated():
        # For authenticated users:
        # If the user profile is not created show the profileUpdate view
        # or show dashboard for authenticated users.
        try:
            local_profile_object = ZoteroUser.objects.get(btw_user=request.user)
        except ObjectDoesNotExist:
            return HttpResponseServerError("users local profile not created.")

        # if request is ajax, process the sarch query and get results
        # otherwise present the Search Form.
        if request.is_ajax():
            # 1. from GET dictionary prepare:
            # a. the zotero library to search info from.
            # b. the keyword to search zotero for.

            # 2. perform search
            # a. see if the search got modified for the field
            # b. if not fetch from cache.
            # c. if modified fetch from zotero, reset key in cache
            # d. if result doesnot exist in cache forcefully fetch.

            query_dict = request.GET

            if 'library' not in query_dict or 'keyword' not in query_dict:
                return HttpResponseServerError("Form data empty.")

            btw_api_dict = btwZoteroDetails()

            local_api_dict = {'uid': local_profile_object.uid, 'api_key':
                              local_profile_object.api_key}

            results_list = []
            extra_data = {}
            try:
                if int(query_dict['library']) in (2, 3):
                    # evaluate the results from local account
                    l_obj = Zotero(local_api_dict, "User Library")

                    search_url = l_obj.getSearchUrl(query_dict['keyword'])
                    print "searching url:", search_url
                    search_results, extra_vars = l_obj.getSearchResults(
                        search_url)
                    # update data
                    results_list.extend(search_results)
                    extra_data.update(extra_vars)

                if int(query_dict['library']) in (1, 3):
                    # evaluate the results from the global account
                    g_obj = Zotero(btw_api_dict, 'BTW Library')

                    search_url = g_obj.getSearchUrl(query_dict['keyword'])
                    print "searching url:", search_url
                    search_results, extra_vars = g_obj.getSearchResults(
                        search_url)

                    # update data
                    results_list.extend(search_results)
                    extra_data.update(extra_vars)

            except ValueError:
                return HttpResponseServerError("Malformed form data.")

            # append the results_list to the user's session
            # as the keyword changes, the result changes
            # when user's session is invalidated, the data too is cleaned.
            request.session['results_list'] = results_list
            request.session['extra_data'] = extra_data
            #print "ajax update fired"

            # redirect to pagination url for returning the results first time.
            return HttpResponseRedirect('/search/results/')

        else:
            # present a unbounded form.
            form = SearchForm()
            template = loader.get_template('bibsearch/search.html')
            context = RequestContext(request, {'form': form})
            return HttpResponse(template.render(context))
    else:
        return HttpResponseServerError("Please Login to your account.")


def results(request):
    """ pagination logic for the search results """

    results_list = request.session.get('results_list')
    extra_data = request.session.get('extra_data')

    if type(results_list) is list:
        # print "start paginating the results"
        paginator = Paginator(results_list, PAGINATION_SIZE)
        page = request.GET.get('page')
        try:
            results = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            results = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 999), deliver last page of results.
            results = paginator.page(paginator.num_pages)

        template = loader.get_template('bibsearch/results.html')
        context = Context({
            'results': results,
            'extras': extra_data,
        })
        return HttpResponse(template.render(context))

    return HttpResponseServerError('Search error.')


def sync(request):
    """ Sync the given json string to BTW project.

    Sync has two steps :
    1) search (Item type, title ) if not with BTW project
    2) sync(write) if new item otherwise,
    3) mark it duplicate."""

    if request.user.is_authenticated():

        results_list = request.session.get('results_list')
        enc_string = request.GET.get('enc')

        if type(enc_string) is unicode and type(results_list) is list:
            data_dict = None
            for result in results_list:
                if 'itemKey' in result and result['itemKey'] == enc_string:
                    data_dict = result
                    break

            else:
                if len(enc_string) == 0:
                    return HttpResponseServerError(
                        "Error: malformed data cannot be copied.")
                return HttpResponse(
                    "Error: Item not in result database.")

            title = data_dict.get('title')
            item_type = data_dict.get('itemType')

            # search for duplicate
            btw_api_dict = btwZoteroDetails()
            sync_obj = Zotero(btw_api_dict, "BTW Library")
            search_url = sync_obj.dupSearchUrl(urllib.quote(title.lower()
                                                            ), item_type)

            print "searching duplicates from url:", search_url

            search_results, extras = sync_obj.getSearchResults(search_url)

            dup_results = sync_obj.duplicateDrillDown(
                search_results, data_dict)

            if len(dup_results) == 0:
                local_profile_object = ZoteroUser.objects.get(
                    btw_user=request.user)
                if item_type == u'attachment':
                    # call setAttachment
                    res = sync_obj.setAttachment(data_dict,
                                                 local_profile_object)

                else:
                    # call setItem
                    res = sync_obj.setItem(data_dict)

                # do additional steps to manupulate bibsearch_sync_status to 0
                if res == "OK":
                    extra_dict = request.session.pop('extra_data')
                    if enc_string in extra_dict:
                        extra_dict[enc_string]['sync_status'] = 0
                    # restore the extra dictionary
                    request.session['extra_data'] = extra_dict

                return HttpResponse(res)

            else:
                extra_dict = request.session.pop('extra_data')
                if enc_string in extra_dict:
                    extra_dict[enc_string]['sync_status'] = 1
                # restore the extra dictionary
                request.session['extra_data'] = extra_dict

                return HttpResponse("DUP")

        return HttpResponseServerError("ERROR: sync data i/o error.")
    else:
        return HttpResponseServerError("ERROR: User not logged in.")


def testjs(request):
    """ Qunit tests view """
    template = loader.get_template('bibsearch/Qtests.html')
    context = RequestContext(request)
    return HttpResponse(template.render(context))
