# Generated by Django 4.2.3 on 2024-03-29 11:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_remove_quiz_question_answer_card_quiz_answer_correct_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='quiz_score',
            field=models.IntegerField(default=0),
        ),
    ]
