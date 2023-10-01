from django.utils import timezone
from rest_framework import status, viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from genius_collection.core.serializers import UserSerializer, CardSerializer

from .models import Card, User, Ownership
from .jwt_validation import JWTAccessTokenAuthentication


class UserViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API endpoint that allows users to be viewed or initialized.
    """
    authentication_classes = [JWTAccessTokenAuthentication]
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=['post'], url_path='init',
            description='Checks if an user exists. If not, the user is initialized')
    def init(self, request):
        try:
            current_user = User.objects.get(email=request.user['email'])
            last_login = current_user.last_login
            current_user.last_login = timezone.now()
            current_user.save()
            return Response(
                data={'status': f'User in Datenbank gefunden.',
                      'user': self.get_serializer(current_user).data,
                      'last_login': last_login})
        except User.DoesNotExist:
            user, self_card_assigned = User.objects.create_user(first_name=request.user['first_name'],
                                                                last_name=request.user['last_name'],
                                                                email=request.user['email'])

            return Response(status=status.HTTP_201_CREATED,
                            data={'status': 'User erfolgreich erstellt.',
                                  'user': self.get_serializer(user).data,
                                  'last_login': None,
                                  'self_card_assigned': self_card_assigned})


class CardViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API endpoint that allows cards to be viewed or transferred.
    """
    authentication_classes = [JWTAccessTokenAuthentication]
    queryset = Card.objects.all()
    serializer_class = CardSerializer

    @action(detail=False, methods=['post'], url_path='transfer',
            description='Removes a card from the giver and adds it to the current user.')
    def transfer(self, request):
        giver = User.objects.get(email=request.data['giver'])
        card = Card.objects.get(id=request.data['id'])

        try:
            ownership = Ownership.objects.get(user=giver, card=card)
        except Ownership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND,
                            data={'status': f'Der Sender besitzt diese Karte nicht.'})

        if ownership.otp_value != request.data['otp']:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={'status': f'Das OTP stimmt nicht mit dem in der Datenbank überein.'})

        if ownership.otp_valid_to < timezone.now():
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={
                                'status': f'Das OTP ist nicht mehr gültig. Bitte den Sender, die Karte neu zu laden.'})
        current_user = User.objects.get(email=request.user['email'])
        giver_ownership, receiver_ownership = Ownership.objects.transfer_ownership(current_user, ownership, card)
        if giver_ownership is None:
            return Response({'status': f'Karte erfolgreich transferiert. {receiver_ownership}.'})
        else:
            return Response({'status': f'Karte erfolgreich transferiert. {giver_ownership} und {receiver_ownership}.'})


class OverviewViewSet(APIView):
    """
    API endpoint that gives a score and ranking overview for the current user.
    """
    authentication_classes = [JWTAccessTokenAuthentication]

    @action(methods=['get'], detail=False, description='Returns the score and ranking overview for the current user.')
    def get(self, request):
        user_cards = User.objects.get(email=request.user['email']).cards.all()

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
    """
    API endpoint that allows admins to distribute cards to users.
    """
    authentication_classes = [JWTAccessTokenAuthentication]

    @action(methods=['post'], detail=False, description='Distributes cards to a list of users or to all users.')
    def post(self, request):
        current_user = User.objects.get(email=request.user['email'])
        if not current_user.is_admin:
            return Response(status=status.HTTP_403_FORBIDDEN,
                            data={'status': f'Du bist kein Admin.'})
        receivers = []
        if request.data['receivers'] == 'all':
            receivers = User.objects.all()
        else:
            for r in request.data['receivers']:
                receivers.append(User.objects.get(email=r))
        for receiver in receivers:
            Ownership.objects.distribute_random_cards(receiver, int(request.data['quantity']))

        return Response(
            {'status': f'{request.data["quantity"]} Karten erfolgreich verteilt.'})
