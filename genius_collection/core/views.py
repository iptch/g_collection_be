from rest_framework import status, viewsets
from rest_framework.request import HttpRequest
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from genius_collection.core.serializers import UserSerializer, CardSerializer

from .models import Card, User, Ownership
from .jwt_validation import JWTAccessTokenAuthentication

from .helper.ownership_helper import OwnershipHelper


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

    def list(self, request):
        # Pass the request to the serializer context
        serializer = CardSerializer(context={'request': request}, many=True)
        data = serializer.to_representation(self.queryset)
        return Response(data)

    @action(detail=False, methods=['post'], url_path='transfer')
    def transfer(self, request: HttpRequest):

        giver: User = User.objects.get(email=request.data["giver"])
        card: Card = Card.objects.get(id=request.data["id"])

        try:
            ownership: Ownership = Ownership.objects.get(user=giver, card=card)
        except Ownership.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=f"Oh Brate, Ownership does not exist!")

        if ownership.otp != request.data["otp"]:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"status": f"Your otp does not match the one in the Database innit."})

        OwnershipHelper.transfer_ownership(request.user, ownership, card)

        return Response({"status": f"Card transfered successfully, Brate, now {ownership}"})


class OverviewViewSet(APIView):
    authentication_classes = [JWTAccessTokenAuthentication]

    @action(methods=['get'], detail=False)
    def get(self, request, *args, **kwargs):
        user_cards = User.objects.get(email=request.user.email).cards.all()

        rankings = [{
            'uniqueCardsCount': u.cards.count(),
            'displayName': u.name,
            'userEmail': u.email
        } for u in User.objects.all()]
        rankings.sort(key=lambda r: r['uniqueCardsCount'], reverse=True)
        for i in range(len(rankings)):
            rankings[i]['rank'] = i + 1

        return Response({
            'myCardsCount': user_cards.count(),
            'myUniqueCardsCount': user_cards.distinct().count(),
            'allCardsCount': Card.objects.all().count(),
            'duplicateCardsCount': user_cards.count() - user_cards.distinct().count(),
            'rankingList': rankings
        })
