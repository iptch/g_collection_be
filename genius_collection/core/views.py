from rest_framework import viewsets
from genius_collection.core.serializers import UserSerializer, CardSerializer

from .models import Card, User
from .jwt_validation import JWTAccessTokenAuthentication


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    authentication_classes = [JWTAccessTokenAuthentication]
    queryset = User.objects.all()
    serializer_class = UserSerializer


class CardViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows cards to be viewed or edited.
    """
    authentication_classes = [JWTAccessTokenAuthentication]
    queryset = Card.objects.all()
    serializer_class = CardSerializer
