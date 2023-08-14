# Genius Collection 2.0 - Backend
## Local Setup
Install requirements
`pip install -r requirements.txt`

Run local server
`python manage.py runserver`

## Authentication
All Calls need a JWT Token. Get one via Curl or Postman. It is valid for 1 hour.

```
curl --request POST 'https://login.microsoftonline.com/a9080dcf-8589-4cb6-a2e2-21398dc6c671/oauth2/token' \
--header 'Content-Type: application/x-www-form-urlencoded' \\
--data-urlencode 'client_id=dd268c17-3b91-47ab-bcb4-1f87f8a0129d' \
--data-urlencode 'client_secret=XXX' \
--data-urlencode 'grant_type=client_credentials' \
--data-urlencode 'resource=api://ae04e6aa-6cb5-4c16-9d3b-45bd6a79845c'
```

Example Call with JWT
```
curl --request GET 'http://127.0.0.1:8000/cards/' \
--header 'Authorization: Bearer <<access_token from above>>'
```

## Deployment
Deployment Pipeline via GitHub Actions 
Definition in `.github/workflows/main_g-collection.yml`
Automatic Deployment when changes on main

## Azure Setup
* Subscription: iptch Sandbox
* Ressource Group: rg-genius-collection
* App Service: g-collection

### App Registrations
2 App Registrations, 1 for FE, 1 for BE [App Registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)

* Backend Registration needed for CORS from FE to BE
  * In "App Registrations" > "g-collection-be" > "Expose an API" > Add a scope
  * Add this scope to FE Application in "app.module.ts" > "protectedRessourceMap" 
* Frontend Registration is needed to initiate OAUTH Flow and obtaining the JWT Token

## DB configuration
### resetting to empty state
#### local
* delete `db.sqlite3`
* `python manage.py makemigrations`
* `python manage.py migrate`

#### remote
* delete all tables & cascade (e.g. via DBeaver)
* execute commands in app-service > SSH
* `python manage.py migrate`

### Postgres Connection
* Host: g-collection-postgres.postgres.database.azure.com
* Port: 5432
* Database: g-collection-db
* Username: gcollectionadmin
* Password: ask friend :-)

### create some dummy entries
`python manage.py shell`
```
from genius_collection.core.models import User, Card
u1 = User(name="Kevin", email="kevin.duss@ipt.ch")
u1.save()
u2 = User(name="Chris", email="christoph.weber@ipt.ch")
u2.save()

c1 = Card(name = 'Stefan Hüsemann', acronym = 'SHU', team = 'Partner', job = 'Lehrer', superpower = 'Besser mit dem Schläger', highlight = 'Andreas Offermann', must_have = 'Robit', image_link="https://ipt.ch/media/filer_public_thumbnails/filer_public/4f/5d/4f5de2b2-3029-4820-b721-92b89e836ffa/stefanhuesemann_casual.jpg__800x600_q85_crop_subsampling-2_upscale.jpg")
c1.save()
u1.cards.add(c1)
```