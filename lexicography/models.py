from django.db import models
from django.core.urlresolvers import reverse
import hashlib
import btw.settings as settings

CHANGE_TYPE = (
    ('C', "Creation"),
    ('U', "Update"),
    ('D', "Deletion")
)

CHANGE_SUBTYPE = (
    ('A', "Automatic"),
    ('M', "Manual"),
    ('R', "Recovery")
)

class ChangeInfo(models.Model):
    # Yep, arbitrarily limited to 1K. CharField() needs a limit. We
    # could use TextField() but the flexibility there comes at a cost.
    headword = models.CharField(max_length=1024)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    datetime = models.DateTimeField()
    session = models.CharField(max_length=100, null=True)
    ctype = models.CharField(max_length=1, choices=CHANGE_TYPE)
    csubtype = models.CharField(max_length=1, choices=CHANGE_SUBTYPE)
    c_hash = models.ForeignKey('Chunk')
    class Meta:
        abstract = True

    def copy_to(self, to):
        if not isinstance(to, ChangeInfo):
            raise ValueError("to is not of the right class")
        for i in ChangeInfo._meta.get_all_field_names():
            setattr(to, i, getattr(self, i))

class Entry(ChangeInfo):
    class Meta:
        verbose_name_plural = "Entries"
        unique_together = (("headword"), )
        # This is really application-wide but Django insists that permissions
        # be associated with specific models.
        permissions = (('garbage_collect', "Perform a garbage collection."),
                       )

    def __unicode__(self):
        return self.headword

    def get_absolute_url(self):
        return reverse('lexicography-details', args=[str(self.id)])

class ChangeRecord(ChangeInfo):
    entry = models.ForeignKey(Entry)

    class Meta:
        unique_together = (("entry", "datetime", "ctype"), )

    def __unicode__(self):
        return self.entry.headword + " " + self.user.username + " " + \
            str(self.datetime) + " " + (self.session or "")

class Chunk(models.Model):
    c_hash = models.CharField(max_length=40, primary_key=True)
    data = models.TextField()

    def __unicode__(self):
        return self.c_hash

    def clean(self):
        sha1 = hashlib.sha1()
        sha1.update(self.data.encode('utf-8'))
        self.c_hash = sha1.hexdigest()
