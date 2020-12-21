#!/bin/bash

set -e -x

# change to this directory
cd "$(dirname "$0")"

# build neural network individual worker
docker build -t hulks-genetic-individual-neuralnet -f ./Dockerfile ../
