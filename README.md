# RoboProp

## Installation and Use

### Creating Your File Server

At present, We will use the OSS version of [DreamFactory](https://github.com/dreamfactorysoftware/dreamfactory) as the API to serve our models. DreamFactory has a local storage API out of the box, and so by having an instance running on, e.g. EC2 or DigitalOcean, (or just your computer) we will have full access to our models / files via a RESTful API.

Easiest way to install is through the [Docker Repo](https://github.com/dreamfactorysoftware/df-docker)

Once spun-up, got to localhost in the browser make your first user (this will be the superuser). You can upload files using the files tab if you want to play around here.

You will want to make a role (RBAC) for the Files service, and then an app (i.e API Key) to give to the client. (At present we will not do user based role access for simplicity, but you should if it is available publicly).

To make a role, click on the roles tab, then create, make a name, description, click "active" and click next. On this tab add the "files" service, all components (*), All access (5 selected), and check both boxes for Requester (API and Script), then save.

To make an app, click apps, create, then makes an application name, description, and for "Assign a Default Role", choose the role you just made. Make it Active, click save, and copy the API key generated to your clipboard.

### Installing and Using the Client

The Clientside program is this repo, which is a Django Project (`roboprop`) and Django app (`roboprop_client`). To install:

```
git clone git@github.com:art-e-fact/RoboProp.git
cd RoboProp
pip install -r requirements.txt
```

You will then want to rename `example.env` to `.env` and add the location of your fileserver (if local development it will be `http://localhost/api/v2/files`) and the api key you generated above.

Start a dev server with `python manage.py runserver` and go to localhost:8000 in the browser

### Development

* Styling: Bootstrap 5