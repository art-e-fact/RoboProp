FROM --platform=linux/amd64 python:3.10-slim-bookworm

ENV ROBOPROP_CLIENT=/home/app/roboprop
RUN groupadd admin && useradd -m -g admin admin

RUN mkdir -p $ROBOPROP_CLIENT
RUN mkdir -p $ROBOPROP_CLIENT/static

WORKDIR $ROBOPROP_CLIENT

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install psycopg2 dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential postgresql gcc \
    && apt-get remove -y build-essential \
    && apt-get install -y --no-install-recommends linux-headers-generic g++ nodejs npm

RUN pip install --upgrade pip
COPY . $ROBOPROP_CLIENT
RUN npm install
RUN pip install -r requirements.txt
