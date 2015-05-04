from rest_framework import serializers
from .models import Item, PrimarySource

class ItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = Item
        fields = ("pk", "date", "title", "creators", "url",
                  "abstract_url", "zotero_url")

class PrimarySourceSerializer(serializers.ModelSerializer):
    item = ItemSerializer(read_only=True)

    class Meta:
        model = PrimarySource
        fields = ("reference_title", "genre", "pk", "url",
                  "abstract_url", "item")

class ItemAndPrimarySourceSerializer(serializers.BaseSerializer):

    def to_representation(self, value):
        if isinstance(value, Item):
            class_ = ItemSerializer
        elif isinstance(value, PrimarySource):
            class_ = PrimarySourceSerializer

        return class_(instance=value).data
