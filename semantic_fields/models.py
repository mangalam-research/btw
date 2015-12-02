from django.db import models, IntegrityError
from django.core.urlresolvers import reverse
from django.utils.html import mark_safe, escape

from .util import parse_local_reference, POS_TO_VERBOSE

class SemanticField(models.Model):
    catid = models.IntegerField(unique=True, max_length=7, null=True)
    _path = models.TextField(unique=True, name="path", db_column="path")
    parent = models.ForeignKey(
        "self", related_name="children", null=True, blank=True)
    heading = models.TextField()

    def make_child(self, heading, pos):
        ref = parse_local_reference(self.path)

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

        max_child = 0 if not children.exists() else  \
            max(parse_local_reference(c.path).last_level_number
                for c in children)

        # The looping and exception handling here is to handle a
        # possible race if two users try to create a new field at
        # the same time.
        while True:
            max_child += 1
            desired_path = ref.make_child('', max_child, pos)
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
    def create_url(self):
        # We create by POSTing to the list URL
        return reverse('semantic_fields_semanticfield-list')

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

class Lexeme(models.Model):

    class Meta:
        unique_together = ("semantic_field", "catorder")
        ordering = ["catorder"]

    htid = models.IntegerField(primary_key=True, max_length=7)
    # This field is our real foreign key. We convert the HTE
    # field catid to it.
    semantic_field = models.ForeignKey(SemanticField)
    word = models.CharField(max_length=60)
    fulldate = models.CharField(max_length=90)
    catorder = models.IntegerField(max_length=3)

class SearchWord(models.Model):
    sid = models.IntegerField(primary_key=True, max_length=7)
    htid = models.ForeignKey(Lexeme)
    searchword = models.CharField(max_length=60, db_index=True)
    type = models.CharField(max_length=3)
