import unittest
import subprocess
import re

prompt_re = re.compile(ur"^> ")
continuation_re = re.compile(ur"^\.\.\. ")

class Node(object):

    def __init__(self):
        self.node = subprocess.Popen(["node", "--interactive"],
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
        self.last_command_nl = None

    def send(self, command):
        command = command.strip()
        self.last_command_nl = command.count("\n")
        command += "\n"
        self.node.stdin.write(command)

    def receive(self):
        result = self.node.stdout.readline().strip()
        result = prompt_re.sub("", result)
        for _ in xrange(0, self.last_command_nl):
            result = continuation_re.sub("", result)
        return result


class TestJavaScript(unittest.TestCase):

    node = None

    @classmethod
    def setUpClass(cls):
        node = Node()

        node.send("""
        define = function (cb) {
            var exports = {};
            cb(null, exports, null);
            global.btw_semantic_fields = exports;
        }
        """)
        assert node.receive().endswith("[Function]")

        node.send(
            "require('./build/static-build/lib/btw/"
            "btw_semantic_fields.js');\n")
        assert node.receive() == "{}"

        cls.node = node

    def check(self, argument, out, depth=None):
        node = self.node

        node.send("""\
        JSON.stringify(btw_semantic_fields.combineSemanticFields([
          {0}
        ], {1}))
        """.format(argument, 'undefined' if depth is None else str(depth)))
        result = node.receive()
        self.assertEqual(result, "'[" + out + "]'")

    def test_empty_array(self):
        """
        Tests that an empty array as input returns an empty array as
        output.
        """
        self.check('', "")

    def test_removal_of_duplicates_no_depth(self):
        """
        Tests that duplicates are removed and the result is sorted in
        order.
        """
        self.check('''\
        "01.01.01.02",
        "01.01.01.01",
        "01.01.01.01",
        "01.01.01.02"''',
                   '"01.01.01.01","01.01.01.02"')

    def test_sorting(self):
        """
        Tests that the result is sorted in order.
        """
        self.check('''\
        "01.01.01.02vt",
        "01.01.01.02",
        "01.01.01",
        "01.01.01.02.02",
        "01.01.01.02aj"''',
                   '"01.01.01","01.01.01.02","01.01.01.02aj",'
                   '"01.01.01.02vt","01.01.01.02.02"')

    def test_sorting_depth(self):
        """
        Tests that the result is sorted in order, when we limit the depth.
        """
        self.check('''\
        "01.01.01.02vt",
        "01.01.01.02",
        "01.01.01",
        "01.01n",
        "01.01.01.02.02",
        "01.01.01.02aj"''',
                   '"01.01","01.01.01","01.01.01.02"', depth=4)
