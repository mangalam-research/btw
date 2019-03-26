# -*- encoding: utf-8 -*-
from io import StringIO

import lxml.etree

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from django.test.client import RequestFactory
from cms.test_utils.testcases import CMSTestCase
from cms.models import Placeholder
from cms.api import add_plugin
from cms.plugin_rendering import ContentRenderer
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
        renderer = ContentRenderer(request=RequestFactory())
        html = renderer.render_plugin(model_instance, {})
        parser = lxml.etree.HTMLParser(encoding="utf8")
        tree = lxml.etree.parse(StringIO(html), parser)
        self.chicago_authors = \
            tree.xpath("//span[@id='chicago_authors']")[0].text
        self.mla_authors = \
            tree.xpath("//span[@id='mla_authors']")[0].text

    def assertNames(self, expected):
        self.assertEqual(self.chicago_authors, expected)
        self.assertEqual(self.mla_authors, expected)

    @override_settings(BTW_EDITORS=[{
        "forename": "Luis",
        "surname": "Gómez",
        "genName": ""
    }, {
        "forename": "Ligeia",
        "surname": "Lugli",
        "genName": ""
    }])
    def test_renders_two_names(self):
        self.make_placeholder()
        self.assertNames("Gómez, Luis and Ligeia Lugli")

    @override_settings(BTW_EDITORS=[{
        "forename": "Ligeia",
        "surname": "Lugli",
        "genName": ""
    }])
    def test_renders_one_name(self):
        self.make_placeholder()
        self.assertNames("Lugli, Ligeia")

    @override_settings(BTW_EDITORS=[{
        "forename": "Luis",
        "surname": "Gómez",
        "genName": ""
    }, {
        "forename": "Ligeia",
        "surname": "Lugli",
        "genName": ""
    }, {
        "forename": "Forename 3",
        "surname": "Surname 3",
        "genName": "GenName 3"
    }])
    def test_renders_three_names(self):
        self.make_placeholder()
        self.assertNames(
            "Gómez, Luis, Ligeia Lugli and Forename 3 Surname 3, GenName 3")

    @override_settings(BTW_EDITORS=[{
        "forename": "Luis",
        "surname": "Gómez",
        "genName": ""
    }, {
        "forename": "Ligeia",
        "surname": "Lugli",
        "genName": ""
    }, {
        "forename": "Forename 3",
        "surname": "Surname 3",
        "genName": "GenName 3"
    }, {
        "forename": "Forename 4",
        "surname": "Surname 4",
        "genName": "GenName 4"
    }])
    def test_renders_four_names(self):
        self.make_placeholder()
        self.assertEqual(
            self.chicago_authors,
            "Gómez, Luis, Ligeia Lugli, Forename 3 Surname 3, GenName 3 "
            "and Forename 4 Surname 4, GenName 4")
        self.assertEqual(self.mla_authors, "Gómez, Luis, et al.")
