FROM tensorflow/tensorflow:latest-gpu

RUN apt-get update && apt-get install --no-install-recommends --yes \
    build-essential \
    git \
    libprotobuf-dev \
    protobuf-compiler \
    wget \
    && rm -Rf /var/lib/apt/lists/*

# download and install latest CMake
RUN cd /tmp && wget -q "$(curl -s https://api.github.com/repos/Kitware/CMake/releases/latest | grep browser_download_url | grep Linux-x86_64.tar.gz | cut -d : -f 2,3 | tr -d \" | xargs)" && tar --extract --keep-old-files --directory /usr --strip-components=1 --file cmake-*-Linux-x86_64.tar.gz

RUN git clone https://github.com/boostorg/boost.git \
    && cd boost \
    && git checkout $(git describe --tags $(git rev-list --tags --max-count=1)) \
    && git submodule update --init \
    && ./bootstrap.sh --prefix=/usr \
    && ./b2 install

RUN pip install git+https://github.com/h3ndrk/PyCompiledNN.git

COPY genetic_individual_neuralnet/ /genetic_individual_neuralnet/
COPY worker/ /worker/
RUN pip install /genetic_individual_neuralnet/ /worker/
