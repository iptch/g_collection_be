from django.db import models


class Card(models.Model):
    def __str__(self):
        return self.name

    name = models.CharField(max_length=200)
    value = models.IntegerField(default=0)
