FROM python:3.9.7-buster

# Clone repository + work directory
RUN git clone https://github.com/confusedkarma/ctrl.git /root/tg_bot
WORKDIR /root/tg_bot

COPY . .

RUN pip install -r requirements.txt

CMD ["python3","-m","tg_bot"]
