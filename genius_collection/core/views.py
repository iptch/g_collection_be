from django.utils import timezone
from rest_framework import status, viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from genius_collection.core.serializers import UserSerializer, CardSerializer
from django.db.models import Sum, Q, Count
from django.db import connection, IntegrityError
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from .models import Card, Quiz, User, Ownership, Distribution
from .jwt_validation import JWTAccessTokenAuthentication
from genius_collection.core.blob_sas import get_blob_sas_url
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import random
from azure.core.exceptions import ResourceNotFoundError
import copy


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

        scores = [{
            'uniqueCardsCount': u.cards.count(),
            'displayName': str(u),
            'userEmail': u.email,
            'last_received_unique': u.last_received_unique,
            'quizScore': u.quiz_score
        } for u in User.objects.all()]
        ranking_cards = copy.deepcopy(sorted(scores, key=lambda r: (
            -r['uniqueCardsCount'], r['last_received_unique'] is None, r['last_received_unique'], r['userEmail'])))
        ranking_quiz = copy.deepcopy(sorted(scores, key=lambda r: (-r['quizScore'], r['userEmail'])))

        for i in range(len(ranking_cards)):
            ranking_cards[i]['rank'] = i + 1
        for i in range(len(ranking_quiz)):
            ranking_quiz[i]['rank'] = i + 1

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
            'rankingCards': ranking_cards,
            'rankingQuiz': ranking_quiz,
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
    API endpoints that allows quiz questions to be viewed and answered
    """
    authentication_classes = [JWTAccessTokenAuthentication]

    @action(detail=False, methods=['post'], url_path='answer',
            description='Checks if the answer is correct.')
    def answer(self, request, pk=None):
        current_user = User.objects.get(email=request.user['email'])
        question = Quiz.objects.get(id=request.data['question_id'])
        given_answer = request.data['answer']

        # Card object has no attribute 'image', since the image URL is not saved in the DB.
        # As a workaround, the front-end sends the email instead to validate the answer.
        answer_type = 'email' if question.answer_type == 'image' else question.answer_type

        correct_answer = getattr(question.question_true_card, answer_type)
        if question.answer_type == 'start_at_ipt':
            correct_answer = correct_answer.strftime("%d.%m.%Y")

        answer_is_correct = (given_answer == correct_answer)

        if question.answer_correct is not None:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={
                'status': 'Du hast diese Frage bereits beantwortet.'
            })

        question.answer_correct = answer_is_correct
        question.answer_timestamp = timezone.now()
        question.save()

        score_change, new_score = self.update_player_score(answer_is_correct, current_user, question.question_type,
                                                           question.answer_type, question.answer_options)

        return Response(status=status.HTTP_200_OK, data={
            'is_correct': answer_is_correct,
            'given_answer': given_answer,
            'correct_answer': correct_answer,
            'score_change': score_change,
            'new_score': new_score
        })

    @staticmethod
    def update_player_score(answer_is_correct, user, question_type, answer_type, answer_options):
        """
        Depending on the question/answer tuple and the number of points award points to the user.
        """
        question_type = str.upper(question_type)
        answer_type = str.upper(answer_type)
        question_value = QuizQuestionViewSet.get_question_mapping(question_type, answer_type)
        if answer_is_correct:
            score_change = question_value
        else:
            # The expected value for "guessing" should be 0, so there is a penalty for wrong answers
            score_change = -round(question_value / (answer_options - 1))
        user.quiz_score += score_change
        user.save()
        return score_change, user.quiz_score

    @staticmethod
    def get_random_question_type(answer_type):
        """
        Depending on the answer_type, return a possible question_type
        """
        mapping = QuizQuestionViewSet.get_question_answer_mapping()
        if answer_type == 'random':
            possible_question_types = list(mapping.keys())
        else:
            possible_question_types = [question for question, answers in mapping.items() if
                                       answer_type in [str(k).lower() for k in answers.keys()]]
        question_type = random.choice(possible_question_types)
        print(question_type)
        return str(question_type).lower()

    @staticmethod
    def get_random_answer_type(question_type):
        """
        Depending on the question_type, return a possible answer_type
        """
        mapping = QuizQuestionViewSet.get_question_answer_mapping()
        if question_type == 'random':
            possible_answer_types = list(mapping.keys())
        else:
            possible_answer_types = list([answers for question, answers in mapping.items() if
                                          question_type == str(question).lower()][0].keys())
        answer_type = random.choice(possible_answer_types)
        print(answer_type)
        return str(answer_type).lower()

    @action(detail=False, methods=['post'], url_path='question',
            description='Returns n random cards for the quiz with the defined question and answer type.')
    def question(self, request, pk=None):
        """
        Get a set of possible cards that can answer the question. Then select one as the correct card.
        """
        answer_options = int(request.data.get('answer_options', 4))
        question_type = request.data.get('question_type', 'image')
        answer_type = request.data.get('answer_type', 'name')
        if question_type == 'random':
            question_type = self.get_random_question_type(answer_type)
        if answer_type == 'random':
            answer_type = self.get_random_answer_type(question_type)

        possible_cards = self.get_possible_cards(question_type, answer_type)

        # take n cards and choose one to be the correct answer
        random.shuffle(possible_cards)
        answer_possible_cards = possible_cards[:answer_options]
        correct_card = random.choice(answer_possible_cards)

        if question_type == 'image':
            question_value = get_blob_sas_url('card-detail-views', correct_card.email)
        elif question_type == 'start_at_ipt':
            question_value = getattr(correct_card, question_type).strftime("%d.%m.%Y")
        else:
            question_value = getattr(correct_card, question_type)
        if answer_type == 'image':
            answer_possible_values = [get_blob_sas_url('card-thumbnails', c.email) for c in answer_possible_cards]
        elif answer_type == 'start_at_ipt':
            answer_possible_values = [getattr(c, answer_type).strftime("%d.%m.%Y") for c in answer_possible_cards]
        else:
            answer_possible_values = [getattr(c, answer_type) for c in answer_possible_cards]

        quiz = Quiz.objects.create(
            user=User.objects.get(email=request.user['email']),
            question_type=question_type,
            answer_type=answer_type,
            question_true_card=correct_card,
            answer_options=answer_options
        )

        quiz.save()

        try:
            question_answer_tuple = {
                'question_id': quiz.id,
                'question_type': question_type,
                'answer_type': answer_type,
                'question_value': question_value,
                'answer_possible_values': answer_possible_values,
                'answer_options': answer_options,
                'question_string': self.get_question_string(question_type, answer_type, question_value)
            }
            return Response(status=status.HTTP_201_CREATED, data=question_answer_tuple)
        except KeyError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=str(e))

    @staticmethod
    def get_possible_cards(question_type, answer_type):
        """
        Get a set of cards that can answer the question (no null values) and don't contain duplicate answers
        """
        if question_type == 'image':
            question_type = 'email'
        if answer_type == 'image':
            answer_type = 'email'
        filter_query = Q(**{f"{question_type}__isnull": False, f"{answer_type}__isnull": False})

        # Query cards where the question/answer is not null
        # and group by answers, to prevent twice e.g. "Senior Consultant" as answer possibility.
        grouped_cards = Card.objects.filter(filter_query).values(answer_type).annotate(count=Count('name'))

        selected_cards = {}
        for group in grouped_cards:
            group_cards = Card.objects.filter(**{answer_type: group[answer_type]})

            # If there's more than one card in the group, randomly select one
            if group['count'] > 1:
                random_card = random.choice(group_cards)
                selected_cards[group[answer_type]] = random_card
            else:
                selected_cards[group[answer_type]] = group_cards.first()
        return list(selected_cards.values())

    @staticmethod
    def get_question_string(question_type, answer_type, input_value):
        """
        Translate the question/answer combination in a natural language question.
        """
        question_type = str.upper(question_type)
        answer_type = str.upper(answer_type)
        return QuizQuestionViewSet.get_question_mapping(question_type, answer_type, input_value)

    @staticmethod
    def get_question_answer_mapping(input_value=None):
        return {
            Quiz.QuizType.IMAGE: {
                Quiz.QuizType.NAME: ('Wen siehst du auf diesem Bild?', 10),
                Quiz.QuizType.JOB: ('Welche Position hat die Person im Bild?', 25),
                Quiz.QuizType.ACRONYM: ('Was ist das Kürzel dieser Person?', 15),
                Quiz.QuizType.START_AT_IPT: ('Wann hat diese Person in der ipt angefangen?', 30),
                Quiz.QuizType.WISH_DESTINATION: ('Wo wollte diese Person schon immer mal hin?', 60),
                Quiz.QuizType.WISH_PERSON: ('Mit wem wollte diese Person schon immer mal tauschen?', 60),
                Quiz.QuizType.WISH_SKILL: ('Was wollte diese Person schon immer einmal lernen?', 60),
                Quiz.QuizType.BEST_ADVICE: ('Was ist der beste berufliche Ratschlag von dieser Person?', 60)
            },
            Quiz.QuizType.NAME: {
                Quiz.QuizType.IMAGE: (f'Welches Bild zeigt {input_value}?', 10),
                Quiz.QuizType.JOB: (f'Welche Position hat {input_value} inne?', 25),
                Quiz.QuizType.START_AT_IPT: (f'Wann hat {input_value} in der ipt angefangen?', 30),
                Quiz.QuizType.WISH_DESTINATION: (f'Wo wollte {input_value} schon immer mal hin?', 60),
                Quiz.QuizType.WISH_PERSON: (f'Mit wem wollte {input_value} schon immer mal tauschen?', 60),
                Quiz.QuizType.WISH_SKILL: (f'Was wollte {input_value} schon immer einmal lernen?', 60),
                Quiz.QuizType.BEST_ADVICE: (f'Was ist der beste berufliche Ratschlag von {input_value}?', 60)
            },
            Quiz.QuizType.START_AT_IPT: {
                Quiz.QuizType.NAME: (f'Wer hatte seinen Start bei der ipt am {input_value}?', 30)
            },
            Quiz.QuizType.WISH_DESTINATION: {
                Quiz.QuizType.NAME: (f'Da würde ich am liebsten hinreisen: "{input_value}". Wer hat das gesagt?', 60)
            },
            Quiz.QuizType.WISH_PERSON: {
                Quiz.QuizType.NAME: (f'Am liebsten tauschen würde ich mit: "{input_value}". Wer hat das gesagt?', 60)
            },
            Quiz.QuizType.WISH_SKILL: {
                Quiz.QuizType.NAME: (
                    f'Das wollte ich schon immer mal erlernen: "{input_value}". Wer hat das gesagt?', 60)
            },
            Quiz.QuizType.BEST_ADVICE: {
                Quiz.QuizType.NAME: (f'Der beste Ratschlag ist: "{input_value}". Wer hat das gesagt?', 60)
            }
        }

    @staticmethod
    def get_question_mapping(question_type, answer_type, input_value=None):
        """
        Translate the question/answer combination in a natural language question and add score for answering correctly.
        https://docs.google.com/spreadsheets/d/1Xz3F_j-i1EhDGd5rSZ7dX4Ta9jcK07BufsIxtwqZevA/edit#gid=0
        """
        mapping = QuizQuestionViewSet.get_question_answer_mapping(input_value)

        try:
            result = mapping[question_type][answer_type]
        except KeyError:
            raise KeyError(f'Kombination von Frage/Antwort ist nicht erlaubt: ({question_type}/{answer_type})')

        if input_value:
            return result[0]
        else:
            return result[1]


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
        except ResourceNotFoundError:
            image_answer = 'Card Image wurde nicht gelöscht, da es im Storage Container nicht gefunden wurde.'

        return Response(
            {'status': f'User-Email: [{user_to_delete_email}]. {user_answer} {card_answer} {image_answer}'})
