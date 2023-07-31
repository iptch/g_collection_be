from django.db import models


class Card(models.Model):
    def __str__(self):
        return self.name

    name = models.CharField(max_length=200)
    value = models.IntegerField(default=0)


class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")

    def __str__(self):
        return self.question_text
