# Genius Collection 2.0 - Backend
## Endpoints

Root: 
* Remote: https://g-collection.scm.azurewebsites.net/
* Local: http://127.0.0.1:8000/

Swagger: http://localhost:8000/swagger/

## Overview
This backend works with Django and Django Rest Framework. Data is stored in SQLite (local) or Postgres (remote) Database. The application is hosted on Azure. The authentication works via Azure OAuth which federates the requests to Google Cloud.

First time working with some of the tools mentioned above? Have a look at these links:
* [Django Quickstart](https://www.django-rest-framework.org/tutorial/quickstart/)
* [Django REST Framework Quickstart](https://www.django-rest-framework.org/#quickstart)

## Running the app in a Dev Container

1. Install and run [Docker](https://www.docker.com/products/docker-desktop/).
2. Open this project in [VS Code](https://code.visualstudio.com/).
3. Install the VS Code extension _Dev Containers_ (`Cmd+Shift+X` or `Ctrl+Shift+X`).
4. Run _Dev Containers: Rebuild Container_ (`Cmd+Shift+P` or `Ctrl+Shift+P`).
5. Run `export SECRET_KEY=...` to set the Azure secret key as environment variable.
6. Add yourself to the Azure Subscription _iptch Sandbox_ (find instructions [here](https://app.happeo.com/pages/1e1oopl952ukqf9e0h/AzureampDu/1e5g766dso0ms8i9mp#wie-darf-ich-subscription-iptch-sandbox-nutzen)).
7. Run `az login` to log into Azure using your ipt address (to access blob storage). If it doesn't work, try `az login --tenant iptzug.onmicrosoft.com`.
8. Run `python manage.py migrate` to prepare the local DB.
9. Run `python manage.py runserver` to start up the app.
10. Code away!

## Local Setup
### Prerequisites
Required:
[Python >= 3.10](https://www.python.org/downloads/), [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)

Recommended:
DB Viewer, e.g. [DBeaver](https://dbeaver.io/)

### Run configuration
Either use the devcontainer in `.devcontainer` with VS Code (described above) or execute the following steps:
* Install requirements `pip install -r requirements.txt`
* Login with Azure CLI using your ipt address (to access blob storage) `az login`
* Run local server `python manage.py runserver`

## Authentication
All Calls need a JWT Token. Get one from the published app.
1. In Chrome via Developer Tools
2. Network
3. Open the *cards* overview
4. Copy the *Authorization:* part from Request Header of `cards` (not `cards/`)

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
Ensure the Firewall allows connection from your IP:

Ressource Group: *rg-genius-collection* > Database: *g-collection-postgres* > Settings > Networking

Then connect via a DB Viewer:

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

For privacy reasons, this files is not versioned by git (this repo is public). Please download it from GDrive [here](https://drive.google.com/file/d/1z2skId5GmNs4oqamrTOKokGPYvYUaDms/view?usp=drive_link)

You can then execute it with:
`python manage.py create_dummy_data`

If you want to get a clean database (without deleting the tables), execute:
`python manage.py flush`