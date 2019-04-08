

import json
import difflib
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.utils import translation
from django.test.client import RequestFactory
from django.urls import resolve
from django.utils.six.moves import input

from semantic_fields.views import SemanticFieldViewSet

from lib.command import SubCommand, SubParser
def serialize_from_query(url):
    parsed = urlparse(url)

    # Work around CSRF protection
    request_factory = RequestFactory(SERVER_NAME="localhost",
                                     HTTP_HOST="localhost")
    request_factory.cookies[settings.CSRF_COOKIE_NAME] = "foo"
    request = request_factory.get(parsed.path,
                                  HTTP_X_CSRFTOKEN="foo",
                                  QUERY_STRING=parsed.query)

    translation.activate("en-us")
    request.LANGUAGE_CODE = "en-us"
    resolved = resolve(parsed.path)

    response = resolved.func(request, *resolved.args, **resolved.kwargs)
    return response


class SerializeField(SubCommand):
    """
    Serialize a semantic field to JSON.
    """

    name = "serialize_field"

    def add_to_parser(self, subparsers):
        sp = super(SerializeField, self).add_to_parser(subparsers)
        sp.add_argument(
            "url",
            help="The url that would be used in a REST query. "
            "MUST BE URL-ENCODED ALREADY!")
        return sp

    def __call__(self, command, options):
        url = options["url"]

        response = serialize_from_query(url)
        if isinstance(response, HttpResponseBadRequest):
            print(response)
        else:
            print(json.dumps(response.data))


class UpdateFixture(SubCommand):
    """
    Update a fixture containing serialized fields.
    """

    name = "update_fixture"

    def add_to_parser(self, subparsers):
        sp = super(UpdateFixture, self).add_to_parser(subparsers)
        sp.add_argument(
            "path",
            help="A path to the JSON fixture to update.")
        return sp

    def __call__(self, command, options):

        original = None
        with open(options["path"]) as data:
            original = data.read()
            fixture = json.loads(original)

        updated = {}
        for key in fixture.keys():
            response = serialize_from_query(key)
            if isinstance(response, HttpResponseBadRequest):
                print(response)
                break
            else:
                updated[key] = response.data

        new_data = json.dumps(updated, indent=2)
        if new_data == original:
            command.stdout.write("No change!")
            return

        print("".join(difflib.unified_diff(original.splitlines(True),
                                           new_data.splitlines(True))))

        msg = ("\nThere are differences between the old an new data. "
               "Update? (yes/no): ")
        confirm = eval(input(msg))
        while True:
            if confirm not in ('yes', 'no'):
                confirm = eval(input('Please enter either "yes" or "no": '))
                continue
            if confirm == 'yes':
                with open(options["path"], 'w') as data:
                    data.write(new_data)
            break


class Command(BaseCommand):
    help = """\
Management commands for the semantic_fields app.
"""
    requires_system_checks = False

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.subcommands = []

        for cmd in [SerializeField, UpdateFixture]:
            self.register_subcommand(cmd)

    def register_subcommand(self, cmd):
        self.subcommands.append(cmd)

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(title="subcommands",
                                           dest="subcommand"
                                           parser_class=SubParser(self),
                                           required=True)

        for cmd in self.subcommands:
            cmd_instance = cmd()
            cmd_instance.add_to_parser(subparsers)

    def handle(self, *args, **options):
        options['subcommand'](self, options)
