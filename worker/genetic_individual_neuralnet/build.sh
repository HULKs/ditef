#!/bin/bash

set -e -x

# change to this directory
cd "$(dirname "$0")"

# build neural network individual worker
#  -f generic/distributed_task_execution_framework/worker/genetic_individual_neuralnet/Dockerfile
docker build -t hulks-genetic-individual-neuralnet -f ./Dockerfile ../../../../
