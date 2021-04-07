FROM tensorflow/tensorflow:latest-gpu AS build-predicter

RUN apt-get update && apt-get install --no-install-recommends --yes \
    build-essential \
    cmake \
    git \
    ninja-build \
    && rm -Rf /var/lib/apt/lists/*

COPY vcpkg-ports/ /vcpkg-ports/
RUN git clone -b "2020.06" https://github.com/microsoft/vcpkg.git && \
    cd vcpkg && \
    ./bootstrap-vcpkg.sh -disableMetrics && \
    ./vcpkg install --recurse --overlay-ports="/vcpkg-ports" compilednn nlohmann-json protobuf cxxopts

COPY predicter/ /predicter/
COPY build-predicter.sh /
RUN sed -i 's|cmake |../../vcpkg/downloads/tools/cmake-3.17.2-linux/cmake-3.17.2-Linux-x86_64/bin/cmake |' build-predicter.sh && \
    ./build-predicter.sh

FROM tensorflow/tensorflow:latest-gpu

COPY --from=build-predicter /predicter/build/predicter /predicter

COPY generic/distributed_task_execution_framework/worker/genetic_individual_neuralnet/ /genetic_individual_neuralnet/
COPY generic/distributed_task_execution_framework/worker/worker/ /worker/
RUN sed -i 's|tensorflow|tensorflow-gpu|' /genetic_individual_neuralnet/setup.py && \
    pip install /genetic_individual_neuralnet/ /worker/
