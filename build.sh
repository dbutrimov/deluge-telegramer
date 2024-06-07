#!/usr/bin/env bash
set -e

OUTPUT_DIR=$(pwd)/build
rm -rf ${OUTPUT_DIR}
mkdir -p ${OUTPUT_DIR}

PYTHON_VERSIONS=("3.9" "3.10" "3.11" "3.12")
for PYTHON_VERSION in ${PYTHON_VERSIONS[@]}; do
  IMAGE_NAME=telegramer.build:py${PYTHON_VERSION}

  docker build \
    --build-arg PYTHON_VERSION=${PYTHON_VERSION} \
    -t ${IMAGE_NAME} .

  docker run -v ${OUTPUT_DIR}:/tmp/out --rm -i ${IMAGE_NAME} bash build_egg.sh

done
