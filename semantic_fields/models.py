from django.db import models, IntegrityError
from django.core.urlresolvers import reverse
from django.utils.html import mark_safe, escape

from .util import parse_local_reference, parse_local_references, \
    POS_TO_VERBOSE, ParsedExpression, POS_VALUES_EXPANDED
from .signals import semantic_field_updated
from lib.util import on_change

def format_duplicate_error(uri, pos, heading):
    pos_description = "with pos '{0}'".format(pos) if pos != '' else \
                      "without pos"

    namespace_description = "the BTW namespace" if uri == '' \
                            else "namespace '{0}'".format(uri)

    heading_description = " and heading '{0}'".format(heading) \
                          if heading else ""

    return ("There is already a semantic field in {0} "
            "{1}{2}.").format(namespace_description,
                              pos_description,
                              heading_description)


def make_field(parent, uri, heading, pos):
    if parent and len(parent.parsed_path) > 1:
        raise ValueError("cannot use make_field on a specified field")

    children = parent.children.all() if parent else \
        SemanticField.objects.roots

    # The siblings use the same URI as the child we want to create
    siblings = [c for c in children if c.parsed_path[0].last_uri == uri]

    dupe = any(c for c in siblings if c.pos == pos and c.heading == heading)
    if dupe:
        raise ValueError(format_duplicate_error(uri, pos, heading))

    max_child = 0 if len(siblings) == 0 else  \
        max(c.parsed_path[0].last_level_number for c in siblings)

    # The looping and exception handling here is to handle a
    # possible race if two users try to create a new field at
    # the same time.
    while True:
        max_child += 1
        desired_path = parent.parsed_path[0].make_child(uri, max_child, pos) \
            if parent else ParsedExpression.make(uri, max_child, pos)
        # We need a string
        desired_path = unicode(desired_path)

        sf = SemanticField(path=desired_path, heading=heading, parent=parent)
        try:
            sf.save()
            return sf
        except IntegrityError as ex:
            # Verify whether the path is already existing.
            try:
                SemanticField.objects.get(path=desired_path)
                # Ok, so the desired path exists. Loop over and retry.
            except SemanticField.DoesNotExist:
                # It is not a path uniqueness problem, reraise.
                raise ex


class SemanticFieldManager(models.Manager):

    def make_field(self, heading, pos):
        # Right now we can only create semantic fields in the BTW
        # namespace, which has the empty string URI.
        return make_field(None, "", heading, pos)

    @property
    def roots(self):
        return self.filter(parent__isnull=True)

class SemanticField(models.Model):
    objects = SemanticFieldManager()
    catid = models.IntegerField(unique=True, null=True)
    _path = models.TextField(unique=True, name="path", db_column="path")
    parent = models.ForeignKey(
        "self", related_name="children", null=True, blank=True)
    heading = models.TextField()

    def _branch_assertions(self):
        ref = self.parsed_path[0]
        # This will have to be modified when we allow user-based
        # custom fields.
        if ref.branches:
            # This is a current limitation of BTW
            assert len(ref.branches) == 1
            branch = ref.branches[-1]

            # This is a current limitation of BTW. BTW branches have
            # an empty URI.
            assert branch.uri == ""

    def make_child(self, heading, pos):
        self._branch_assertions()
        # Right now we can only create semantic fields in the BTW
        # namespace, which has the empty string URI.
        return make_field(self, "", heading, pos)

    def make_related_by_pos(self, heading, pos):
        ref = self.parsed_path[0]

        self._branch_assertions()

        # Right now we can only create semantic fields in the BTW
        # namespace, which has the empty string URI.
        uri = ""

        desired_path = ref.make_related_by_pos(pos)
        sf = SemanticField(path=unicode(desired_path),
                           heading=heading,
                           parent=self.parent)

        # We try preventing duplication by restricting the list of
        # possible pos values that we show in user's forms. However, a
        # race condition is still possible. Alice could bring up the
        # form and go have a coffee. Then Bob brings up the form and
        # creates a related by pos with pos X. Then Alice comes back
        # and tries to do the same. The form will still show X as a
        # possibility for her.
        try:
            sf.save()
            return sf
        except IntegrityError as ex:
            # Verify whether the path is already existing.
            try:
                SemanticField.objects.get(path=unicode(desired_path))
                # Already exists, report!
                raise ValueError(format_duplicate_error(uri, pos, None))
            except SemanticField.DoesNotExist:
                # It is not a path uniqueness problem, reraise.
                raise ex

    @property
    def heading_for_display(self):
        """
        This is the heading value we should be using for displaying the
        field to the user. For fields that are not subcategories,
        that's just the heading. For fields that are subcategories,
        that's the heading plus ``" :: "`` separating it from the
        parent's heading.

        This value is useful when the semantic field is meant to be
        shown to the user in isolation. If the semantic field is going
        to be part of a list displaying it and its ancestors (e.g. the
        breadcrubs), then it is better to use ``heading``
        directly. Otherwise, the parent will appear twice in the list.
        """
        return self.heading if not self.is_subcat else \
            self.parent.heading_for_display + " :: " + self.heading

    @property
    def is_custom(self):
        # catid is None for all custom fields. This is the fastest
        # way to check...
        return self.catid is None

    @property
    def detail_url(self):
        return reverse('semantic_fields_semanticfield-detail',
                       args=(self.pk, ))

    @property
    def add_child_url(self):
        return reverse('semantic_fields_semanticfield-children',
                       args=(self.pk, ))

    @property
    def add_related_by_pos_url(self):
        # Adding a related_by_pos to a non-custom field is illegal.
        return reverse('semantic_fields_semanticfield-related-by-pos',
                       args=(self.pk, )) if self.is_custom else None

    @property
    def edit_url(self):
        # We do not check whether the field is custom. In theory,
        # performing an update that changes nothing to a non-custom
        # field should be okay.
        return reverse('semantic_fields_semanticfield-detail',
                       args=(self.pk, ))

    @property
    def add_child_form_url(self):
        return reverse('semantic_fields_semanticfield-add-child-form',
                       args=(self.pk, ))

    @property
    def add_related_by_pos_form_url(self):
        # Adding a related_by_pos to a non-custom field is illegal.
        return reverse('semantic_fields_semanticfield-add-related-by-pos-form',
                       args=(self.pk, )) if self.is_custom else None

    @property
    def edit_form_url(self):
        # We do not check whether the field is custom. In theory,
        # performing an update that changes nothing to a non-custom
        # field should be okay.
        return reverse('semantic_fields_semanticfield-edit-form',
                       args=(self.pk, ))

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, val):
        self._path = val
        self._parsed_path = None
        self._related_by_pos = None
        self._validate_path()

    def _validate_path(self):
        if len(self.parsed_path) > 1:
            raise ValueError("paths cannot have specifications")

    _parsed_path = None

    @property
    def parsed_path(self):
        pp = self._parsed_path
        if pp is not None:
            return pp

        parsed = parse_local_references(self.path)
        self._parsed_path = parsed
        return parsed

    _related_by_pos = None

    @property
    def related_by_pos(self):
        rp = self._related_by_pos

        if rp is not None:
            return rp

        ref = self.parsed_path[0]
        related = ref.related_by_pos()
        related = \
            SemanticField.objects.filter(
                path__in=(unicode(x) for x in related))
        self._related_by_pos = related
        return related

    @property
    def possible_new_poses(self):
        """
        A set of parts of speech (pos) for which there no relatives of this
        semantic field exist.
        """
        if not self.is_custom:
            return set()

        existing = set(related.pos for related in self.related_by_pos)
        existing.add(self.pos)
        return POS_VALUES_EXPANDED - existing

    @property
    def pos(self):
        return self.parsed_path[0].pos

    @property
    def verbose_pos(self):
        return POS_TO_VERBOSE[self.pos]

    @property
    def heading_and_pos(self):
        return "{0} ({1})".format(self.heading, self.verbose_pos)

    @property
    def heading_for_display_and_pos(self):
        return "{0} ({1})".format(self.heading_for_display, self.verbose_pos)

    @property
    def is_subcat(self):
        return self.parsed_path[0].hte_subcats is not None

    def make_link(self, text=None, css_class=""):
        """
        Makes an HTML serialization of a ``a`` element which links to the
        REST URL for obtaining the details of this instance. The link
        is generated to meet the needs of the BTW project.

        :param text: The text to use for the link. If not specified,
        the heading of this instance is used.
        :param css_class: An additional CSS class to give to the link.
        :returns: The HTML of the link.
        """
        if text is None:
            text = self.heading_for_display

        if css_class != "":
            css_class = " " + css_class

        return mark_safe(
            "<a class='btn btn-default btn-sm sf-link{0}' href='{1}'>{2}</a>"
            .format(css_class, self.detail_url, escape(text)))

    @property
    def link(self):
        """
        An HTML serialization of a ``a`` element which links to the REST
        URL for obtaining the details of this instance. The link is
        generated to meet the needs of the BTW project. The link has
        for text the heading of this instance. The class on the ``a``
        element is ``btn btn-default btn-sm sf-link``.
        """
        return self.make_link()

    def _breadcrumbs(self, linked, first):
        heading = self.heading_and_pos if first else self.heading
        ret = self.make_link(heading) if linked else escape(heading)
        if self.parent:
            ret = self.parent._breadcrumbs(linked, first=False) + \
                escape(" :: " if self.is_subcat else " > ") + ret
        return ret

    @property
    def linked_breadcrumbs(self):
        """
        The linked version of the breadcrumbs of this object. This version
        is identical to the non-linked version but each heading is a
        hyperlink to the details of the object to which the heading
        belongs. The value is escaped HTML.
        """
        return mark_safe('<span class="sf-breadcrumbs">{0}</span>'
                         .format(self._breadcrumbs(True, True)))

    @property
    def breadcrumbs(self):
        """
        The breadcrumbs for this object. The breadcrumbs are formed by
        combining the heading of this object together with the
        breadcrumbs for the parent of this object, if any. If this
        object is a subcategory, then the breadcrumbs of the parent
        are separated from this object's heading with " ::
        ". Otherwise, " > " is the separatator. The value is escaped
        HTML.
        """
        return self._breadcrumbs(False, True)

    @property
    def hte_url(self):
        return None if self.catid is None else \
            "http://historicalthesaurus.arts.gla.ac.uk/category/?id={0}" \
            .format(self.catid)

    def __unicode__(self):
        return self.heading + " " + self.path

def make_specified_sf(fields):
    """
    Create a "fake" semantic field that is the product of a complex
    semantic field expression.
    """
    return SpecifiedSemanticField(
        path="@".join(field.path for field in fields),
        heading=" @ ".join(field.heading_for_display for field in fields))


class SpecifiedSemanticField(SemanticField):
    """
    A "specified" semantic field is a kind of field that has a path
    specification (with "@"). These are not *real* fields but we do
    return such fields in search queries to the REST API, for instance
    so it is useful to have a fake class for them.
    """

    def save(self, *args, **kwargs):
        "We cannot save SpecifiedSemanticField objects to the database."
        raise Exception("cannot save a specified semantic field")

    def _validate_path(self):
        self.parsed_path  # pylint: disable=pointless-statement

    @property
    def is_subcat(self):
        return False

    @property
    def is_custom(self):
        return False

    @property
    def related_by_pos(self):
        return SemanticField.objects.none()

    @property
    def possible_new_poses(self):
        return set()

    def make_child(self, *args, **kwargs):
        raise Exception("cannot make a child of a SpecifiedSemanticField")

    def make_related_by_pos(self, *args, **kwargs):
        raise Exception("cannot make a related field for a "
                        "SpecifiedSemanticField")

    @property
    def detail_url(self):
        # They do not have a real detail url. Querying the list
        # endpoint with "?paths=p:" + path will return constructed
        # records.
        return reverse('semantic_fields_semanticfield-list') + \
            "?paths=" + self.path

    @property
    def add_child_url(self):
        return None

    @property
    def add_related_by_pos_url(self):
        return None

    @property
    def edit_url(self):
        return None

    @property
    def add_child_form_url(self):
        return None

    @property
    def add_related_by_pos_form_url(self):
        return None

    @property
    def edit_form_url(self):
        return None

def emit_change_signal(instance):
    semantic_field_updated.send(instance.__class__, instance=instance)

# The only thing that may change is the heading.
on_change(SemanticField, lambda sf: sf.heading, emit_change_signal)

class Lexeme(models.Model):

    class Meta:
        unique_together = ("semantic_field", "catorder")
        ordering = ["catorder"]

    htid = models.IntegerField(primary_key=True)
    # This field is our real foreign key. We convert the HTE
    # field catid to it.
    semantic_field = models.ForeignKey(SemanticField, related_name="lexemes")
    word = models.CharField(max_length=60)
    fulldate = models.CharField(max_length=90)
    catorder = models.IntegerField()

class SearchWord(models.Model):
    sid = models.IntegerField(primary_key=True)
    htid = models.ForeignKey(Lexeme)
    searchword = models.CharField(max_length=60, db_index=True)
    type = models.CharField(max_length=3)
