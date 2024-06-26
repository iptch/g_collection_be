import random
from django.db import models
from django.utils import timezone


class Card(models.Model):
    def __str__(self):
        return self.name

    name = models.CharField(max_length=200)
    acronym = models.CharField(max_length=3)
    job = models.CharField(max_length=200)
    start_at_ipt = models.DateField()
    email = models.CharField(max_length=200)
    wish_destination = models.CharField(max_length=2000, null=True)
    wish_person = models.CharField(max_length=2000, null=True)
    wish_skill = models.CharField(max_length=2000, null=True)
    best_advice = models.CharField(max_length=2000, null=True)


class UserManager(models.Manager):
    # Use the manager instead of overriding the __init__ method. See:
    # https://docs.djangoproject.com/en/4.2/ref/models/instances/
    def create_user(self, first_name, last_name, email, init_cards=10, init_self=20):
        user = self.create(first_name=first_name, last_name=last_name, email=email)
        Ownership.objects.distribute_random_cards(user, init_cards)
        try:
            Ownership.objects.distribute_self_cards_to_user(user, init_self)
            return user, True
        except Card.DoesNotExist:
            return user, False


class User(models.Model):
    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    email = models.CharField(max_length=200)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    cards = models.ManyToManyField(Card, through='Ownership')
    is_admin = models.BooleanField(default=False)
    last_login = models.DateTimeField(auto_now=True)
    last_received_unique = models.DateTimeField(null=True)
    quiz_score = models.IntegerField(default=0)
    objects = UserManager()


class OwnershipManager(models.Manager):

    def add_card_to_user(self, user, card, qty=1):
        """
        Increase the quantity of the owned card of a user or add it as a new ownership.
        """
        # Check if the user already owns the card
        ownership, created = self.get_or_create(user=user, card=card)

        if created:
            ownership.quantity = qty
            user.last_received_unique = timezone.now()
            user.save()
        else:
            ownership.quantity += qty
            ownership.last_received = timezone.now()
        ownership.save()

        return ownership

    def remove_card_from_user(self, user, card):
        """
        Decrease the owned quantity by 1. Deletes the ownership if qty == 0
        """
        ownership = self.get(user=user, card=card)
        if ownership.quantity > 1:
            ownership.quantity -= 1
            ownership.save()
            return ownership
        else:
            ownership.delete()
            return None

    def distribute_random_cards(self, user, qty):
        """
        Gives the user [qty] new cards. Duplicates possible.
        """
        cards = Card.objects.all()
        num_cards = len(cards)
        if num_cards == 0:
            return
        card_indices = random.choices(range(num_cards), k=qty)

        for idx in card_indices:
            self.add_card_to_user(user=user, card=Card.objects.all()[idx])

    def distribute_self_cards_to_user(self, user, qty):
        """
        Gives the user [qty] new cards of himself.
        """
        card = Card.objects.get(email=user.email)
        self.add_card_to_user(user=user, card=card, qty=qty)

    def transfer_ownership(self, to_user, giver_ownership, card):
        """
        Remove 1 card from giver and give it to receiver.
        """
        from_user = giver_ownership.user

        receiver_ownership = self.add_card_to_user(user=to_user, card=card)
        giver_ownership.otp_valid_to = None
        giver_ownership.otp_value = None
        giver_ownership.save()
        giver_ownership = self.remove_card_from_user(user=from_user, card=card)

        return giver_ownership, receiver_ownership


class Ownership(models.Model):
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    card = models.ForeignKey(Card, on_delete=models.RESTRICT)
    otp_value = models.CharField(null=True, max_length=16)
    otp_valid_to = models.DateTimeField(null=True)
    quantity = models.PositiveIntegerField(default=1)
    last_received = models.DateTimeField(auto_now_add=True)
    objects = OwnershipManager()

    def __str__(self):
        return f'{self.user} besitzt {self.quantity} {self.card}'


class Distribution(models.Model):
    def __str__(self):
        return f'qty: {self.quantity} triggered_by: {self.user} timestamp: {self.timestamp}'

    quantity = models.PositiveIntegerField(default=1)
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    timestamp = models.DateTimeField(auto_now_add=True)
    receiver = models.CharField(max_length=200, null=True)


class Quiz(models.Model):
    class QuizType(models.TextChoices):
        IMAGE = 'IMAGE'
        NAME = 'NAME'
        JOB = 'JOB'
        ACRONYM = 'ACRONYM'
        START_AT_IPT = 'START_AT_IPT'
        WISH_DESTINATION = 'WISH_DESTINATION'
        WISH_PERSON = 'WISH_PERSON'
        WISH_SKILL = 'WISH_SKILL'
        BEST_ADVICE = 'BEST_ADVICE'

    id = models.AutoField(primary_key=True)
    question_timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    question_type = models.CharField(max_length=16, choices=QuizType.choices, default=QuizType.IMAGE)
    answer_type = models.CharField(max_length=16, choices=QuizType.choices, default=QuizType.NAME)
    question_true_card = models.ForeignKey(Card, on_delete=models.RESTRICT, related_name='true_card')
    answer_timestamp = models.DateTimeField(null=True)
    answer_options = models.IntegerField(null=True)
    answer_correct = models.BooleanField(null=True)