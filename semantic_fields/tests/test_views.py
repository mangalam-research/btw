import urllib
import itertools

from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django_webtest import WebTest
from django.utils import translation
from django.template.loader import render_to_string

from cms.test_utils.testcases import BaseCMSTestCase

from ..models import SemanticField, SearchWord, Lexeme

user_model = get_user_model()

@override_settings(ROOT_URLCONF='semantic_fields.tests.urls')
class ViewsTestCase(BaseCMSTestCase, WebTest):

    def setUp(self):
        super(ViewsTestCase, self).setUp()
        translation.activate('en-us')
        self.noperm = user_model.objects.create(username="foo", password="foo")
        self.perm = user_model.objects.create(username="bar", password="bar")
        self.perm.user_permissions.add(Permission.objects.get(
            content_type=ContentType.objects.get_for_model(SemanticField),
            codename="add_semanticfield"))
        self.perm.save()

        # Not a test proper... but make sure that what we expect is
        # the case.
        assert self.perm.can_add_semantic_fields

class MainTestCase(ViewsTestCase):

    def setUp(self):
        super(MainTestCase, self).setUp()
        self.url = reverse("semantic_fields_main")
        self.login_url = reverse('login')

    def test_not_logged_in(self):
        """
        Test that the response is a redirection to the login page when the
        user is not logged in.
        """
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, self.login_url + "?" +
                             urllib.urlencode({"next": self.url}))

    def test_logged_in(self):
        """
        Test that the response shows a page
        """
        self.app.get(self.url, user=self.noperm)

class SearchTableTestCase(ViewsTestCase):

    def setUp(self):
        super(SearchTableTestCase, self).setUp()
        self.url = reverse("semantic_fields_table")
        self.complete_params = {
            "search[value]": "foo",
            "aspect": "sf",
            "scope": "all"
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
        response = self.app.get(self.url, params=params, user=self.noperm)
        self.assertEqual(
            response.json["error"],
            "\nAn error occured while processing an AJAX request.")

    def bad_value(self, param):
        """
        Test that an error is raised if the parameter has an incorrect
        value.
        """
        params = dict(self.complete_params)
        params[param] = "INCORRECT!!!"
        response = self.app.get(self.url, params=params, user=self.noperm)
        self.assertEqual(
            response.json["error"],
            "\nAn error occured while processing an AJAX request.")

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

        self.assertItemsEqual([row[1] for row in json["data"]], headings)

    def scope_check(self, scope, headings):
        """
        Test that setting the scope produces correct results.
        """
        hte = SemanticField(path="01n", heading="hte", catid="1")
        hte.save()

        nonhte = SemanticField(path="02n", heading="nonhte")
        nonhte.save()

        response = self.app.get(self.url,
                                params={
                                    "search[value]": "h",
                                    "scope": scope,
                                    "aspect": "sf",
                                },
                                user=self.noperm)

        self.assertDataTablesResponse(response, total=2, names=headings)

    def aspect_check(self, aspect, headings):
        """
        Test that setting the aspect produces correct results.
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

        response = self.app.get(self.url,
                                params={
                                    "search[value]": "term",
                                    "scope": "all",
                                    "aspect": aspect,
                                },
                                user=self.noperm)

        self.assertDataTablesResponse(response, total=2, names=headings)

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

    for param in ("aspect", "scope"):
        makefunc(c, c.missing_parameter, "test_missing_" + param,
                 param, param)

        makefunc(c, c.bad_value, "test_bad_" + param, param, param)

    for (scope_setting, headings) in (("all", ["hte", "nonhte"]),
                                      ("hte", ["hte"]),
                                      ("btw", ["nonhte"])):
        makefunc(c, c.scope_check, "test_scope_" + scope_setting,
                 scope_setting, scope_setting, headings)

    for (aspect_setting, headings) in (("sf", ["term"]),
                                       ("lexemes", ["aaaa"])):
        makefunc(c, c.aspect_check, "test_aspect_" + aspect_setting,
                 aspect_setting, aspect_setting, headings)

init()

class DetailsTestCaseHTML(ViewsTestCase):

    def setUp(self):
        super(DetailsTestCaseHTML, self).setUp()
        self.hte = hte = SemanticField(path="01n", heading="hte", catid="1")
        hte.save()

    def test_not_logged_in(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        response = self.app.get(self.hte.detail_url, expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def query(self, url, user):
        return self.app.get(url,
                            headers={"Accept": "text/html"},
                            user=user)

    def test_creation_possible(self):
        """
        Test that when a user with adequate permissions sees the page, the
        user can create new semantic fields.
        """
        response = self.query(self.hte.detail_url, self.perm)
        self.assertEqual(len(response.lxml.cssselect(".create-child")), 1,
                         "the button for creating children should exist")

    def test_creation_not_possible(self):
        """
        Test that when a user without adequate permissions sees the page, the
        user cannot create new semantic fields.
        """
        response = self.query(self.hte.detail_url, self.noperm)
        self.assertEqual(len(response.lxml.cssselect(".create-child")), 0,
                         "the button for creating children should not exist")

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
        self.assertItemsEqual(
            lexemes,
            ["foo q", "bar q"],
            "there should be two lexemes with the right values")

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

    def setUp(self):
        super(DetailsTestCaseJSON, self).setUp()
        self.hte = hte = SemanticField(path="01n", heading="hte", catid="1")
        hte.save()

    def test_not_logged_in(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        response = self.app.get(self.hte.detail_url, expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def test_logged_in(self):
        """
        Test that a logged in user gets a response.
        """
        response = self.app.get(self.hte.detail_url, user=self.perm)
        self.assertEqual(response.json,
                         {
                             "path": "01n",
                             "heading": "hte",
                             "parent": None
                         },
                         "the returned value should be correct")


class AddChildFormTestCase(ViewsTestCase):

    def setUp(self):
        super(AddChildFormTestCase, self).setUp()
        self.hte = hte = SemanticField(path="01n", heading="hte", catid="1")
        hte.save()

    def test_not_logged_in(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        response = self.app.get(
            self.hte.add_child_form_url, expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def test_no_permissions(self):
        """
        Test that a user without permission to add semantic fields cannot
        get the form.
        """
        response = self.app.get(self.hte.add_child_form_url, user=self.noperm,
                                expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def test_bad_accept(self):
        """
        Test that a user who specifies the wrong content type gets an error.
        """
        response = self.app.get(self.hte.add_child_form_url, user=self.perm,
                                headers={
                                    "Accept": "application/json",
                                },
                                expect_errors=True)
        self.assertEqual(response.status_code, 406)

    def test_response(self):
        """
        Test that a user who specifies no content type gets HTML.
        """
        response = self.app.get(self.hte.add_child_form_url, user=self.perm)
        self.assertEqual(response.content_type, "text/html")

class CreateTestCase(ViewsTestCase):

    def setUp(self):
        super(CreateTestCase, self).setUp()
        self.hte = hte = SemanticField(path="01n", heading="hte", catid="1")
        hte.save()
        self.url = reverse('semantic_fields_semanticfield-list')

    def test_not_logged_in(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        response = self.app.get(self.url, expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def test_no_permissions(self):
        """
        Test that a user without permission to add semantic fields cannot
        create.
        """
        response = self.app.post(
            self.url, user=self.noperm, expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def test_bad_accept(self):
        """
        Test that a user who specifies the wrong content type gets an error.
        """
        response = self.app.get(self.hte.add_child_form_url, user=self.perm)
        self.assertEqual(response.status_code, 200)
        form = response.form
        form["heading"] = "foo"
        form["pos"] = "n"

        response = self.app.post(self.url, user=self.perm,
                                 headers={
                                     "Accept": "text/xml",
                                 },
                                 params=form.submit_fields(),
                                 expect_errors=True)
        self.assertEqual(response.status_code, 406)

    def creation_successful(self, accept):
        """
        Test that a user can create a new semantic field.
        """
        self.assertEqual(self.hte.children.count(), 0)
        response = self.app.get(self.hte.add_child_form_url, user=self.perm)
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
        self.assertEqual(response.body, "")

        # Reacquire, and check the values of the child.
        hte = SemanticField.objects.get(id=self.hte.id)
        self.assertEqual(hte.children.count(), 1)
        child = hte.children.first()
        self.assertEqual(child.parent, hte)
        self.assertEqual(child.path, hte.path + "/1n")
        self.assertEqual(child.heading, "foo")
        self.assertIsNone(child.catid)
        self.assertEqual(child.children.count(), 0)

    def heading_required(self, accept):
        """
        Test that creating a new field without a heading yields an error.
        """
        self.assertEqual(self.hte.children.count(), 0)
        response = self.app.get(self.hte.add_child_form_url, user=self.perm)
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
            el = response.lxml.cssselect("#error_id_heading_1")[0]
            self.assertEqual(el.text, error)
        elif expected_content_type == "application/json":
            self.assertEqual(response.json, {u"heading": [error]})
        else:
            raise ValueError("unexpected expected_content_type value: " +
                             expected_content_type)

        # Check again that there are no children. We reacquire the
        # object to make sure caching is not interfering.
        self.assertEqual(
            SemanticField.objects.get(id=self.hte.id).children.count(),
            0)

    def incorrect_pos(self, accept):
        """
        Test that creating a new field with an incorrect pos yields an
        error.
        """
        self.assertEqual(self.hte.children.count(), 0)
        response = self.app.get(self.hte.add_child_form_url, user=self.perm)
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
            u"Select a valid choice. xxxxxx is not one of the " \
            u"available choices."
        if expected_content_type == "text/html":
            el = response.lxml.cssselect("#error_id_pos_1")[0]
            self.assertEqual(el.text, error)
        elif expected_content_type == "application/json":
            self.assertEqual(response.json, {u"pos": [error]})
        else:
            raise ValueError("unexpected expected_content_type value: " +
                             expected_content_type)

        # Check again that there are no children. We reacquire the
        # object to make sure caching is not interfering.
        self.assertEqual(
            SemanticField.objects.get(id=self.hte.id).children.count(),
            0)

    def incorrect_parent(self, accept):
        """
        Test that creating a new field with an incorrect parent yields an
        error.
        """
        self.assertEqual(self.hte.children.count(), 0)
        response = self.app.get(self.hte.add_child_form_url, user=self.perm)
        self.assertEqual(response.status_code, 200)
        form = response.form
        form["heading"] = "foo"
        form["pos"] = ""
        form["parent"].force_value("-1")

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
            u"Select a valid choice. That choice is not one of the " \
            u"available choices."
        if expected_content_type == "text/html":
            # This field is hidden. A hidden field does not show
            # errors.
            pass
        elif expected_content_type == "application/json":
            self.assertEqual(response.json, {u"parent": [error]})
        else:
            raise ValueError("unexpected expected_content_type value: " +
                             expected_content_type)

        # Check again that there are no children. We reacquire the
        # object to make sure caching is not interfering.
        self.assertEqual(
            SemanticField.objects.get(id=self.hte.id).children.count(),
            0)

    def missing_parent(self, accept):
        """
        Test that creating a new field with a missing parent yields an
        error.
        """
        self.assertEqual(self.hte.children.count(), 0)
        response = self.app.get(self.hte.add_child_form_url, user=self.perm)
        self.assertEqual(response.status_code, 200)
        form = response.form
        form["heading"] = "foo"
        form["pos"] = ""
        form["parent"].force_value("")

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
        error = u"This field is required."
        if expected_content_type == "text/html":
            # This field is hidden. A hidden field does not show
            # errors.
            pass
        elif expected_content_type == "application/json":
            self.assertEqual(response.json, {u"parent": [error]})
        else:
            raise ValueError("unexpected expected_content_type value: " +
                             expected_content_type)

        # Check again that there are no children. We reacquire the
        # object to make sure caching is not interfering.
        self.assertEqual(
            SemanticField.objects.get(id=self.hte.id).children.count(),
            0)

def init():
    for (accept, test) in itertools.product(
            ("application/json", "application/x-form"),
            ("creation_successful", "heading_required", "incorrect_pos",
             "incorrect_parent", "missing_parent")):
        makefunc(CreateTestCase, getattr(CreateTestCase, test),
                 "test_{0}_{1}".format(test, accept), accept, accept)

init()
