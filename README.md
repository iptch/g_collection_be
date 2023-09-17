# Genius Collection 2.0 - Backend
Endpoint: https://g-collection.scm.azurewebsites.net/ 

## Overview
This backend works with Django and Django Rest Framework. Data is stored in SQLite (local) or Postgres (remote) Database. The application is hosted on Azure. The authentication works via Azure OAuth which federates the requests to Google Cloud.

First time working with some of the tools mentioned above? Have a look at these links:
* [Django Quickstart](https://www.django-rest-framework.org/tutorial/quickstart/)
* [Django REST Framework Quickstart](https://www.django-rest-framework.org/#quickstart)

## Local Setup
### Prerequisites
Required:
[Python >= 3.10](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)

Recommended:
DB Viewer, e.g. [DBeaver](https://dbeaver.io/)

### Run configuration
Either use the devcontainer in `.devcontainer` with VS Code or execute the following steps:
* Install requirements `pip install -r requirements.txt`
* Login with Azure CLI using your ipt address (to access blob storage) `az login`
* Run local server `python manage.py runserver`

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
Based on this [tutorial](https://learn.microsoft.com/en-us/azure/app-service/tutorial-python-postgresql-app?tabs=flask%2Cwindows&pivots=deploy-portal)


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

### Remote Debugging
* In Azure Portal, navigate to the "App Service" > "SSH"
* execute `python manage.py shell`
* This opens a Python Shell in the configured Djange setup where you can execute commands
  * e.g. `os.environ['DJANGO_SETTINGS_MODULE']`


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

FYI: The App Service connects via "Service Connector" to the Postgres Instance.

### Creating Dummy Entries
There is a helper script in `genius_collection/core/management/commands/create_dummy_data.py` that creates some
* Users
* Cards
* Gives the users some cards

You can execute it with:
`python manage.py create_dummy_data`

If you want to get a clean database (without deleting the tables), execute:
`python manage.py flush`