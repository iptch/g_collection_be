# Generated by Django 4.2.3 on 2024-03-26 08:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alter_quiz_question_answer_card'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quiz',
            name='answer_type',
            field=models.CharField(choices=[('IMAGE', 'Image'), ('NAME', 'Name'), ('JOB', 'Job'), ('ACRONYM', 'Acronym'), ('START_AT_IPT', 'Start At Ipt'), ('WISH_DESTINATION', 'Wish Destination'), ('WISH_PERSON', 'Wish Person'), ('WISH_SKILL', 'Wish Skill'), ('BEST_ADVICE', 'Best Advice')], default='NAME', max_length=16),
        ),
        migrations.AlterField(
            model_name='quiz',
            name='question_type',
            field=models.CharField(choices=[('IMAGE', 'Image'), ('NAME', 'Name'), ('JOB', 'Job'), ('ACRONYM', 'Acronym'), ('START_AT_IPT', 'Start At Ipt'), ('WISH_DESTINATION', 'Wish Destination'), ('WISH_PERSON', 'Wish Person'), ('WISH_SKILL', 'Wish Skill'), ('BEST_ADVICE', 'Best Advice')], default='IMAGE', max_length=16),
        ),
    ]
