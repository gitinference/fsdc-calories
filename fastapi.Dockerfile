# syntax=docker/dockerfile:1

FROM python

WORKDIR .

COPY requirements.txt requirements.txt

RUN ["pip", "install", "-r", "requirements.txt"]

COPY . .

EXPOSE 80

CMD ["fastapi", "dev", "main.py"]