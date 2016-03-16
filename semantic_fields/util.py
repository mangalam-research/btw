import copy

from grako.ast import AST
from .field import fieldParser

class _FieldParser(fieldParser):

    def __init__(self):
        super(_FieldParser, self).__init__(whitespace='')

    def parse(self, string, start):
        return super(_FieldParser, self).parse(string, start)

def _to_ast(string):
    return _FieldParser().parse(string, "field")

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
                tuple(_ParsedBranch(branch=branch) for branch in exp.branches)
        else:
            self.branches = None

        self.specification = ParsedExpression(exp.specification) \
            if exp.specification else None

    @staticmethod
    def make(uri, number, pos):
        return ParsedExpression(None).make_child(uri, number, pos)

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

    @property
    def pos(self):
        """
        The pos that govern this expression. This is the last pos that
        appears in the sequence of hte number and branches.
        """
        if self.specification:
            raise ValueError("cannot determine the pos of a "
                             "specified reference")

        if self.branches:
            return self.branches[-1].pos

        return self.hte_pos

    @property
    def last_uri(self):
        """
        The URI of the last branch of this expression.
        """
        return self.branches[-1].uri if self.branches else None

    def related_by_pos(self):
        """
        :returns: The list of expressions which would differ from this
        expression only due to the governing pos being different. Note
        that this function builds a theoretical list. It does not
        verify whether these expression correspond to existing fields
        in the database.
        """
        if self.specification:
            raise ValueError("cannot determine the related expressions of a "
                             "specified reference")

        my_pos = self.pos

        ret = []

        # The set of choices we iterate over is different depending on
        # whether we are on a branch or not. Branches can take a blank
        # pos, HTE fields (no branch) cannot.
        choices = POS_CHOICES_EXPANDED if self.branches else POS_CHOICES

        for (pos, _) in choices:
            if pos == my_pos:
                continue
            related = copy.copy(self)
            if related.branches:
                related.branches = \
                    related.branches[:-1] + (copy.copy(related.branches[-1]), )
                related.branches[-1].pos = pos
            else:
                related.hte_pos = pos
            ret.append(related)

        return ret

    @property
    def last_level_number(self):
        if self.specification:
            raise ValueError("cannot determine the last level of a "
                             "specified reference")

        if self.branches:
            return self.branches[-1].last_level_number

        if self.hte_subcats:
            return int(self.hte_subcats[-1])

        return int(self.hte_levels[-1])

    def make_child(self, uri, number, pos):
        if self.specification:
            raise ValueError("cannot make a child for a specified reference")

        if pos not in POS_TO_VERBOSE:
            raise ValueError("pos is not among valid choices")

        if number <= 0:
            raise ValueError("the number must be greater than 0")

        ret = self.branch_out(uri)

        ret = copy.copy(self) if ret is self else ret
        ret.branches = ret.branches[:-1] + \
            (ret.branches[-1].make_child(number, pos), )
        return ret

    def branch_out(self, uri):
        if self.specification:
            raise ValueError("cannot make a branch for a specified reference")

        if self.branches and self.branches[-1].uri == uri:
            # There's nothing to be done
            return self

        ret = copy.copy(self)
        if not ret.branches:
            ret.branches = (_ParsedBranch(uri=uri), )
            return ret

        ret.branches = ret.branches + (_ParsedBranch(uri=uri), )
        return ret


class _ParsedBranch(object):

    def __init__(self, branch=None, uri=None):
        if branch is not None:
            self.uri = branch.uri or ""
            self.levels = tuple(branch.levels)
            self.pos = branch.pos or ""
        else:
            self.uri = uri
            self.levels = ()
            self.pos = ''

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

    @property
    def last_level_number(self):
        return int(self.levels[-1])

    def make_child(self, number, pos):
        if pos not in POS_TO_VERBOSE:
            raise ValueError("pos is not among valid choices")

        if number <= 0:
            raise ValueError("the number must be greater than 0")

        ret = copy.copy(self)
        ret.pos = pos
        ret.levels = ret.levels + (str(number), )
        return ret

POS_CHOICES = (
    ('aj', 'Adjective'),
    ('av', 'Adverb'),
    ('cj', 'Conjunction'),
    ('in', 'Interjection'),
    ('n', 'Noun'),
    ('p', 'Preposition'),
    ('ph', 'Phrase'),
    ('v', 'Verb'),
    ('vi', 'Intransitive verb'),
    ('vm', 'Impersonal verb'),
    ('vp', 'Passive verb'),
    ('vr', 'Reflexive verb'),
    ('vt', 'Transitive verb')
)

# HTE fields need a pos, but custom fields may have a blank pos.
POS_CHOICES_EXPANDED = POS_CHOICES + (('', 'None'), )

POS_TO_VERBOSE = dict(POS_CHOICES_EXPANDED)

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
