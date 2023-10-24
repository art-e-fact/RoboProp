FROM python:3.9.13-alpine

ENV ROBOPROP_CLIENT=/home/app/roboprop
RUN addgroup -S admin && adduser -S admin -G admin
# set work directory


RUN mkdir -p $ROBOPROP_CLIENT
RUN mkdir -p $ROBOPROP_CLIENT/static

# where the code lives
WORKDIR $ROBOPROP_CLIENT

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies
RUN apk update \
    && apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add postgresql-dev gcc python3-dev musl-dev \
    && apk del build-deps \
    && apk --no-cache add musl-dev linux-headers g++

RUN apk add --update nodejs npm
# install dependencies
RUN pip install --upgrade pip
# copy project
COPY . $ROBOPROP_CLIENT
RUN npm install
RUN pip install -r requirements.txt