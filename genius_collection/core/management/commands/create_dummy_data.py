from django.core.management.base import BaseCommand
from genius_collection.core.models import User, Card, Ownership
import random


class Command(BaseCommand):
    help = 'Populating the database with users and cards'

    def _create(self):
        print('=== START CREATING DUMMY DATA ===')
        test_users = [User(name='Kevin Duss', email='kevin.duss@ipt.ch'),
                      User(name='Christoph Weber', email='christoph.weber@ipt.ch'),
                      User(name='Dominik Bruggisser', email='dominik.bruggisser@ipt.ch'),
                      User(name='Dominique Heyn', email='dominique.heyn@ipt.ch'),
                      User(name='Jennifer Studer', email='jennifer.studer@ipt.ch'),
                      User(name='Larissa Zollinger', email='larissa.zollinger@ipt.ch'),
                      User(name='Luka Jovanovic', email='luka.jovanic@ipt.ch'),
                      User(name='Manuel Kuchelmeister', email='manuel.kuchelmeister@ipt.ch'),
                      User(name='Manuel Szecsenyi', email='manuel.szecseny@ipt.ch'),
                      User(name='Mathias Dedial', email='mathias.dedial@ipt.ch'),
                      User(name='Monika Spisak', email='monika.spisak@ipt.ch'),
                      User(name='Nicolas Mesot', email='nicolas.mesot@ipt.ch'),
                      User(name='Patrick Plattner', email='patrick.plattner@ipt.ch'),
                      User(name='Philipp Meier', email='philipp.meier@ipt.ch'),
                      User(name='Selim Kälin', email='selim.kaelin@ipt.ch'),
                      User(name='Stefan Hüsemann', email='stefan.huesemann@ipt.ch'),
                      User(name='Stephan Zehnder', email='stephan.zehnder@ipt.ch'),
                      User(name='Thomas Zimmermann', email='thomas.zimmermann@ipt.ch'),
                      User(name='Vele Ristovski', email='vele.ristovski@ipt.ch')]

        test_cards = [
            Card(name='Markus Ingold', team='Consultant', acronym='MIN', job='Lehrer',
                 superpower='Zuhören und für das Gegenüber interessieren', highlight='Zusammenhalt',
                 must_have='soziales Umfeld', image_link='min.jpg'),
            Card(name='Lukas Eisenring', team='Consultant', acronym='LEI', job='Feuerwehrmann',
                 superpower='Kombination von Technologien', highlight='Tolle Arbeitskollegen',
                 must_have='Bewegung in der Natur', image_link='lei.jpg'),
            Card(name='Nicolas Mesot', team='Consultant', acronym='NME', job='Hacker',
                 superpower='Empathie', highlight='Zusammenarbeit, Leute, Projekte',
                 must_have='Mein Notebook', image_link='nme.jpg'),
            Card(name='Simal Papadopoulos', team='P&D', acronym='SPA', job='Kindergärtnerin',
                 superpower='Positivity', highlight='Unser Speed & die coolen Leute',
                 must_have='Kätzchen', image_link='spa.jpg'),
            Card(name='Manuela Züger', team='Consultant', acronym='MZU', job='Lehrerin',
                 superpower='Positives Denken', highlight='Die coole Crew 🤩',
                 must_have='Kafi und Schoggi', image_link='mzu.jpg'),
            Card(name='Yves Brise', team='Partnerschaft', acronym='YBR', job='Tierarzt',
                 superpower='Vorbilder kopieren', highlight='Gestaltungsfreiraum',
                 must_have='Chillis', image_link='ybr.jpg'),
            Card(name='Stefan Hüsemann', team='Partnerschaft', acronym='SHU', job='Müllmann (orange!) später Gärtner',
                 superpower='Ski in allen Lagen', highlight='Tolle Kollegen, hohe Innovationskraft',
                 must_have='Schnee', image_link='shu.jpg'),
        ]

        for test_card in test_cards:
            test_card.save()
        for test_user in test_users:
            test_user.save()
            is_first = True
            # Give every user 2 to 5 different cards. The first one is always a double
            for card_index in random.sample(range(len(test_cards)), random.randint(2, 5)):
                Ownership.objects.add_card_to_user(user=test_user, card=test_cards[card_index])
                if is_first:
                    Ownership.objects.add_card_to_user(user=test_user, card=test_cards[card_index])
                    is_first = False
        print('=== FINISHED CREATING DUMMY DATA ===')

    def handle(self, *args, **options):
        self._create()
