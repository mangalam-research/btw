#!/usr/bin/env python2

import sys

from behave.__main__ import run_behave
from behave.configuration import Configuration
from behave.runner import Runner, Context, the_step_registry

class BTWRunner(Runner):

    def __init__(self, *args, **kwargs):
        super(BTWRunner, self).__init__(*args, **kwargs)

    def run_model(self, *args, **kwargs):
        # Expose the step registry as a field on the context.
        self.context.step_registry = the_step_registry
        return super(BTWRunner, self).run_model(*args, **kwargs)


def main(args=None):
    """Main function to run behave (as program).

    :param args:    Command-line args (or string) to use.
    :return: 0, if successful. Non-zero, in case of errors/failures.
    """
    config = Configuration(args)
    return run_behave(config, BTWRunner)

if __name__ == "__main__":
    # -- EXAMPLE: main("--version")
    sys.exit(main())
