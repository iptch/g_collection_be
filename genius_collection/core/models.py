import random
from django.db import models


class Card(models.Model):
    def __str__(self):
        return self.name

    name = models.CharField(max_length=200)
    acronym = models.CharField(max_length=3)
    team = models.CharField(max_length=200)
    job = models.CharField(max_length=200)
    superpower = models.CharField(max_length=200)
    highlight = models.CharField(max_length=200)
    must_have = models.CharField(max_length=200)
    image_link = models.CharField(max_length=200)


class User(models.Model):
    def __str__(self):
        return self.name

    email = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    cards = models.ManyToManyField(Card, through='Ownership')
    is_admin = models.BooleanField(default=False)


class OwnershipManager(models.Manager):
    def add_card_to_user(self, user, card):
        # Check if the user already owns the card
        ownership, created = self.get_or_create(user=user, card=card)

        # If the ownership already exists, increase the quantity by 1
        if not created:
            ownership.quantity += 1
            ownership.save()

        return ownership

    def remove_card_from_user(self, user, card):
        ownership = self.get(user=user, card=card)
        if ownership.quantity > 1:
            ownership.quantity -= 1
            ownership.save()
            return ownership
        else:
            ownership.delete()
            return None

    def assign_ownership(self, user, num_samples):
        cards = Card.objects.all()
        num_cards = len(cards)
        if num_cards == 0:
            return
        card_indices = random.choices(range(num_cards), k=num_samples)

        for idx in card_indices:
            self.add_card_to_user(user=user, card=Card.objects.all()[idx])


class Ownership(models.Model):
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    card = models.ForeignKey(Card, on_delete=models.RESTRICT)
    otp_value = models.CharField(null=True, max_length=16)
    otp_valid_to = models.DateTimeField(null=True)
    quantity = models.PositiveIntegerField(default=1)
    last_received = models.DateTimeField(auto_now=True)
    objects = OwnershipManager()

    def __str__(self):
        return f'{self.user.__str__()} owns {self.quantity} of {self.card.__str__()}'
