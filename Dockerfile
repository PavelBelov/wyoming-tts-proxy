FROM python:3.14-slim

WORKDIR /app

COPY ./src/*.py /app
COPY requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt

EXPOSE 10200

CMD ["python", "-u", "main.py"]