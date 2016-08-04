import argparse
from django.core.management.base import CommandParser

class SubCommand(object):
    """
    A class for adding subcommands to Django commands.
    """

    name = None
    "The name of the command."

    def __call__(self, command, options):
        raise NotImplementedError()

    def add_to_parser(self, subparsers):
        """
        Add the command to the parser. The default creates a subparser
        that adds a command that has:

        * For name ``self.name``.

        * For description ``self.__doc__``.

        * For help ``self.__doc__``

        Derived classes could call this implementation and add to the
        subparser returned.

        :param subparsers: The ``CommandParser`` object on which to add
                           the subparser.
        :returns: The subparser created.
        """
        sp = subparsers.add_parser(
            self.name,
            description=self.__doc__,
            help=self.__doc__,
            formatter_class=argparse.RawTextHelpFormatter)
        sp.set_defaults(subcommand=self)
        return sp

def SubParser(top):  # pylint: disable=invalid-name
    """
    Create a class that is suitable to be used as a subcommand parser
    (subparser) for Django commands.

    The ``CommandParser`` that Django uses requires a reference to the
    object at the top level of the hierarchy of parsers, but by
    default the argparse code does not provide this. The clases
    created here rectify the issue.

    :param top: The top command parser.
    """
    class _SubParser(CommandParser):

        def __init__(self, **kwargs):
            super(_SubParser, self).__init__(top, **kwargs)

    return _SubParser
