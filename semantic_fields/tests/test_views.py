import urllib.request
import urllib.parse
import urllib.error
import json
from unittest import mock

from django.urls import reverse
from django.test.utils import override_settings
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import translation
from django.utils.datastructures import MultiValueDictKeyError
from django.conf import settings
from django_webtest import WebTest, TransactionWebTest
from django.middleware.csrf import _get_new_csrf_token
from cms.test_utils.testcases import BaseCMSTestCase
from nose.tools import nottest

from .util import MinimalQuery, FakeChangeRecord
from ..models import SemanticField, SearchWord, Lexeme
from ..serializers import SemanticFieldSerializer
from lib import util
from lib.testutil import wipd

user_model = get_user_model()

def _make_test_url(sf):
    return "http://testserver" + sf.detail_url

FAKE_CSRF = _get_new_csrf_token()

class _Mixin(object):

    def setUp(self):
        super(_Mixin, self).setUp()
        translation.activate('en-us')

    # This exists so that we can use setUpTestData and setUp later.
    @classmethod
    def create_data_for(cls, whom):
        whom.noperm = user_model.objects.create(username="foo", password="foo")
        whom.perm = user_model.objects.create(username="bar", password="bar")
        whom.perm.user_permissions.add(Permission.objects.get(
            content_type=ContentType.objects.get_for_model(SemanticField),
            codename="add_semanticfield"))
        whom.perm.user_permissions.add(Permission.objects.get(
            content_type=ContentType.objects.get_for_model(SemanticField),
            codename="change_semanticfield"))
        whom.perm.save()

        # Not a test proper... but make sure that what we expect is
        # the case.
        assert whom.perm.can_add_semantic_fields


@override_settings(ROOT_URLCONF='semantic_fields.tests.urls')
class ViewsTestCase(BaseCMSTestCase, _Mixin, util.DisableMigrationsMixin,
                    WebTest):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.create_data_for(cls)
        super(ViewsTestCase, cls).setUpTestData()

@override_settings(ROOT_URLCONF='semantic_fields.tests.urls')
class ViewsTransactionTestCase(BaseCMSTestCase, _Mixin,
                               util.DisableMigrationsTransactionMixin,
                               TransactionWebTest):

    def setUp(self):
        super(ViewsTransactionTestCase, self).setUp()
        self.create_data_for(self)


class MainTestCase(ViewsTestCase):

    @classmethod
    def setUpTestData(cls):
        super(MainTestCase, cls).setUpTestData()
        cls.url = reverse("semantic_fields_main")
        cls.login_url = reverse('login')

    def test_not_logged_in(self):
        """
        Test that the response is a redirection to the login page when the
        user is not logged in.
        """
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, self.login_url + "?" +
                             urllib.parse.urlencode({"next": self.url}))

    def test_logged_in(self):
        """
        Test that the response shows a page
        """
        self.app.get(self.url, user=self.noperm)

    def create_field_button(self, response):
        els = response.lxml.cssselect(".btn.create-field")
        return els[0] if els else None

    def test_creation_possible(self):
        """
        Test that when a user with adequate permissions sees the page, the
        user can create new semantic fields.
        """
        response = self.app.get(self.url, user=self.perm)
        self.assertIsNotNone(self.create_field_button(response),
                             "the button for creating fields should exist")

    def test_creation_not_possible(self):
        """
        Test that when a user without adequate permissions sees the page,
        the user can create new semantic fields.
        """
        response = self.app.get(self.url, user=self.noperm)
        self.assertIsNone(self.create_field_button(response),
                          "the button for creating fields should exist")


class ParameterChecksMixin(object):

    def scope_check(self, scope, headings):
        """
        Test that setting the scope produces correct results.
        """
        hte = SemanticField(path="01n", heading="hte", catid="1")
        hte.save()

        nonhte = SemanticField(path="02n", heading="nonhte")
        nonhte.save()

        self.make_request_and_check({
            "search[value]": "h",
            "scope": scope,
            "aspect": "sf",
            "root": "all",
        }, total=2, headings=headings)

    def aspect_check(self, aspect, headings):
        """
        Test that setting the root produces correct results.
        """
        cat1 = SemanticField(path="01n", heading="term")
        cat1.save()

        cat2 = SemanticField(path="02n", heading="aaaa")
        cat2.save()

        lexeme = Lexeme(htid=1, semantic_field=cat2, word="term",
                        fulldate="q", catorder=0)
        lexeme.save()

        word = SearchWord(sid=1, htid=lexeme, searchword="term", type="oed")
        word.save()

        self.make_request_and_check({
            "search[value]": "term",
            "scope": "all",
            "aspect": aspect,
            "root": "all",
        }, total=2, headings=headings)

    def root_check(self, root, headings):
        """
        Test that setting the root produces correct results.
        """
        cat1 = SemanticField(path="01n", heading="term one")
        cat1.save()

        cat2 = SemanticField(path="01.01n", heading="term two", parent=cat1)
        cat2.save()

        cat3 = SemanticField(path="02.02n", heading="term three")
        cat3.save()

        self.make_request_and_check({
            "search[value]": "term",
            "scope": "all",
            "aspect": "sf",
            "root": root,
        }, total=3, headings=headings)

    @staticmethod
    @nottest
    def make_tests(c):
        for (scope_setting, headings) in (("all", ["hte", "nonhte"]),
                                          ("hte", ["hte"]),
                                          ("btw", ["nonhte"])):
            makefunc(c, c.scope_check, "test_scope_" + scope_setting,
                     scope_setting, scope_setting, headings)

        for (aspect_setting, headings) in (("sf", ["term"]),
                                           ("lexemes", ["aaaa"])):
            makefunc(c, c.aspect_check, "test_aspect_" + aspect_setting,
                     aspect_setting, aspect_setting, headings)

        for (root_setting, headings) in (("all", ["term one", "term two",
                                                  "term three"]),
                                         ("01", ["term one", "term two"]),
                                         ("02", ["term three"])):
            makefunc(c, c.root_check, "test_root_" + root_setting,
                     root_setting, root_setting, headings)

class SearchTableTestCase(ParameterChecksMixin, ViewsTestCase):

    @classmethod
    def setUpTestData(cls):
        super(SearchTableTestCase, cls).setUpTestData()
        cls.url = reverse("semantic_fields_table")
        cls.complete_params = {
            "search[value]": "foo",
            "aspect": "sf",
            "scope": "all",
            "root": "all",
        }

    def test_not_logged_in(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        response = self.app.get(self.url, expect_errors=True)
        self.assertEqual(response.status_code, 403)

    # pylint: disable=redefined-outer-name
    def missing_parameter(self, param):
        """
        Test that an error is raised if the parameter is missing.
        """
        params = dict(self.complete_params)
        del params[param]
        with self.assertRaisesRegex(MultiValueDictKeyError, param):
            self.app.get(self.url, params=params, user=self.noperm)

    def bad_value(self, param):
        """
        Test that an error is raised if the parameter has an incorrect
        value.
        """
        params = dict(self.complete_params)
        params[param] = "INCORRECT!!!"
        with self.assertRaisesRegex(ValueError,
                                    "unknown value for {}: INCORRECT!!!"
                                    .format(param)):
            self.app.get(self.url, params=params, user=self.noperm)

    def make_request_and_check(self, params, total, headings):
        response = self.app.get(self.url,
                                params=params,
                                user=self.noperm)

        self.assertDataTablesResponse(response, total=total, names=headings)

    def test_correct_params(self):
        """
        Test that a query with the correct params does not return an error.
        """
        response = self.app.get(self.url, params=self.complete_params,
                                user=self.noperm)
        self.assertEqual(response.json["result"], "ok")

    def assertDataTablesResponse(self, response, total, names):
        # Testing more than just ``data`` helps deal with possible
        # surprises.
        json = response.json
        self.assertEqual(json["recordsTotal"], total)
        self.assertEqual(json["recordsFiltered"], len(names))

        headings = \
            ["<p>" +
             SemanticField.objects.get(heading=name).linked_breadcrumbs +
             "</p>"
             for name in names]

        self.assertCountEqual([row[1] for row in json["data"]], headings)

    def test_exact_search(self):
        """
        Test that using quotes in a search results in an exact search.
        """
        hte = SemanticField(path="01n", heading="term")
        hte.save()

        nonhte = SemanticField(path="02n", heading="non-terminal")
        nonhte.save()

        response = self.app.get(self.url,
                                params={
                                    "search[value]": '"term"',
                                    "scope": "all",
                                    "aspect": "sf",
                                    "root": "all",
                                },
                                user=self.noperm)

        self.assertDataTablesResponse(response, total=2, names=["term"])

def makefunc(class_, f, name, docstring, *params):
    def l(self):
        f(self, *params)
    l.__name__ = name
    l.__doc__ = "{0} ({1})".format(f.__doc__, docstring)
    setattr(class_, l.__name__, l)


#
# Here we generate and add tests to the class. We cannot use
# generators. Nose by itself allows it but in Django's test system
# they just end up being ignored (yes, even with django-nose).
#
# We do it in a function so as to avoid polluting the top level space.
#
def init():
    c = SearchTableTestCase

    for param in ("aspect", "scope", "root"):
        makefunc(c, c.missing_parameter, "test_missing_" + param,
                 param, param)

        makefunc(c, c.bad_value, "test_bad_" + param, param, param)

    ParameterChecksMixin.make_tests(c)

init()

class DetailsTestCaseHTML(ViewsTestCase):

    @classmethod
    def setUpTestData(cls):
        super(DetailsTestCaseHTML, cls).setUpTestData()
        cls.hte = hte = SemanticField(path="01n", heading="hte", catid="1")
        hte.save()
        cls.custom = custom = SemanticField(path="/1n", heading="custom")
        custom.save()

    def test_not_logged_in(self):
        """
        Test that users that are not logged in can access the page.
        """
        self.app.get(self.hte.detail_url)

    def query(self, url, user):
        return self.app.get(url,
                            headers={"Accept": "text/html"},
                            user=user)

    def related_by_pos_button(self, response):
        els = response.lxml.cssselect(".btn.create-related-by-pos")
        return els[0] if els else None

    def create_child_button(self, response):
        els = response.lxml.cssselect(".btn.create-child")
        return els[0] if els else None

    def test_creation_possible_custom_field(self):
        """
        Test that when a user with adequate permissions sees the page, the
        user can create new semantic fields.
        """
        response = self.query(self.custom.detail_url, self.perm)
        self.assertIsNotNone(self.create_child_button(response),
                             "the button for creating children should exist")
        self.assertIsNotNone(
            self.related_by_pos_button(response),
            "the button for creating related-by-pos should exist")

    def test_creation_possible_hte_field(self):
        """
        Test that when a user with adequate permissions sees the page, the
        user can create new semantic fields. However, for a HTE field,
        the button to create related by pos fields is not present.
        """
        response = self.query(self.hte.detail_url, self.perm)
        self.assertIsNotNone(self.create_child_button(response),
                             "the button for creating children should exist")
        self.assertIsNone(
            self.related_by_pos_button(response),
            "the button for creating related-by-pos should not exist")

    def test_creation_not_possible(self):
        """
        Test that when a user without adequate permissions sees the page, the
        user cannot create new semantic fields.
        """
        response = self.query(self.custom.detail_url, self.noperm)
        self.assertIsNone(self.create_child_button(response),
                          "the button for creating children should not exist")
        self.assertIsNone(
            self.related_by_pos_button(response),
            "the button for creating related-by-pos should not exist")

    def test_hte_link(self):
        """
        Test that a link to the HTE site appears only for HTE semantic fields.
        """
        selector = "a[title='Open on HTE site.']"

        response = self.query(self.hte.detail_url, self.noperm)
        self.assertEqual(len(response.lxml.cssselect(selector)), 1,
                         "the URL linking to the HTE site should exist")

        nonhte = SemanticField(path="02n", heading="nonhte")
        nonhte.save()
        response = self.query(nonhte.detail_url, self.noperm)
        self.assertEqual(len(response.lxml.cssselect(selector)), 0,
                         "the URL linking to the HTE site should not exist")

    def test_related_by_pos(self):
        """
        Test that fields related by pos appear if they exist.
        """
        selector = "span.sf-other-pos"

        response = self.query(self.hte.detail_url, self.noperm)
        self.assertEqual(len(response.lxml.cssselect(selector)), 0,
                         "there should be no listing of other pos")

        sibling = SemanticField(path="01aj", heading="sibling")
        sibling.save()

        response = self.query(self.hte.detail_url, self.noperm)
        self.assertEqual(
            len(response.lxml.cssselect("{0} a".format(selector))), 1,
            "there should be a listing of exactly one other pos")

        self.assertEqual(
            len(response.lxml.cssselect(
                "{0} a[href='{1}']".format(selector, sibling.detail_url))),
            1,
            "there should be a link to the sibling")

    def test_lexemes(self):
        """
        Test that lexemes appear if they exist.
        """

        selector = "span.sf-lexemes"

        response = self.query(self.hte.detail_url, self.noperm)
        self.assertEqual(len(response.lxml.cssselect(selector)), 0,
                         "there should be no listing of lexemes")

        other = SemanticField(path="02n", heading="other")
        other.save()

        lexeme = Lexeme(htid=1, semantic_field=self.hte, word="foo",
                        fulldate="q", catorder=0)
        lexeme.save()
        lexeme2 = Lexeme(htid=2, semantic_field=self.hte, word="bar",
                         fulldate="q", catorder=1)
        lexeme2.save()

        # Create an unrelated lexeme which will not appear in the list.
        lexeme3 = Lexeme(htid=3, semantic_field=other, word="x", fulldate="q",
                         catorder=0)
        lexeme3.save()

        response = self.query(self.hte.detail_url, self.noperm)
        # Get only the text.
        lexemes = [x.text for x in
                   response.lxml.cssselect("{0} .label".format(selector))]
        self.assertCountEqual(lexemes,
                              ["foo q", "bar q"],
                              "there should be two lexemes with the right "
                              "values")

    def test_children(self):
        """
        Test that children appear if they exist.
        """
        selector = "span.sf-children"

        response = self.query(self.hte.detail_url, self.noperm)
        self.assertEqual(len(response.lxml.cssselect(selector)), 0,
                         "there should be no listing of children")

        hte = self.hte

        child1 = hte.make_child(heading="child 1", pos="n")
        child2 = hte.make_child(heading="child 2", pos="n")

        expected = [{"text": x.heading, "href": x.detail_url} for x in
                    (child1, child2)]

        other = SemanticField(path="02n", heading="other")
        other.save()
        other.make_child(heading="child other", pos="n")

        response = self.query(self.hte.detail_url, self.noperm)
        children = [{"text": x.text, "href": x.get("href")}
                    for x in response.lxml.cssselect("{0} a".format(selector))]

        self.assertEqual(children, expected,
                         "there should be the expected children")

class DetailsTestCaseJSON(ViewsTestCase):

    @classmethod
    def setUpTestData(cls):
        super(DetailsTestCaseJSON, cls).setUpTestData()
        cls.hte = hte = SemanticField(path="01n", heading="hte", catid="1")
        hte.save()

    def test_not_logged_in(self):
        """
        Test that users that are not logged in can access the view.
        """
        self.app.get(self.hte.detail_url)

    def test_logged_in(self):
        """
        Test that a logged in user gets a response.
        """
        response = self.app.get(_make_test_url(self.hte), user=self.perm)
        self.assertEqual(
            response.json,
            {
                "url": _make_test_url(self.hte),
                "path": "01n",
                "heading": "hte",
                "heading_for_display": "hte",
                "verbose_pos": "Noun",
                "is_subcat": False,
            },
            "the returned value should be correct")

class _AjaxMixin(object):

    ajax_bad_accept = "text/xml"

    @property
    def ajax_method(self):
        return self.app.get

    @property
    def ajax_params(self):
        return {}

    def test_not_logged_in(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        response = self.ajax_method(self.url, expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def test_no_permissions(self):
        """
        Test that a user without permission to add semantic fields cannot
        get the form.
        """
        response = self.ajax_method(self.url, user=self.noperm,
                                    expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def test_bad_accept(self):
        """
        Test that a user who specifies the wrong content type gets an error.
        """
        # Getting the params is done by performing a request to the server,
        # which also populates the cookies.
        params = self.ajax_params
        headers = {
            "Accept": self.ajax_bad_accept,
        }

        csrftoken = self.app.cookies.get('csrftoken')
        if csrftoken:
            headers["X-CSRFToken"] = csrftoken

        response = self.ajax_method(self.url, user=self.perm,
                                    headers=headers,
                                    params=params,
                                    expect_errors=True)
        self.assertEqual(response.status_code, 406)


class _FormTestCase(_AjaxMixin, ViewsTestCase):
    # Make sure json is not accepted
    ajax_bad_accept = "application/json"

    def test_response(self):
        """
        Test that a user who specifies no content type gets HTML.
        """
        response = self.app.get(self.url, user=self.perm)
        self.assertEqual(response.content_type, "text/html")

class AddChildFormTestCase(_FormTestCase):

    @classmethod
    def setUpTestData(cls):
        super(AddChildFormTestCase, cls).setUpTestData()
        hte = SemanticField(path="01n", heading="hte", catid="1")
        hte.save()
        cls.url = hte.add_child_form_url


class AddFormTestCase(_FormTestCase):

    @classmethod
    def setUpTestData(cls):
        super(AddFormTestCase, cls).setUpTestData()
        cls.url = reverse('semantic_fields_semanticfield-add-form')

class AddRelatedByPosFormTestCase(_FormTestCase):

    @classmethod
    def setUpTestData(cls):
        super(AddRelatedByPosFormTestCase, cls).setUpTestData()
        hte = SemanticField(path="/1n", heading="hte")
        hte.save()
        cls.url = hte.add_related_by_pos_form_url

class EditFormTestCase(_FormTestCase):

    @classmethod
    def setUpTestData(cls):
        super(EditFormTestCase, cls).setUpTestData()
        hte = SemanticField(path="/1n", heading="hte")
        hte.save()
        cls.url = hte.edit_form_url

class _CreateMixin(_AjaxMixin):
    ajax_bad_accept = "text/xml"

    @property
    def ajax_method(self):
        return self.app.post

    @property
    def ajax_params(self):
        response = self.app.get(self.form_url, user=self.perm)
        self.assertEqual(response.status_code, 200)
        form = response.form
        form["heading"] = "q"
        form["pos"] = "n"
        return form.submit_fields()

    def heading_required(self, accept):
        """
        Test that creating a new field without a heading yields an error.
        """
        self.assertCreatedCount(0)
        response = self.app.get(self.form_url, user=self.perm)
        self.assertEqual(response.status_code, 200)
        form = response.form
        form["heading"] = ""
        form["pos"] = "n"

        response = self.app.post(
            self.url,
            headers={
                "Accept": accept,
            },
            params=form.submit_fields(),
            user=self.perm, expect_errors=True)
        expected_content_type = {
            "application/x-form": "text/html",
            "application/json": "application/json"
        }[accept]
        self.assertEqual(response.content_type, expected_content_type)
        error = "This field is required."
        if expected_content_type == "text/html":
            el = response.lxml.cssselect(".help-block")[0]
            self.assertEqual("".join(el.itertext()).strip(), error)
        elif expected_content_type == "application/json":
            self.assertEqual(response.json, {"heading": [error]})
        else:
            raise ValueError("unexpected expected_content_type value: " +
                             expected_content_type)

        # Check again that there are no children.
        self.assertCreatedCount(0)

    def incorrect_pos(self, accept):
        """
        Test that creating a new field with an incorrect pos yields an
        error.
        """
        self.assertCreatedCount(0)
        response = self.app.get(self.form_url, user=self.perm)
        self.assertEqual(response.status_code, 200)
        form = response.form
        form["heading"] = "foo"
        form["pos"].force_value("xxxxxx")

        response = self.app.post(
            self.url,
            headers={
                "Accept": accept,
            },
            params=form.submit_fields(),
            user=self.perm, expect_errors=True)
        expected_content_type = {
            "application/x-form": "text/html",
            "application/json": "application/json"
        }[accept]
        self.assertEqual(response.content_type, expected_content_type)
        error = \
            "Select a valid choice. xxxxxx is not one of the " \
            "available choices."
        if expected_content_type == "text/html":
            el = response.lxml.cssselect(".help-block")[0]
            self.assertEqual("".join(el.itertext()).strip(), error)
        elif expected_content_type == "application/json":
            self.assertEqual(response.json, {"pos": [error]})
        else:
            raise ValueError("unexpected expected_content_type value: " +
                             expected_content_type)

        # Check again that there are no children.
        self.assertCreatedCount(0)

    def creation_successful(self, accept):
        """
        Test that a user can create a new semantic field.
        """
        self.assertCreatedCount(0)
        response = self.app.get(self.form_url, user=self.perm)
        self.assertEqual(response.status_code, 200)
        form = response.form
        form["heading"] = "foo"
        form["pos"] = "n"

        response = self.app.post(
            self.url,
            headers={
                "Accept": accept,
            },
            params=form.submit_fields(),
            user=self.perm)
        self.assertIsNone(response.content_type)
        self.assertEqual(response.body, b"")

        self.assertCreatedCount(1)
        self.checkCreated()


class _DuplicateMixin(object):

    def duplicate(self, accept):
        """
        Test that creating a duplicate field yields an error.
        """

        response = self.app.get(self.form_url, user=self.perm)
        self.assertEqual(response.status_code, 200)
        form = response.form
        form["heading"] = "DUPLICATE"
        form["pos"] = ""

        # We want to have the duplicate creation here to simulate the
        # case where a user got the form, when for coffee, and came
        # back. And in the meantime someone created a field that would
        # clash with the field the user wants to create. (We have to
        # do this because forms will sometimes restrict options. So if
        # we create the duplicate *before* we get the form, we may get
        # a form error instead of the error we are looking for below.)
        self.create_duplicate()
        orig_count = self.assertCreatedCount(1)

        response = self.app.post(
            self.url,
            headers={
                "Accept": accept,
            },
            params=form.submit_fields(),
            user=self.perm, expect_errors=True)
        expected_content_type = {
            "application/x-form": "text/html",
            "application/json": "application/json"
        }[accept]
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content_type, expected_content_type)
        error = self.expected_duplicate_error
        if expected_content_type == "text/html":
            import lxml
            el = response.lxml.cssselect(".alert")[0]
            self.assertEqual("".join(el.itertext()).replace(
                "\xd7", "").strip(), error)
        elif expected_content_type == "application/json":
            self.assertEqual(response.json, {"__all__": [error]})
        else:
            raise ValueError("unexpected expected_content_type value: " +
                             expected_content_type)

        # Check again that nothing was created after the original.
        self.assertCreatedCount(orig_count)


class _CreateFromParentMixin(_CreateMixin, _DuplicateMixin):
    # Creation from a parent requires significantly different tests
    # than creation from a related field so we put those common to
    # parrents here.

    expected_duplicate_error = \
        "There is already a semantic field in the BTW namespace "\
        "without pos and heading 'DUPLICATE'."

    def assertCreatedCount(self, count):
        field = self.field
        children = field.children if field else SemanticField.objects.roots
        self.assertEqual(children.count(), count)
        return count

    def create_duplicate(self):
        field = self.field
        if field:
            field.make_child("DUPLICATE", "")
        else:
            SemanticField.objects.make_field("DUPLICATE", "")

    def checkCreated(self):
        field = self.field  # Reacquire from DB.
        children = field.children if field else SemanticField.objects.roots
        child = children.first()
        self.assertEqual(child.parent, field)
        self.assertEqual(child.path, (field.path if field else "") + "/1n")
        self.assertEqual(child.heading, "foo")
        self.assertIsNone(child.catid)
        self.assertEqual(child.children.count(), 0)


class CreateChildTestCase(_CreateFromParentMixin, ViewsTestCase):

    def setUp(self):
        super(CreateChildTestCase, self).setUp()
        hte = SemanticField(path="01n", heading="hte", catid="1")
        hte.save()
        self.field_id = hte.id

        self.url = hte.add_child_url
        self.form_url = hte.add_child_form_url

    @property
    def field(self):
        return SemanticField.objects.get(id=self.field_id)


class CreateFieldTestCase(_CreateFromParentMixin, ViewsTestCase):

    def setUp(self):
        super(CreateFieldTestCase, self).setUp()
        self.field = None
        self.url = reverse('semantic_fields_semanticfield-list')
        self.form_url = reverse('semantic_fields_semanticfield-add-form')


class _CreateRelatedByPosMixin(object):

    def setUp(self):
        super(_CreateRelatedByPosMixin, self).setUp()
        field = SemanticField(path="/1v", heading="custom")
        field.save()
        self.field_id = field.id

        self.url = field.add_related_by_pos_url
        self.form_url = field.add_related_by_pos_form_url

    @property
    def field(self):
        return SemanticField.objects.get(id=self.field_id)

    def assertCreatedCount(self, count):
        self.assertEqual(self.field.related_by_pos.count(), count)
        return count

    def create_duplicate(self):
        self.field.make_related_by_pos("DUPLICATE", "")

    def checkCreated(self):
        field = self.field
        n_variants = [x for x in self.field.related_by_pos if x.pos == "n"]
        self.assertEqual(len(n_variants), 1)
        rel = n_variants[0]
        self.assertEqual(rel.parent, field.parent)
        self.assertEqual(rel.path, "/1n")
        self.assertEqual(rel.heading, "foo")
        self.assertIsNone(rel.catid)
        self.assertEqual(rel.children.count(), 0)


class CreateRelatedByPosTestCase(_CreateRelatedByPosMixin, _CreateMixin,
                                 ViewsTestCase):
    pass


class CreateRelatedByPosTransactionTestCase(_CreateRelatedByPosMixin,
                                            _DuplicateMixin,
                                            ViewsTransactionTestCase):
    expected_duplicate_error = \
        "There is already a semantic field in the BTW namespace "\
        "without pos."


def init():
    def make(class_, test, accept):
        makefunc(class_, getattr(class_, test),
                 "test_{0}_{1}".format(test, accept), accept, accept)

    for accept in ("application/json", "application/x-form"):
        for test in ("heading_required", "incorrect_pos",
                     "creation_successful"):
            make(_CreateMixin, test, accept)

        make(_DuplicateMixin, "duplicate", accept)

init()

class EditTestCase(_AjaxMixin, ViewsTestCase):
    ajax_bad_accept = "text/xml"

    @property
    def ajax_method(self):
        return self.app.put

    @property
    def ajax_params(self):
        response = self.app.get(self.form_url, user=self.perm)
        self.assertEqual(response.status_code, 200)
        form = response.form
        form["heading"] = "q"
        return form.submit_fields()

    @classmethod
    def setUpTestData(cls):
        super(EditTestCase, cls).setUpTestData()

        hte = SemanticField(path="/1n", heading="custom")
        hte.save()
        cls.field_id = hte.id

        cls.url = hte.edit_url
        cls.form_url = hte.edit_form_url

    def edit_successful(self, accept):
        """
        Test that a user can edit a semantic field.
        """
        response = self.app.get(self.form_url, user=self.perm)
        self.assertEqual(response.status_code, 200)
        form = response.form
        self.assertEqual(form["heading"].value, "custom")
        form["heading"] = "changed"

        response = self.app.put(
            self.url,
            headers={
                "Accept": accept,
                "X-CSRFToken": self.app.cookies["csrftoken"]
            },
            params=form.submit_fields(),
            user=self.perm)
        self.assertIsNone(response.content_type)
        self.assertEqual(response.body, b"")

        field = SemanticField.objects.get(id=self.field_id)
        self.assertEqual(field.heading, "changed")

    def cannot_change_pos(self, accept):
        """
        Test that a user cannot edit the pos.
        """
        response = self.app.get(self.form_url, user=self.perm)
        self.assertEqual(response.status_code, 200)

        response = self.app.put(
            self.url,
            headers={
                "Accept": accept,
                "X-CSRFToken": self.app.cookies["csrftoken"]
            },
            params=(('heading', 'changed'), ('pos', 'v')),
            user=self.perm, expect_errors=True)
        expected_content_type = {
            "application/x-form": "text/html",
            "application/json": "application/json"
        }[accept]
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content_type, expected_content_type)
        error = ("it is not possible to change the part of speech "
                 "of a field after creation")
        if expected_content_type == "text/html":
            el = response.lxml.cssselect(".alert")[0]
            self.assertEqual(el.text.strip(), error)
        elif expected_content_type == "application/json":
            self.assertEqual(response.json, {"__all__": [error]})
        else:
            raise ValueError("unexpected expected_content_type value: " +
                             expected_content_type)

        # Check that it has not changed.
        field = SemanticField.objects.get(id=self.field_id)
        self.assertEqual(field.heading, "custom")
        self.assertEqual(field.pos, "n")

def init():
    def make(class_, test, accept):
        makefunc(class_, getattr(class_, test),
                 "test_{0}_{1}".format(test, accept), accept, accept)

    for accept in ("application/json", "application/x-form"):
        for test in ("edit_successful", ):
            make(EditTestCase, test, accept)

init()

class ListTestCase(ViewsTestCase):

    @classmethod
    def setUpTestData(cls):
        super(ListTestCase, cls).setUpTestData()
        cls.url = reverse("semantic_fields_semanticfield-list")

        cat1 = cls.cat1 = SemanticField(path="01n", heading="term")
        cat1.save()

        cat2 = cls.cat2 = SemanticField(path="02n", heading="aaaa", catid="1")
        cat2.save()

        cat3 = cls.cat3 = SemanticField(path="01.01n", heading="bwip",
                                        parent=cat1)
        cat3.save()

        request_factory = RequestFactory()
        request = request_factory.get("/foo")
        cls.context = {"request": request}

    def test_not_logged_in_no_csrf_token(self):
        """
        A user who is not logged in and has no csrf token should fail to get.
        """
        response = self.app.get(self.url, headers={
            "Accept": "application/json",
        }, expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def test_logged_in_no_csrf_token(self):
        """
        A user who is logged in but has no csrf token should fail to get.
        """
        response = self.app.get(self.url, headers={
            "Accept": "application/json",
        }, user=self.noperm, expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def test_not_logged_in_with_csrf_token(self):
        """
        A user who is not logged in but has a csrf token should get without
        problem.
        """
        # We simulate what happens if a CSRF token has been set by
        # Django in a previous request. We set the value to "foo" and
        # set the header value to "foo" too, which is a match.
        self.app.set_cookie(settings.CSRF_COOKIE_NAME, FAKE_CSRF)
        self.app.get(self.url,
                     params={"paths": "01n"},
                     headers={
                         "Accept": "application/json",
                         "X-CSRFToken": FAKE_CSRF
                     })

    def test_logged_in_with_csrf_token(self):
        """
        A user who is logged in and has a csrf token should get without
        problem.
        """
        # We simulate what happens if a CSRF token has been set by
        # Django in a previous request. We set the value to "foo" and
        # set the header value to "foo" too, which is a match.

        # We have to get the front page first, so that the user is
        # logged before we play with the CSRF token.
        self.app.get("/", user=self.noperm)
        csrf = self.app.cookies[settings.CSRF_COOKIE_NAME]
        self.app.get(self.url,
                     params={"paths": "01n"},
                     headers={
                         "Accept": "application/json",
                         "X-CSRFToken": csrf,
                     }, user=self.noperm)

    def test_bad_accept(self):
        """
        Accept with an incorrect value yields an error.
        """
        self.app.set_cookie(settings.CSRF_COOKIE_NAME, FAKE_CSRF)
        response = self.app.get(self.url, headers={
            "Accept": "text/html",
            "X-CSRFToken": FAKE_CSRF
        }, expect_errors=True)
        self.assertEqual(response.status_code, 406)

    def test_no_paths(self):
        """
        A query without a ``paths`` parameter yields an error.
        """
        self.app.set_cookie(settings.CSRF_COOKIE_NAME, FAKE_CSRF)
        response = self.app.get(self.url, headers={
            "Accept": "application/json",
            "X-CSRFToken": FAKE_CSRF
        }, expect_errors=True)
        self.assertEqual(response.status_code, 400)

    def test_paths(self):
        """
        A query with proper paths yields results.
        """
        self.app.set_cookie(settings.CSRF_COOKIE_NAME, FAKE_CSRF)
        response = self.app.get(self.url,
                                params={"paths": "01.01n;02n;99n"},
                                headers={
                                    "Accept": "application/json",
                                    "X-CSRFToken": FAKE_CSRF,
                                })

        serializer = SemanticFieldSerializer(
            [self.cat2, self.cat3],
            context=self.context,
            unpublished=False,
            many=True)
        transformed = json.loads(json.dumps(serializer.data))
        self.assertCountEqual(response.json, transformed)

    def test_expanded_scope(self):
        """
        A query requesting changerecords gets them.
        """
        self.app.set_cookie(settings.CSRF_COOKIE_NAME, FAKE_CSRF)

        with mock.patch("semantic_fields.serializers.ChangeRecord"
                        ".objects.with_semantic_field") as mocked:
            mocked.return_value = MinimalQuery([
                FakeChangeRecord(lemma="foo", url="/lexicography/foo",
                                 datetime="2000-01-01", published=True)
            ])
            response = self.app.get(self.url,
                                    params={"paths": "01.01n;02n;99n",
                                            "fields": "changerecords"},
                                    headers={
                                        "Accept": "application/json",
                                        "X-CSRFToken": FAKE_CSRF,
                                    })

            serializer = SemanticFieldSerializer(
                [self.cat2, self.cat3],
                fields=["changerecords"],
                context=self.context,
                unpublished=False,
                many=True)
            transformed = json.loads(json.dumps(serializer.data))
            self.assertCountEqual(response.json, transformed)

    def test_complex_paths(self):
        """
        A query with complex paths yields the expected results.
        """
        self.app.set_cookie(settings.CSRF_COOKIE_NAME, FAKE_CSRF)

        response = self.app.get(self.url,
                                params={"paths": "01.01n@02n;01n@02n;02n"},
                                headers={
                                    "Accept": "application/json",
                                    "X-CSRFToken": FAKE_CSRF,
                                })

        url = "http://testserver" + self.url

        self.assertCountEqual(response.json,
                              [{
                                  "url": url + "?paths=01.01n@02n",
                                  "path": "01.01n@02n",
                                  "heading": "bwip @ aaaa",
                                  "heading_for_display": "bwip @ aaaa",
                                  "is_subcat": False,
                                  "verbose_pos": "Noun",
                              }, {
                                  "url": url + "?paths=01n@02n",
                                  "path": "01n@02n",
                                  "heading": "term @ aaaa",
                                  "heading_for_display": "term @ aaaa",
                                  "is_subcat": False,
                                  "verbose_pos": "Noun",
                              }, {
                                  "url": _make_test_url(self.cat2),
                                  "path": "02n",
                                  "heading": "aaaa",
                                  "heading_for_display": "aaaa",
                                  "is_subcat": False,
                                  "verbose_pos": "Noun",
                              }])

    def test_paging(self):
        """
        A search query paginates.
        """
        self.app.set_cookie(settings.CSRF_COOKIE_NAME, FAKE_CSRF)

        response = self.app.get(self.url,
                                params={
                                    "search": "aaaa",
                                    "aspect": "sf",
                                    "scope": "all",
                                    "root": "all",
                                },
                                headers={
                                    "Accept": "application/json",
                                    "X-CSRFToken": FAKE_CSRF,
                                })

        result = response.json
        self.assertEqual(result["unfiltered_count"], 3)
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["results"]), 1)

    def test_parent_unbound(self):
        """
        A search with unbound ``parent``, returns parent relations.
        """
        self.app.set_cookie(settings.CSRF_COOKIE_NAME, FAKE_CSRF)
        response = self.app.get(self.url,
                                params={
                                    "ids": self.cat3.id,
                                    "fields": "parent",
                                    "depths.parent": "-1",
                                },
                                headers={
                                    "Accept": "application/json",
                                    "X-CSRFToken": FAKE_CSRF,
                                })

        data = SemanticFieldSerializer(self.cat3, context=self.context,
                                       fields=["parent"],
                                       depths={"parent": -1},
                                       unpublished=True).data
        self.assertEqual(response.json[0], data)

class ListParameterTestCases(ParameterChecksMixin, ViewsTestCase):

    @classmethod
    def setUpTestData(cls):
        super(ListParameterTestCases, cls).setUpTestData()
        cls.url = reverse("semantic_fields_semanticfield-list")

    def make_request_and_check(self, params, total, headings):
        params["search"] = params.pop("search[value]")
        self.app.set_cookie(settings.CSRF_COOKIE_NAME, FAKE_CSRF)

        response = self.app.get(self.url,
                                params=params,
                                headers={
                                    "Accept": "application/json",
                                    "X-CSRFToken": FAKE_CSRF,
                                })

        result = response.json
        self.assertEqual(result["unfiltered_count"], total)
        self.assertEqual(result["count"], len(headings))
        self.assertEqual(len(result["results"]), len(headings))
        response_headings = [x["heading"] for x in result["results"]]
        self.assertCountEqual(response_headings, headings)

def init():
    ParameterChecksMixin.make_tests(ListParameterTestCases)

init()
