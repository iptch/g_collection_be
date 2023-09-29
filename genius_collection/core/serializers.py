from rest_framework import serializers

from .models import Card, User
from genius_collection.core.blob_sas import get_blob_sas_url


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'name']


class CardSerializer(serializers.HyperlinkedModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = ['id', 'name', 'acronym', 'team', 'job', 'superpower', 'highlight', 'must_have', 'image_url', 'owned']
    
    def get_image_url(self, obj):
        return get_blob_sas_url(obj.image_link)
