# Building
FROM --platform=linux/amd64 python:3.10-slim-bookworm as builder

ENV ROBOPROP_CLIENT=/home/app/roboprop
RUN groupadd admin && useradd -m -g admin admin

RUN mkdir -p $ROBOPROP_CLIENT
RUN mkdir -p $ROBOPROP_CLIENT/static

WORKDIR $ROBOPROP_CLIENT

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_ALLOWED_HOSTS *

RUN pip install --upgrade pip virtualenv
RUN virtualenv /venv

COPY requirements.txt .
RUN /venv/bin/pip install -r requirements.txt

COPY . $ROBOPROP_CLIENT
RUN apt-get update && apt-get install nodejs npm -y
RUN npm install && npx tailwindcss -i $ROBOPROP_CLIENT/static/src/input.css -o $ROBOPROP_CLIENT/static/src/output.css
RUN rm -rf node_modules
# Final
FROM --platform=linux/amd64 python:3.10-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    linux-headers-generic g++ \
    libx11-dev libxxf86vm-dev libxcursor-dev \
    libxi-dev libxrandr-dev libxinerama-dev \
    libglew-dev libxkbcommon-dev libsm6 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /venv /venv
COPY --from=builder /home/app/roboprop /home/app/roboprop

WORKDIR /home/app/roboprop

ENV PATH="/venv/bin:$PATH"

RUN python manage.py makemigrations && \
    python manage.py migrate && \
    python manage.py collectstatic --noinput

EXPOSE 8000
CMD [ "gunicorn", "roboprop.wsgi:application", "--bind", "0.0.0.0:8000" ]