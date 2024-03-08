import random
from django.utils import timezone
from rest_framework import status, viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from genius_collection.core.serializers import UserSerializer, CardSerializer
from django.db.models import Sum
from django.db import connection, IntegrityError
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core import serializers
from django.forms.models import model_to_dict
from .models import Card, User, Ownership, Distribution
from .models import Card, Quiz, User, Ownership, Distribution
from .jwt_validation import JWTAccessTokenAuthentication
from genius_collection.core.blob_sas import get_blob_sas_url
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import pandas as pd
import json


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

            user_card = Card.objects.filter(email=current_user.email)

            return Response(
                data={'status': f'User in Datenbank gefunden.',
                      'user': self.get_serializer(current_user).data,
                      "card_id": user_card.get().pk if user_card.exists() else None,
                      'last_login': last_login})
        except User.DoesNotExist:
            user, self_card_assigned = User.objects.create_user(first_name=request.user['first_name'],
                                                                last_name=request.user['last_name'],
                                                                email=request.user['email'])

            return Response(status=status.HTTP_201_CREATED,
                            data={'status': 'User erfolgreich erstellt.',
                                  'user': self.get_serializer(user).data,
                                  'last_login': None,
                                  "card_id": None,
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

        query = """
            with co as (
            select
                *
            from
                core_ownership co
            join core_user cu on
                co.user_id = cu.id
            where
                cu.email = %s)
            select
                coalesce(co.quantity, 0) as quantity,
                co.last_received,
                cc.*
            from
                core_card cc
            left join co on
                cc.id = co.card_id
        """
        cursor.execute(query, [request.user['email']])
        card_dicts = self.dict_fetchall(cursor)
        cards = [dict(c, **{'image_url': get_blob_sas_url('card-thumbnails', c['email'])}) for c in card_dicts]
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
            is_initial_card_creation = False
        except Card.DoesNotExist:
            user_card = Card()
            is_initial_card_creation = True

        # Update the fields of the user_card object with the data provided in the request
        user_card.name = request.data.get('name', f'{request.user["first_name"]} {request.user["last_name"]}')
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
                            data={'status': 'Validation error', 'error': str(e)})

        # Save the updated user_card object back to the database
        try:
            user_card.save()
        except IntegrityError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={'status': 'Could not save the card.', 'error': str(e)})

        if is_initial_card_creation:
            # give the user x times his own card
            current_user = User.objects.get(email=request.user['email'])
            Ownership.objects.distribute_self_cards_to_user(current_user, 20)

        return Response(CardSerializer(user_card, context={'request': request}).data)


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
            'userEmail': u.email,
            'last_received_unique': u.last_received_unique
        } for u in User.objects.all()]
        rankings.sort(key=lambda r: (
            -r['uniqueCardsCount'], r['last_received_unique'] is None, r['last_received_unique'], r['userEmail']))
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


class PictureViewSet(APIView):
    """
    API endpoint that uploads a picture for the current user.
    """
    authentication_classes = [JWTAccessTokenAuthentication]

    @action(methods=['get'], detail=False, description='Gets the URL to the picture in original quality.')
    def get(self, request):
        email = request.user['email']
        image_url = get_blob_sas_url('card-originals', email)
        return Response(image_url)

    @action(methods=['post'], detail=False,
            description='Uploads a picture for the current user to the Azure Blob Container.')
    def post(self, request):
        file = request.FILES['file']
        if file.content_type != 'image/jpeg':
            return Response({'status': 'Bild muss vom Typ JPEG sein'}, status=status.HTTP_400_BAD_REQUEST)

        if file.size > 10 * 1024 * 1024:  # 10MB in bytes
            return Response({'status': 'Bild darf maximal 10MB gross sein.'}, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate with managed identity
        credential = DefaultAzureCredential()

        # Connect to Azure Blob Storage
        blob_service_client = BlobServiceClient(account_url="https://gcollection.blob.core.windows.net",
                                                credential=credential)
        container_client = blob_service_client.get_container_client("card-originals")

        # Upload file to Azure Blob Storage
        email = request.user['email']
        blob_client = container_client.get_blob_client(f'{email}.jpg')
        blob_client.upload_blob(file, overwrite=True)

        # URL of the uploaded image
        image_url = get_blob_sas_url('card-originals', email)

        return Response(image_url)


class QuizQuestionViewSet(viewsets.GenericViewSet):
    """
    API endpoint that allows quiz questions to be viewed and answered
    """
    authentication_classes = [JWTAccessTokenAuthentication]

    """
    API endpoint that checks if the answer is correct.
    """

    # @action(detail=False, methods=['post'], url_path='answer',
    #         description='Checks if the answer is correct.')
    # def answer(self, request, pk=None):
    #     question = QuizQuestion.objects.get(id=request.data['question'])
    #     answer = QuizAnswer.objects.get(id=request.data['answer'])
    #
    #     answer_is_correct = (answer == question.correct_answer)
    #
    #     if (question.given_answer is not None):
    #         return Response(status=status.HTTP_400_BAD_REQUEST, data={
    #             'status': 'Du hast diese Frage bereits beantwortet.'
    #         })
    #
    #     question.given_answer = answer
    #     question.answer_timestamp = timezone.now()
    #     question.save()
    #
    #     # TODO Update score of the user
    #
    #     return Response(status=status.HTTP_200_OK, data={
    #         'isCorrect': answer_is_correct,
    #         "correctAnswer": question.correct_answer.id
    #     })

    """
    API endpoint that returns a question based on request
    """

    @action(detail=False, methods=['post'], url_path='question',
            description='Returns 4 random cards for the quiz.')
    def question(self, request, pk=None):
        # TODO filter that only people are selected, which filled out answers for the question/answers
        # flow:
        # 1. filter/where clause to check that answer and question type are both not null
        # 2. make a groupby on the answer-column to get distinct values (preventing multiple times e.g. "Senior Consultant" as answer)
        # 3. select a subset of n cards
        answer_possibility_count = int(request.data.get('answer_possibilities', '4'))
        question_type = request.data.get('question_type', 'IMAGE')
        answer_type = request.data.get('answer_type', 'NAME')

        cursor = connection.cursor()
        query = f"""
            SELECT email
            FROM core_card cc
            WHERE  1=1 
            AND %s IS NOT NULL
            AND %s IS NULL
            ORDER BY RANDOM()
            LIMIT 4;
        """

        cursor.execute(query, [str.lower(question_type), str.lower(answer_type)])
        usable_card_emails = [i[0] for i in cursor.fetchall()]
        # usable_cards = Card.objects
        # if Quiz.QuizType.WISH_DESTINATION in [question_type, answer_type]:
        #     usable_cards = usable_cards.exclude(wish_destination='')
        # if Quiz.QuizType.WISH_PERSON in [question_type, answer_type]:
        #     usable_cards = usable_cards.exclude(wish_person__isnull='')
        # if Quiz.QuizType.WISH_SKILL in [question_type, answer_type]:
        #     usable_cards = usable_cards.exclude(wish_skill='')
        # if Quiz.QuizType.BEST_ADVICE in [question_type, answer_type]:
        #     usable_cards = usable_cards.exclude(best_advice='')
        #
        # answer_possibility_cards = usable_cards.order_by('?')[0:answer_possibility_count]
        answer_possibility_cards = Card.objects.filter(email__in=usable_card_emails)
        # answer_possibility_cards = Card.objects.filter(answer_card__id__in=usable_card_ids).order_by('?')[0:answer_possibility_count]
        answer_possibility_cards = Card.objects

        answer_id = random.randrange(len([answer_possibility_cards]))
        question_true_card = answer_possibility_cards[answer_id]
        if question_type == Quiz.QuizType.IMAGE:
            input_value = None
            image_url = get_blob_sas_url('card-thumbnails', question_true_card.email)
        else:
            image_url = None
            input_value = getattr(question_true_card, str.lower(question_type))

        if answer_type == Quiz.QuizType.IMAGE:
            answer_possibilities = [{'card_id': c.id, 'answer_value': c.name} for c in
                                    list(answer_possibility_cards)]
        else:
            answer_possibilities = [{'card_id': c.id, 'answer_value': getattr(c, str.lower(answer_type))} for c in
                                    list(answer_possibility_cards)]
        quiz = Quiz.objects.create(
            user=User.objects.get(email=request.user['email']),
            question_type=question_type,
            answer_type=answer_type,
            question_true_card=question_true_card
        )
        quiz.save()
        try:
            question_answer_tuple = {
                'question_type': question_type,
                'image_url': image_url,
                'answer_type': answer_type,
                'answer_possibilities': answer_possibilities,
                'question_string': self.get_question_string(question_type, answer_type, input_value)
            }
            return Response(status=status.HTTP_201_CREATED, data=question_answer_tuple)
        except KeyError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=str(e))

    @staticmethod
    def get_question_string(question_type, answer_type, input_value):
        mapping = {
            Quiz.QuizType.IMAGE: {
                Quiz.QuizType.NAME: 'Wen siehst du auf diesem Bild?',
                Quiz.QuizType.JOB: 'Welche Position hat die Person im Bild?',
                Quiz.QuizType.ACRONYM: 'Was ist das Kürzel dieser Person?',
                Quiz.QuizType.START_AT_IPT: 'Wann hat diese Person in der ipt angefangen?',
                Quiz.QuizType.WISH_DESTINATION: 'Wo wollte diese Person schon immer mal hin?',
                Quiz.QuizType.WISH_PERSON: 'Mit wem wollte diese Person schon immer mal tauschen?',
                Quiz.QuizType.WISH_SKILL: 'Was wollte diese Person schon immer einmal lernen?',
                Quiz.QuizType.BEST_ADVICE: 'Was ist der beste berufliche Ratschlag von dieser Person?'
            },
            Quiz.QuizType.NAME: {
                Quiz.QuizType.IMAGE: f'Welches Bild zeigt {input_value}?',
                Quiz.QuizType.JOB: f'Welche Position hat {input_value} inne?',
                Quiz.QuizType.START_AT_IPT: f'Wann hat {input_value} in der ipt angefangen?',
                Quiz.QuizType.WISH_DESTINATION: f'Wo wollte {input_value} schon immer mal hin?',
                Quiz.QuizType.WISH_PERSON: f'Mit wem wollte {input_value} schon immer mal tauschen?',
                Quiz.QuizType.WISH_SKILL: f'Was wollte {input_value} schon immer einmal lernen?',
                Quiz.QuizType.BEST_ADVICE: f'Was ist der beste berufliche Ratschlag von {input_value}?'
            },
            Quiz.QuizType.WISH_DESTINATION: {
                Quiz.QuizType.NAME: f'Da würde ich am liebsten hinreisen: "{input_value}". Wer hat das gesagt?'
            },
            Quiz.QuizType.WISH_PERSON: {
                Quiz.QuizType.NAME: f'Am liebsten tauschen würde ich mit: "{input_value}". Wer hat das gesagt?'
            },
            Quiz.QuizType.WISH_SKILL: {
                Quiz.QuizType.NAME: f'Das wollte ich schon immer mal erlernen: "{input_value}". Wer hat das gesagt?'
            },
            Quiz.QuizType.BEST_ADVICE: {
                Quiz.QuizType.NAME: f'Der beste Ratschlag ist: "{input_value}". Wer hat das gesagt?'
            }
        }

        try:
            return mapping[question_type][answer_type]
        except KeyError:
            raise KeyError(f'Combination of Question/Answer not allowed: ({question_type}/{answer_type})')


class DeleteUserAndCard(APIView):
    """
    API endpoint that deletes a user, its connected card and all ownerships related to the card or user
    """
    authentication_classes = [JWTAccessTokenAuthentication]

    @action(methods=['delete'], detail=False,
            description='Deletes a user, its connected card and all ownerships related to the card or user')
    def delete(self, request):
        current_user = User.objects.get(email=request.user['email'])
        if not current_user.is_admin:
            return Response(status=status.HTTP_403_FORBIDDEN,
                            data={'status': f'Du bist kein Admin.'})
        user_to_delete_email = request.data['user_to_delete']

        try:
            user_to_delete = User.objects.get(email=user_to_delete_email)
            Ownership.objects.filter(user=user_to_delete).delete()
            user_to_delete.delete()
            user_answer = 'User Objekt wurde in der Datenbank gefunden und gelöscht.'
        except ObjectDoesNotExist:
            user_answer = 'User Objekt wurde nicht gelöscht, da es in der Datenbank nicht gefunden wurde.'
        try:
            card_to_delete = Card.objects.get(email=user_to_delete_email)
            Ownership.objects.filter(card=card_to_delete).delete()
            card_to_delete.delete()
            card_answer = 'Card Objekt wurde in der Datenbank gefunden und gelöscht.'
        except ObjectDoesNotExist:
            card_answer = 'Card Objekt wurde nicht gelöscht, da es in der Datenbank nicht gefunden wurde.'

        try:
            # Authenticate with managed identity
            credential = DefaultAzureCredential()
            # Connect to Azure Blob Storage
            blob_service_client = BlobServiceClient(account_url="https://gcollection.blob.core.windows.net",
                                                    credential=credential)
            container_client = blob_service_client.get_container_client("card-originals")
            # Upload file to Azure Blob Storage
            container_client.delete_blob(f'{user_to_delete_email}.jpg')
            image_answer = 'Card Image wurde im Storage Container gefunden und gelöscht.'
        except azure.core.exceptions.ResourceNotFoundError:
            image_answer = 'Card Image wurde nicht gelöscht, da es im Storage Container nicht gefunden wurde.'

        return Response(
            {'status': f'User-Email: [{user_to_delete_email}]. {user_answer} {card_answer} {image_answer}'})
