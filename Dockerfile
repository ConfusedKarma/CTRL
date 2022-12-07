FROM python:3.11.1-buster

WORKDIR /root/tg_bot

COPY . .

RUN pip install -r requirements.txt

CMD ["python3","-m","tg_bot"]
