from rest_framework import serializers

from .models import Card, User, Ownership
from genius_collection.core.blob_sas import get_blob_sas_url


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'name']


class CardSerializer(serializers.HyperlinkedModelSerializer):
    image_url = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = ['id', 'name', 'acronym', 'team', 'job', 'superpower', 'highlight', 'must_have', 'image_url',
                  'quantity']

    def get_image_url(self, obj):
        return get_blob_sas_url(obj.image_link)

    def get_quantity(self, obj):
        result = Ownership.objects.filter(card=obj, user=self.context["request"].user).first()

        if result is None:
            return 0
        else:
            return result.quantity
