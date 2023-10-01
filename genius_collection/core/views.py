from django.utils import timezone
from rest_framework import status, viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from genius_collection.core.serializers import UserSerializer, CardSerializer

from .models import Card, User, Ownership
from .jwt_validation import JWTAccessTokenAuthentication
from .helper.ownership_helper import OwnershipHelper


class UserViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    authentication_classes = [JWTAccessTokenAuthentication]
    queryset = User.objects.all()
    serializer_class = UserSerializer


class CardViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API endpoint that allows cards to be viewed or edited.
    """
    authentication_classes = [JWTAccessTokenAuthentication]
    queryset = Card.objects.all()
    serializer_class = CardSerializer

    @action(detail=False, methods=['post'], url_path='transfer')
    def transfer(self, request):
        giver = User.objects.get(email=request.data['giver'])
        card = Card.objects.get(id=request.data['id'])

        try:
            ownership = Ownership.objects.get(user=giver, card=card)
        except Ownership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND,
                            data={'status': f'The giver does not own this card.'})

        if ownership.otp_value != request.data['otp']:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={'status': f'The OTP does not match with the one stored in the database.'})

        if ownership.otp_valid_to < timezone.now():
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={'status': f'The OTP is no longer valid. Tell the giver to reload the card!'})

        giver_ownership, receiver_ownership = OwnershipHelper.transfer_ownership(request.user, ownership, card)
        if giver_ownership is None:
            return Response({'status': f'Card transferred successfully. Now {receiver_ownership}.'})
        else:
            return Response(
                {'status': f'Card transferred successfully. Now {giver_ownership} and {receiver_ownership}'})


class OverviewViewSet(APIView):
    authentication_classes = [JWTAccessTokenAuthentication]

    @action(methods=['get'], detail=False)
    def get(self, request):
        user_cards = User.objects.get(email=request.user.email).cards.all()

        rankings = [{
            'uniqueCardsCount': u.cards.count(),
            'displayName': str(u),
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


class DistributeViewSet(APIView):
    authentication_classes = [JWTAccessTokenAuthentication]

    @action(methods=['post'], detail=False)
    def post(self, request):
        if not request.user.is_admin:
            return Response(status=status.HTTP_403_FORBIDDEN,
                            data={'status': f'You are not an admin.'})
        receivers = []
        if request.data['receivers'] == 'all':
            receivers = User.objects.all()
        else:
            for r in request.data['receivers']:
                receivers.append(User.objects.get(email=r))
        for receiver in receivers:
            Ownership.objects.assign_ownership(receiver, int(request.data['quantity']))

        return Response(
            {'status': f'{request.data["quantity"]} cards successfully distributed to {request.data["receivers"]}.'})
