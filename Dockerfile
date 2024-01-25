FROM --platform=linux/amd64 python:3.10-slim-bookworm

ENV ROBOPROP_CLIENT=/home/app/roboprop
RUN groupadd admin && useradd -m -g admin admin
# set work directory

RUN mkdir -p $ROBOPROP_CLIENT
RUN mkdir -p $ROBOPROP_CLIENT/static

# where the code lives
WORKDIR $ROBOPROP_CLIENT

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential postgresql gcc \
    && apt-get remove -y build-essential \
    && apt-get install -y --no-install-recommends linux-headers-generic g++ nodejs npm

# install depenencies
RUN pip install --upgrade pip
# copy project
COPY . $ROBOPROP_CLIENT
RUN npm install
RUN pip install -r requirements.txt
