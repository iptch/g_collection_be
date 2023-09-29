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


class Otp(models.Model):
    def __str__(self):
        return self.otp

    otp = models.CharField(max_length=200)
    valid_to = models.DateTimeField()


class OwnershipManager(models.Manager):
    def add_card_to_user(self, user, card):
        # Check if the user already owns the card
        ownership, created = self.get_or_create(user=user, card=card)

        # If the ownership already exists, increase the quantity by 1
        if not created:
            ownership.quantity += 1
            ownership.save()

        return ownership


class Ownership(models.Model):
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    card = models.ForeignKey(Card, on_delete=models.RESTRICT)
    otp = models.ForeignKey(Otp, on_delete=models.RESTRICT, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)

    objects = OwnershipManager()

    def __str__(self):
        return f'{self.user.__str__()} owns {self.quantity} of {self.card.__str__()}'

    def assign_ownership(self, user, num_samples, num_duplicates=0):
        num_cards = Card.objects.count()
        if num_cards == 0:
            return
        card_indices = random.choices(range(num_cards), num_samples)
        for idx in card_indices:
            self.objects.add_card_to_user(user=user, card=self.test_cards[idx])