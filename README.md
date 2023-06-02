# RoboProp

## Installation and Use

### Creating Your File Server

At present, We will use the OSS version of [DreamFactory](https://github.com/dreamfactorysoftware/dreamfactory) as the API to serve our models. DreamFactory has a local storage API out of the box, and so by having an instance running on, e.g. EC2 or DigitalOcean, (or just your computer) we will have full access to our models / files via a RESTful API.

Easiest way to install is through the [Docker Repo](https://github.com/dreamfactorysoftware/df-docker)

### Installing and Using the Client

The Clientside program is this repo, which is a Django Project (`roboprop`) and Django app (`roboprop_client`). To install:

```
git clone git@github.com:art-e-fact/RoboProp.git
cd RoboProp
pip install -r requirements.txt
python manage.py runserver
```
