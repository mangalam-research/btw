# -*- encoding: utf-8 -*-
from cStringIO import StringIO

import lxml.etree

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from cms.test_utils.testcases import CMSTestCase
from cms.models import Placeholder
from cms.api import add_plugin
from sekizai.context import SekizaiContext

from core.cms_plugins import CitePlugin

user_model = get_user_model()

class CiteTestCase(CMSTestCase):

    def make_placeholder(self):
        placeholder = Placeholder.objects.create(slot='test')
        model_instance = add_plugin(
            placeholder,
            CitePlugin,
            'en',
        )
        context = SekizaiContext()
        html = model_instance.render_plugin(context)
        parser = lxml.etree.HTMLParser(encoding="utf8")
        tree = lxml.etree.parse(StringIO(html.encode("utf8")), parser)
        self.chicago_authors = \
            tree.xpath("//span[@id='chicago_authors']")[0].text
        self.mla_authors = \
            tree.xpath("//span[@id='mla_authors']")[0].text

    def assertNames(self, expected):
        self.assertEqual(self.chicago_authors, expected)
        self.assertEqual(self.mla_authors, expected)

    @override_settings(BTW_EDITORS=[{
        "forename": u"Luis",
        "surname": u"Gómez",
        "genName": u""
    }, {
        "forename": u"Ligeia",
        "surname": u"Lugli",
        "genName": u""
    }])
    def test_renders_two_names(self):
        self.make_placeholder()
        self.assertNames(u"Gómez, Luis and Ligeia Lugli")

    @override_settings(BTW_EDITORS=[{
        "forename": u"Ligeia",
        "surname": u"Lugli",
        "genName": u""
    }])
    def test_renders_one_name(self):
        self.make_placeholder()
        self.assertNames(u"Lugli, Ligeia")

    @override_settings(BTW_EDITORS=[{
        "forename": u"Luis",
        "surname": u"Gómez",
        "genName": u""
    }, {
        "forename": u"Ligeia",
        "surname": u"Lugli",
        "genName": u""
    }, {
        "forename": u"Forename 3",
        "surname": u"Surname 3",
        "genName": u"GenName 3"
    }])
    def test_renders_three_names(self):
        self.make_placeholder()
        self.assertNames(
            u"Gómez, Luis, Ligeia Lugli and Forename 3 Surname 3, GenName 3")

    @override_settings(BTW_EDITORS=[{
        "forename": u"Luis",
        "surname": u"Gómez",
        "genName": u""
    }, {
        "forename": u"Ligeia",
        "surname": u"Lugli",
        "genName": u""
    }, {
        "forename": u"Forename 3",
        "surname": u"Surname 3",
        "genName": u"GenName 3"
    }, {
        "forename": u"Forename 4",
        "surname": u"Surname 4",
        "genName": u"GenName 4"
    }])
    def test_renders_four_names(self):
        self.make_placeholder()
        self.assertEqual(
            self.chicago_authors,
            u"Gómez, Luis, Ligeia Lugli, Forename 3 Surname 3, GenName 3 "
            u"and Forename 4 Surname 4, GenName 4")
        self.assertEqual(self.mla_authors, u"Gómez, Luis, et al.")