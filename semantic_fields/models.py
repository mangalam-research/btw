from django.db import models

class Category(models.Model):
    catid = models.IntegerField(unique=True, max_length=7, null=True)
    path = models.TextField(unique=True)
    parent = models.ForeignKey(
        "self", related_name="children", null=True, blank=True)
    heading = models.TextField()

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

class Lexeme(models.Model):

    class Meta:
        unique_together = ("category", "catorder")

    htid = models.IntegerField(primary_key=True, max_length=7)
    # The category field is our real foreign key. We convert the HTE
    # field catid to it.
    category = models.ForeignKey(Category)
    word = models.CharField(max_length=60)
    fulldate = models.CharField(max_length=90)
    catorder = models.IntegerField(max_length=3)

class SearchWord(models.Model):
    sid = models.IntegerField(primary_key=True, max_length=7)
    htid = models.ForeignKey(Lexeme)
    searchword = models.CharField(max_length=60, db_index=True)
    type = models.CharField(max_length=3)
