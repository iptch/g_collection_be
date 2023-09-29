from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
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


class OverviewViewSet(APIView):

    authentication_classes = [JWTAccessTokenAuthentication]

    @action(methods=['get'], detail=False)
    def get(self, request, *args, **kwargs):

        # TODO Implement getUserEmailFromToken()
        email = getUserEmailFromToken()
        user_cards = User.objects.get(email=email).cards.all()

        rankings = [{
            'uniqueCardsCount': u.cards.count(),
            'displayName': u.name,
            'userEmail': u.email
        } for u in User.objects.all()]
        rankings.sort(key=lambda r: r['uniqueCardsCount'], reverse=True)
        for i in range(len(rankings)):
            rankings[i]['rank'] = i

        return Response({
            'myCardsCount': user_cards.count(),
            'myUniqueCardsCount': user_cards.distinct().count(),
            'allCardsCount': Card.objects.all().count(),
            'duplicateCardsCount': user_cards.count() - user_cards.distinct().count(),
            'rankingList': rankings
        })
