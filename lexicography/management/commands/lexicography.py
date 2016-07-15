import argparse
import json

from django.core.management.base import BaseCommand, CommandError, \
    CommandParser

from ...article import prepare_article_data
from lib import util

class SubCommand(object):
    name = None

    def __call__(self, command, options):
        raise NotImplementedError()

    def add_to_parser(self, subparsers):
        sp = subparsers.add_parser(
            self.name,
            description=self.__doc__,
            help=self.__doc__,
            formatter_class=argparse.RawTextHelpFormatter)
        sp.set_defaults(subcommand=self)
        return sp

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

    def __call__(self, command, options):
        from django.utils import translation
        translation.activate('en-us')

        with open(options["src"], 'r') as src:
            prepared = prepare_article_data(src.read().decode("utf-8"), True)
            with open(options["dst"], 'w') as dst:
                data = util.run_xsltproc(
                    "utils/xsl/strip.xsl", prepared["xml"])
                dst.write(data.encode("utf-8"))
            with open(options["bibl"], 'w') as bibl:
                bibl.write(json.dumps(prepared["bibl_data"]).encode("utf-8"))


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
        top = self

        class SubParser(CommandParser):

            def __init__(self, **kwargs):
                super(SubParser, self).__init__(top, **kwargs)

        subparsers = parser.add_subparsers(title="subcommands",
                                           parser_class=SubParser)

        for cmd in self.subcommands:
            cmd_instance = cmd()
            cmd_instance.add_to_parser(subparsers)

    def handle(self, *args, **options):
        options['subcommand'](self, options)
