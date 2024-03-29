# syntax=docker/dockerfile:1

FROM python:3.11

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ARG PYTHONUNBUFFERED=1
ENV DOCKERIZED=1

EXPOSE 5000
CMD [ "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000" ]