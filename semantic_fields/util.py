import copy

from grako.ast import AST
from .field import fieldParser

class _FieldParser(fieldParser):

    def __init__(self):
        super(_FieldParser, self).__init__(whitespace='')

    def parse(self, string, start):
        return super(_FieldParser, self).parse(string, start)

__parser = _FieldParser()

def _to_ast(string):
    return __parser.parse(string, "field")

def _make_from_hte(**kwargs):
    """
    Makes a :class:`ParsedExpression` from an HTE semantic field path.

    Note that it is quite possible to make instances that contain
    garbage. This method is meant to be used in testing only.
    """
    ret = ParsedExpression(None)
    ret.hte_levels = [
        kwargs[x] for x in ("t1", "t2", "t3", "t4", "t5", "t6", "t7")
        if kwargs.get(x, None)]
    subcat = kwargs.get("subcat", None)
    ret.hte_subcats = subcat and subcat.split(".")
    ret.hte_pos = kwargs["pos"]
    return ret

class ParsedExpression():

    """
    Instances represent a parsed semantic field
    expression. The expressions can be semantic fields with any
    number of branches and any number of specifications.

    Instances should be treated as immutable by all code. (Some
    code internal to the class may mutate fields before letting a
    new instance "escape".)

    :param exp: The expression that this object should represent.
    :type exp: A string or a :class:`AST`.
    :raises: :class:`grako.exceptions.FailedParse` if ``exp`` was a
             string that could not be parsed.
    """

    def __init__(self, exp):
        if exp is None:
            self.hte_levels = None
            self.hte_subcats = None
            self.hte_pos = None
            self.branches = None
            self.specification = None
            return

        if not isinstance(exp, AST):
            exp = _to_ast(exp)

        if exp.hte:
            self.hte_levels = tuple(exp.hte.levels)
            self.hte_subcats = \
                tuple(exp.hte.subcats) if exp.hte.subcats else None
            self.hte_pos = exp.hte.pos
        else:
            self.hte_levels = None
            self.hte_subcats = None
            self.hte_pos = None

        if exp.branches:
            self.branches = \
                tuple(_ParsedBranch(branch) for branch in exp.branches)
        else:
            self.branches = None

        self.specification = ParsedExpression(exp.specification) \
            if exp.specification else None

    def __hash__(self):
        return unicode(self)

    def __eq__(self, other):
        return unicode(self) == unicode(other)

    def __unicode__(self):
        ret = u""
        if self.hte_levels:
            ret += ".".join(self.hte_levels)
            if self.hte_subcats:
                ret += "|" + ".".join(self.hte_subcats)
            ret += self.hte_pos

        if self.branches:
            for branch in self.branches:
                ret += unicode(branch)

        if self.specification:
            ret += "@" + unicode(self.specification)

        return ret

    def __str__(self):
        return unicode(self).encode("utf-8")

    def parent(self):
        """
        Return the :class:`ParsedExpression` which is the parent path
        of this one. This is a purely syntactical operation: the path
        returned may not exist in the database.

        :returns: The parent path.
        :rtype: :class:`ParsedExpression` or ``None`` if there is no
                parent.
        :raises: :class:`ValueError` if the instance has a
                 specification, because the specification makes the
                 notion of "parent" ambiguous.
        """
        if self.specification:
            raise ValueError("cannot determine the parent of a "
                             "specified reference")
        if self.branches:
            ret = copy.copy(self)
            parent = ret.branches[-1].parent()
            if parent is not None:
                ret.branches = ret.branches[:-1] + (parent, )
                return ret

            ret.branches = ret.branches[:-1] \
                if len(ret.branches) > 1 else None

            return ret

        if self.hte_subcats:
            ret = copy.copy(self)
            ret.hte_subcats = ret.hte_subcats[:-1] \
                if len(ret.hte_subcats) > 1 else None

            return ret

        if len(self.hte_levels) <= 1:
            return None

        ret = copy.copy(self)
        ret.hte_levels = ret.hte_levels[:-1]
        return ret

    def specification_to_list(self):
        """
        Converts an expression that has specifications to a list of
        unspecified expressions. An expression like ``A`` would be
        converted to ``[A]``, an epression like ``A@B@C`` woulc be
        converted to ``[A, B, C]``.

        :returns: The list of expressions.
        :rtype: :class:`list` of :class:`ParsedExpression`.
        """
        spec = self.specification
        if spec is None:
            return [self]

        self_copy = copy.copy(self)
        self_copy.specification = None
        return [self_copy] + spec.specification_to_array()

class _ParsedBranch(object):

    def __init__(self, branch):
        self.uri = branch.uri
        self.levels = tuple(branch.levels)
        self.pos = branch.pos

    def __unicode__(self):
        ret = u"/"
        if self.uri:
            ret += "{" + self.uri + "}"
        ret += ".".join(self.levels)
        if self.pos:
            ret += self.pos
        return ret

    def __str__(self):
        return unicode(self).encode("utf-8")

    def parent(self):
        """
        Return the :class:`_ParsedBranch` which is the parent path
        of this one.

        :returns: The parent path.
        :rtype: :class:`_ParsedBranch` or ``None`` if there is no
                parent.
        """
        if len(self.levels) <= 1:
            return None

        ret = copy.copy(self)
        ret.levels = ret.levels[:-1]
        return ret


def _branch_checks(ast):
    if ast.branches and len(ast.branches) > 1:
        raise ValueError("BTW currently supports only one branch")

    if ast.branches:
        for branch in ast.branches:
            if len(branch.levels) > 2:
                raise ValueError("BTW does not allow branches with "
                                 "more than two levels")
            if branch.uri:
                raise ValueError("BTW does not allow branches with URIs")


def parse_local_reference(ref):
    """
    This function parses a semantic field reference. This function is
    doing only minimal validation. It is not meant to be used as a
    general purpose validating function for semantic field codes. You
    should not rely on it to check whether a code is valid. It is
    legitimate for this function to return garbage if passed garbage.

    Whereas :class:`ParsedExpression` implements the general grammar,
    this function accepts only a reference without a specification
    ("@...."). Moreover, it imposes the current limitations of BTW on
    it and will fail with a `:class:ValueError` if these limitations
    are violated.

    This function does not verify that a reference refers to an
    *existing* semantic field.

    :param ref: The semantic field reference.
    :returns: A the parsed reference.
    :rtype: :class:`ParsedExpression`
    """
    ref = ref.strip()
    ast = _to_ast(ref)
    if ast.specification is not None:
        raise ValueError("references cannot have specifications")

    _branch_checks(ast)
    return ParsedExpression(ast)

def parse_local_references(ref):
    """
    This function parses a semantic field reference, which may be
    specified. This function is doing only minimal validation. It is
    not meant to be used as a general purpose validating function for
    semantic field codes. You should not rely on it to check whether a
    code is valid. It is legitimate for this function to return
    garbage if passed garbage.

    Whereas :class:`ParsedExpression` implements the general grammar,
    this function imposes the current limitations of BTW on it and
    will fail with a `:class:ValueError` if these limitations are
    violated.

    This function does not verify that a reference refers to an
    *existing* semantic field.

    :param ref: The semantic field reference.
    :returns: A the parsed reference.
    :rtype: :class:`list` of :class:`ParsedExpression`
    """
    ref = ref.strip()
    ast = _to_ast(ref)

    _branch_checks(ast)
    return ParsedExpression(ast).specification_to_list()
