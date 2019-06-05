import argparse
import sys

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

required = {"required": True} if sys.version_info >= (3, 7, 0) else {}
