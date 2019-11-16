#!/bin/bash

PYTHON_VERSION="${1}"
if [ -z "${PYTHON_VERSION}" ]
then
  PYTHON_VERSION="3.6"
fi

LINK_MODULES=(
  future
  certifi
  asn1crypto
  pycparser
  cffi
  cryptography
  urllib3
  tornado
  telegram
)

rm -rf ./.env

if [[ ${PYTHON_VERSION} == 2.* ]]
then
  virtualenv .env
else
  python${PYTHON_VERSION} -m venv .env
fi

.env/bin/pip install -U pip
.env/bin/pip install -U python-telegram-bot

for i in ${LINK_MODULES[@]}
do
  ln -s .env/lib/python${PYTHON_VERSION}/site-packages/${i} .
done

.env/bin/python setup.py clean --all
.env/bin/python setup.py bdist_egg

for i in ${LINK_MODULES[@]}
do
  rm -rf ./${i}
done
