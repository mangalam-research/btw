from django.db import models, IntegrityError
from django.core.urlresolvers import reverse
from django.utils.html import mark_safe, escape

from .util import parse_local_reference, POS_TO_VERBOSE, ParsedExpression

class SemanticFieldManager(models.Manager):
    def make_field(self, heading, pos):
        uri = ""
        roots = self.filter(parent__isnull=True)
        siblings = [c for c in roots if c.parsed_path.last_uri == uri]

        dupe = any(c for c in siblings if c.pos == pos and
                   c.heading == heading)
        if dupe:
            raise ValueError(
                ("There is already a semantic field in the namespace '{0}', "
                 "with pos '{1}' and heading '{2}'.")
                .format(uri, pos, heading))

        max_child = 0 if len(siblings) == 0 else  \
            max(c.parsed_path.last_level_number for c in siblings)

        # The looping and exception handling here is to handle a
        # possible race if two users try to create a new field at
        # the same time.
        while True:
            max_child += 1
            desired_path = ParsedExpression.make(uri, max_child, pos)
            sf = SemanticField(path=desired_path,
                               heading=heading,
                               parent=None)
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


class SemanticField(models.Model):
    objects = SemanticFieldManager()
    catid = models.IntegerField(unique=True, null=True)
    _path = models.TextField(unique=True, name="path", db_column="path")
    parent = models.ForeignKey(
        "self", related_name="children", null=True, blank=True)
    heading = models.TextField()

    def make_child(self, heading, pos):
        ref = self.parsed_path

        # This will have to be modified when we allow user-based
        # custom fields.
        if ref.branches:
            # This is a current limitation of BTW
            assert len(ref.branches) == 1
            branch = ref.branches[-1]

            # This is a current limitation of BTW. BTW branches have
            # an empty URI.
            assert branch.uri == ""

        children = self.children.all()

        # Right now we can only create semantic fields in the BTW
        # namespace, which has the empty string URI.
        uri = ""

        # The siblings use the same URI as the child we want to create
        siblings = [c for c in children if c.parsed_path.last_uri == uri]
        dupe = any(c for c in siblings if c.pos == pos and
                   c.heading == heading)
        if dupe:
            raise ValueError(
                ("There is already a semantic field in the namespace '{0}', "
                 "with pos '{1}' and heading '{2}'.")
                .format(uri, pos, heading))

        max_child = 0 if len(siblings) == 0 else  \
            max(c.parsed_path.last_level_number for c in siblings)

        # The looping and exception handling here is to handle a
        # possible race if two users try to create a new field at
        # the same time.
        while True:
            max_child += 1
            desired_path = ref.make_child(uri, max_child, pos)
            sf = SemanticField(path=desired_path,
                               heading=heading,
                               parent=self)
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

    @property
    def detail_url(self):
        return reverse('semantic_fields_semanticfield-detail',
                       args=(self.pk, ))

    @property
    def add_child_url(self):
        return reverse('semantic_fields_semanticfield-children',
                       args=(self.pk, ))

    @property
    def add_child_form_url(self):
        return reverse('semantic_fields_semanticfield-add-child-form',
                       args=(self.pk, ))

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, val):
        self._path = val
        self._parsed_path = None
        self._related_by_pos = None

    _parsed_path = None

    @property
    def parsed_path(self):
        pp = self._parsed_path
        if pp is not None:
            return pp

        parsed = parse_local_reference(self.path)
        self._parsed_path = parsed
        return parsed

    _related_by_pos = None

    @property
    def related_by_pos(self):
        rp = self._related_by_pos

        if rp is not None:
            return rp

        ref = self.parsed_path
        related = ref.related_by_pos()
        related = \
            SemanticField.objects.filter(
                path__in=(unicode(x) for x in related))
        self._related_by_pos = related
        return related

    @property
    def pos(self):
        return self.parsed_path.pos

    @property
    def verbose_pos(self):
        return POS_TO_VERBOSE[self.pos]

    @property
    def heading_and_pos(self):
        return "{0} ({1})".format(self.heading, self.verbose_pos)

    @property
    def is_subcat(self):
        return self.parsed_path.hte_subcats is not None

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
            text = self.heading

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

class Lexeme(models.Model):

    class Meta:
        unique_together = ("semantic_field", "catorder")
        ordering = ["catorder"]

    htid = models.IntegerField(primary_key=True)
    # This field is our real foreign key. We convert the HTE
    # field catid to it.
    semantic_field = models.ForeignKey(SemanticField)
    word = models.CharField(max_length=60)
    fulldate = models.CharField(max_length=90)
    catorder = models.IntegerField()

class SearchWord(models.Model):
    sid = models.IntegerField(primary_key=True)
    htid = models.ForeignKey(Lexeme)
    searchword = models.CharField(max_length=60, db_index=True)
    type = models.CharField(max_length=3)
