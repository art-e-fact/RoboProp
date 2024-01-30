FROM --platform=linux/amd64 python:3.10-slim-bookworm

ENV ROBOPROP_CLIENT=/home/app/roboprop
RUN groupadd admin && useradd -m -g admin admin

RUN mkdir -p $ROBOPROP_CLIENT
RUN mkdir -p $ROBOPROP_CLIENT/static

WORKDIR $ROBOPROP_CLIENT

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_ALLOWED_HOSTS *

# Install psycopg2 dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential postgresql gcc \
    && apt-get remove -y build-essential \
    && apt-get install -y --no-install-recommends linux-headers-generic g++ nodejs npm

RUN pip install --upgrade pip
COPY . $ROBOPROP_CLIENT
RUN npm install
RUN pip install -r requirements.txt

RUN python manage.py makemigrations && \
    python manage.py migrate && \
    npx tailwindcss -i static/src/input.css -o static/src/output.css

EXPOSE 8000
CMD [ "gunicorn", "roboprop.wsgi:application", "--bind", "0.0.0.0:8000" ]