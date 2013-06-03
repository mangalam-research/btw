from django.db import models
from django.core.urlresolvers import reverse

class Entry(models.Model):
    # Yep, arbitrarily limited to 1K. CharField() needs a limit. We
    # could use TextField() but the flexibility there comes at a cost.
    headword = models.CharField(max_length=1024)
    creation_datetime = models.DateTimeField(auto_now_add=True)
    data = models.TextField()

    class Meta:
        verbose_name_plural = "Entries"
        unique_together = (("headword", "creation_datetime"), )

    def __unicode__(self):
        return self.headword

    def get_absolute_url(self):
        return reverse('lexicography-details', args=[str(self.id)])
