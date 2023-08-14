# g_collection_be

python manage.py makemigrations
python manage.py migrate

from genius_collection.core.models import User, Card
u1 = User(name="Kevin", email="kevin.duss@ipt.ch")
u1.save()
u2 = User(name="Chris", email="christoph.weber@ipt.ch")
u2.save()

c1 = Card(name = 'Stefan Hüsemann', acronym = 'SHU', team = 'Partner', job = 'Lehrer', superpower = 'Besser mit dem Schläger', highlight = 'Andreas Offermann', must_have = 'Robit', image_link="https://ipt.ch/media/filer_public_thumbnails/filer_public/4f/5d/4f5de2b2-3029-4820-b721-92b89e836ffa/stefanhuesemann_casual.jpg__800x600_q85_crop_subsampling-2_upscale.jpg")
c1.save()
u1.cards.add(c1)
