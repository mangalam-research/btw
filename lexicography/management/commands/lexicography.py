import json

from django.core.management.base import BaseCommand

from ...article import prepare_article_data, get_bibliographical_data
from lib import util, testutil
from lib.command import SubCommand

class PrepareArticle(SubCommand):
    """
    Run the transformations that are done to the XML to prepare an
    article for displaying.
    """

    name = "prepare-article"

    def add_to_parser(self, subparsers):
        sp = super(PrepareArticle, self).add_to_parser(subparsers)
        sp.add_argument("src",
                        help='The source to convert.')
        sp.add_argument("dst",
                        help='Where to save the XML of the article.')
        sp.add_argument("bibl",
                        help='Where to save the bibliographical data.')
        return sp

    def __call__(self, command, options):
        from django.utils import translation
        translation.activate('en-us')

        testutil.unmonkeypatch_databases()

        with open(options["src"], 'r') as src:
            source = src.read()
            prepared, _ = prepare_article_data(source)
            with open(options["dst"], 'w') as dst:
                data = util.run_xsltproc(
                    "utils/xsl/strip.xsl", prepared)
                dst.write(data)
            with open(options["bibl"], 'w') as bibl:
                bibl.write(json.dumps(get_bibliographical_data(source)[1]))


class Command(BaseCommand):
    help = """\
Management commands for the lexicography app.
"""
    requires_system_checks = False

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.subcommands = []

        for cmd in [PrepareArticle]:
            self.register_subcommand(cmd)

    def register_subcommand(self, cmd):
        self.subcommands.append(cmd)

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(title="subcommands",
                                           dest="subcommand",
                                           required=True)

        for cmd in self.subcommands:
            cmd_instance = cmd()
            cmd_instance.add_to_parser(subparsers)

    def handle(self, *args, **options):
        options['subcommand'](self, options)
