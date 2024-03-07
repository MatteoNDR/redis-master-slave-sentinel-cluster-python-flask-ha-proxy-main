#Nome immagine pythonredis

FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

WORKDIR /flask-app

# # Without this setting, Python never prints anything out.
# ENV PYTHONUNBUFFERED=1

COPY requirements.txt /flask-app

COPY /flask-app /flask-app

RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

ENTRYPOINT ["python3"]

CMD ["app.py"]