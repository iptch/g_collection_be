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


class Ownership(models.Model):
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    card = models.ForeignKey(Card, on_delete=models.RESTRICT)
    otp = models.ForeignKey(Otp, on_delete=models.RESTRICT, blank=True, null=True)
