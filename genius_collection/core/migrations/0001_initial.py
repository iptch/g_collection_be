# Generated by Django 4.2.3 on 2023-10-28 14:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Card',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('acronym', models.CharField(max_length=3)),
                ('job', models.CharField(max_length=200)),
                ('start_at_ipt', models.DateField()),
                ('wish_destination', models.CharField(max_length=200)),
                ('wish_person', models.CharField(max_length=200)),
                ('wish_skill', models.CharField(max_length=200)),
                ('best_advice', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Ownership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('otp_value', models.CharField(max_length=16, null=True)),
                ('otp_valid_to', models.DateTimeField(null=True)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('last_received', models.DateTimeField(auto_now_add=True)),
                ('card', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='core.card')),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.CharField(max_length=200)),
                ('first_name', models.CharField(max_length=200)),
                ('last_name', models.CharField(max_length=200)),
                ('is_admin', models.BooleanField(default=False)),
                ('last_login', models.DateTimeField(auto_now=True)),
                ('cards', models.ManyToManyField(through='core.Ownership', to='core.card')),
            ],
        ),
        migrations.AddField(
            model_name='ownership',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='core.user'),
        ),
    ]
