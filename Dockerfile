FROM python:3.10-alpine

RUN apk update
RUN apk add make automake gcc g++ python3-dev
RUN python -m pip install --upgrade pip

WORKDIR /app
COPY ./requirements.txt /app
RUN pip install -r requirements.txt

COPY ./app.py /app

EXPOSE 3000/tcp
CMD ["python", "./app.py"]