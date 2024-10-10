# syntax=docker/dockerfile:1

FROM python

COPY jp-imports /usr/src/jp-imports

COPY . /usr/src/app

WORKDIR /usr/src/app

RUN ["pip", "install", "-r", "requirements.txt"]

EXPOSE 80

CMD ["python3", "main.py"]