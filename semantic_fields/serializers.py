from rest_framework import serializers
from .models import SemanticField

class SemanticFieldSerializer(serializers.ModelSerializer):

    class Meta:
        model = SemanticField
        fields = ("path", "heading", "parent")
