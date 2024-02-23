from django.utils import timezone
from rest_framework import status, viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from genius_collection.core.serializers import UserSerializer, CardSerializer
from django.db.models import Sum
from django.db import connection, IntegrityError
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from .models import Card, User, Ownership, Distribution
from .jwt_validation import JWTAccessTokenAuthentication
from genius_collection.core.blob_sas import get_blob_sas_url


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
                      'last_login': last_login,
                      'user_card_exists': Card.objects.exists(email=current_user.email)})
        except User.DoesNotExist:
            user, self_card_assigned = User.objects.create_user(first_name=request.user['first_name'],
                                                                last_name=request.user['last_name'],
                                                                email=request.user['email'])

            return Response(status=status.HTTP_201_CREATED,
                            data={'status': 'User erfolgreich erstellt.',
                                  'user': self.get_serializer(user).data,
                                  'last_login': None,
                                  'self_card_assigned': self_card_assigned})

class CardViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    # class CardViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API endpoint that allows cards to be viewed, modified or transferred.
    """
    authentication_classes = [JWTAccessTokenAuthentication]
    queryset = Card.objects.all()
    serializer_class = CardSerializer

    @staticmethod
    def dict_fetchall(cursor):
        """Return all rows from a cursor as a dict"""
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    def list(self, request, *args, **kwargs):
        # Override the list method to circumvent the serializer calling the DB many times
        # https://www.cdrf.co/3.9/rest_framework.viewsets/ReadOnlyModelViewSet.html#list
        cursor = connection.cursor()

        query = f"""
            with co as (
            select
                *
            from
                core_ownership co
            join core_user cu on
                co.user_id = cu.id
            where
                cu.email = '{request.user['email']}')
            select
                coalesce(co.quantity,
                0) as quantity,
                co.last_received,
                cc.*
            from
                core_card cc
            left join co on
                cc.id = co.card_id
        """
        cursor.execute(query)
        card_dicts = self.dict_fetchall(cursor)
        cards = [dict(c, **{'image_url': get_blob_sas_url('card-thumbnails', c['acronym'])}) for c in card_dicts]
        return Response(cards)

    @action(detail=False, methods=['post'], url_path='transfer',
            description='Removes a card from the giver and adds it to the current user.')
    def transfer(self, request):
        giver = User.objects.get(email=request.data['giver'])
        card = Card.objects.get(id=request.data['id'])
        current_user = User.objects.get(email=request.user['email'])

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

        if ownership.user == current_user:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={'status': f'Du kannst nicht mit dir selbst tauschen.'})

        giver_ownership, receiver_ownership = Ownership.objects.transfer_ownership(current_user, ownership, card)
        if giver_ownership is None:
            return Response({'status': f'Karte erfolgreich transferiert. {receiver_ownership}.'})
        else:
            return Response({'status': f'Karte erfolgreich transferiert. {giver_ownership} und {receiver_ownership}.'})

    @action(detail=False, methods=['post'], url_path='modify',
            description='Modifies the card from the current user.')
    def modify(self, request):        
        # Retrieve the user_card object from the database
        try:
            user_card = Card.objects.get(email=request.user['email'])
        except Card.DoesNotExist:
            user_card = Card()
        
        # Update the fields of the user_card object with the data provided in the request
        user_card.name = request.data.get('name', f'{request.user['first_name']} {request.user['last_name']}')
        user_card.acronym = request.data.get('acronym', user_card.acronym)
        user_card.job = request.data.get('job', user_card.job)
        user_card.start_at_ipt = request.data.get('start_at_ipt', user_card.start_at_ipt)
        user_card.email = request.data.get('email', request.user['email'])
        user_card.wish_destination = request.data.get('wish_destination', user_card.wish_destination)
        user_card.wish_person = request.data.get('wish_person', user_card.wish_person)
        user_card.wish_skill = request.data.get('wish_skill', user_card.wish_skill)
        user_card.best_advice = request.data.get('best_advice', user_card.best_advice)
        
        # Validate the updated user_card object
        try:
            user_card.full_clean()
        except ValidationError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={'status': 'Validation error', 'errors': dict(e)})
        
        # Save the updated user_card object back to the database
        try:
            user_card.save()
        except IntegrityError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={'status': 'Could not save the card.', 'error': str(e)})
        
        return Response({'status': 'Card updated successfully.'})

class OverviewViewSet(APIView):
    """
    API endpoint that gives a score and ranking overview for the current user.
    """
    authentication_classes = [JWTAccessTokenAuthentication]

    @action(methods=['get'], detail=False, description='Returns the score and ranking overview for the current user.')
    def get(self, request):
        user_cards = User.objects.get(email=request.user['email']).cards.all()
        total_quantity = Ownership.objects.aggregate(total_quantity=Sum('quantity'))['total_quantity']

        rankings = [{
            'uniqueCardsCount': u.cards.count(),
            'displayName': str(u),
            'userEmail': u.email
        } for u in User.objects.all()]
        rankings.sort(key=lambda r: (-r['uniqueCardsCount'], r['userEmail']))
        for i in range(len(rankings)):
            rankings[i]['rank'] = i + 1

        try:
            last_dist = Distribution.objects.latest('timestamp').timestamp
        except ObjectDoesNotExist:
            last_dist = None


        return Response({
            'myCardsCount': user_cards.count(),
            'totalCardQuantity': total_quantity,
            'myUniqueCardsCount': user_cards.distinct().count(),
            'allCardsCount': Card.objects.all().count(),
            'duplicateCardsCount': user_cards.count() - user_cards.distinct().count(),
            'rankingList': rankings,
            'lastDistribution': last_dist
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
        qty = int(request.data['quantity'])
        receivers = request.data['receivers']
        distribution = Distribution(quantity=qty, user=current_user, receiver=receivers)
        distribution.save()

        receiver_users = []
        if receivers == 'all':
            receiver_users = User.objects.all()
        else:
            for r in receivers:
                receiver_users.append(User.objects.get(email=r))
        for receiver_user in receiver_users:
            Ownership.objects.distribute_random_cards(receiver_user, qty)

        return Response(
            {'status': f'{len(receiver_users)} * {qty} = {len(receiver_users) * qty} Karten erfolgreich verteilt.'})
