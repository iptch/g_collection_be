from rest_framework import serializers

from .models import Card, User


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'name']


class CardSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Card
        fields = ['name', 'acronym', 'team', 'job', 'superpower', 'highlight', 'must_have', 'image_link']
