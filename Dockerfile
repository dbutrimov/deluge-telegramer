ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-alpine AS base

RUN mkdir -p /usr/src/app
RUN mkdir -p /output
WORKDIR /usr/src/app

COPY telegramer ./telegramer
COPY setup.py ./setup.py
COPY requirements.txt ./requirements.txt
COPY LICENSE ./LICENSE
COPY build_egg.sh ./build_egg.sh

RUN \
  echo "**** install build packages ****" && \
  apk add --no-cache --upgrade \
    bash && \
  apk add --no-cache --upgrade --virtual=build-dependencies \
    py3-pip && \
  echo "**** install packages ****" && \
  apk add --no-cache --upgrade \
    py3-urllib3 && \
  echo "**** install python modules ****" && \
  pip3 install -U --no-cache-dir pip && \
  pip3 install -U --no-cache-dir -r requirements.txt && \
  echo "**** cleanup ****" && \
  apk del --purge \
    build-dependencies && \
  rm -rf \
    $HOME/.cache \
    /tmp/*
