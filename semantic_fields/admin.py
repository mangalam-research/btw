from django.contrib import admin

# Register your models here.

from .models import SemanticField, Lexeme, SearchWord

admin.site.register(SemanticField)
admin.site.register(Lexeme)
admin.site.register(SearchWord)
