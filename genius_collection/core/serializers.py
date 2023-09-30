from rest_framework import serializers
from datetime import timedelta
from django.utils import timezone
from random import choice
from string import ascii_lowercase

from .models import Card, User, Ownership
from genius_collection.core.blob_sas import get_blob_sas_url


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'name']


class CardSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Card
        fields = ['id', 'name', 'acronym', 'team', 'job', 'superpower', 'highlight', 'must_have']

    def to_representation(self, obj):
        data = super().to_representation(obj)

        data['image_url'] = get_blob_sas_url(obj.image_link)

        ownership = Ownership.objects.filter(card=obj, user=self.context["request"].user).first()
        if ownership is None:
            data['otp_value'] = None
            data['otp_valid_to'] = None
            data['last_received'] = None
            data['quantity'] = 0
        else:
            ownership.otp_value = ''.join(choice(ascii_lowercase) for _ in range(16))
            ownership.otp_valid_to = timezone.now() + timedelta(minutes=5)
            ownership.save()
            data['otp_value'] = ownership.otp_value
            data['otp_valid_to'] = ownership.otp_valid_to
            data['last_received'] = ownership.last_received
            data['quantity'] = ownership.quantity
        return data
