#!/bin/bash
set -e

DEPENDENCIES=(
  urllib3
  tzlocal
  apscheduler
  cachetools
  certifi
  pytz
  tornado
  telegram
)

for DEPENDENCY in ${DEPENDENCIES[@]}; do
  DEPENDENCY_PATH=`python -c "import ${DEPENDENCY} as _; print(_.__path__[0])"`
  ln -s "${DEPENDENCY_PATH}" .
done

python setup.py bdist_egg

for DEPENDENCY in ${DEPENDENCIES[@]}; do
  rm -rf ./${DEPENDENCY}
done

chown -R $(id -u):$(id -g) dist
cp -ar dist/*.egg /tmp/out/
