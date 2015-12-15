FROM ubuntu:latest
MAINTAINER Hive Solutions

EXPOSE 9090
EXPOSE 443

VOLUME /data

ENV LEVEL INFO
ENV APP_SERVER netius
ENV APP_SERVER_ENCODING gzip
ENV APP_HOST 0.0.0.0
ENV APP_PORT 9090
ENV APP_SSL 1
ENV APP_SSL_KEY /data/pushi.key
ENV APP_SSL_CER /data/pushi.cer
ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=443
ENV SERVER_SSL 1
ENV SERVER_SSL_KEY /data/pushi.key
ENV SERVER_SSL_CER /data/pushi.cer
ENV MONGOHQ_URL mongodb://localhost:27017
ENV FILE_LOG 1

ADD requirements.txt /
ADD extra.txt /
ADD src /src

RUN apt-get update && apt-get install -y -q python python-setuptools python-dev python-pip
RUN pip install -r /requirements.txt && pip install -r /extra.txt && pip install --upgrade netius

CMD python /src/pushi/base/state.py
