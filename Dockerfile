FROM nvidia/cuda:12.4.0-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
software-properties-common build-essential wget curl git ca-certificates && \
add-apt-repository ppa:deadsnakes/ppa && apt-get update && \
apt-get install -y --no-install-recommends python3.11 python3.11-dev python3.11-distutils && \
apt-get clean && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.11
RUN wget https://bootstrap.pypa.io/get-pip.py && python3.11 get-pip.py && rm get-pip.py

# Install PyTorch, Torchvision, Torchaudio with CUDA 12.4 support
RUN python3.11 -m pip install \
    torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 \
    --index-url https://download.pytorch.org/whl/cu124

RUN mkdir /workspace
WORKDIR /workspace

RUN git clone --recursive https://github.com/ZiYang-xie/WorldGen.git --depth 1 && \
    cd WorldGen && \
    python3.11 -m pip install . && \
    python3.11 -m pip install git+https://github.com/facebookresearch/pytorch3d.git --no-build-isolation

ENV HF_HOME = "/runpod-volume/huggingface/data_Cache"
ENV HF_HUB_CACHE = "/runpod-volume/huggingface/model_Cache"
ENV TMPDIR = "/runpod-volume/tmp"

RUN mkdir /runpod-volume/huggingface/data_Cache \
    /runpod-volume/hugginface/model_Cache

VOLUME [ "/runpod-volume" ]

CMD ["sleep", "infinity"]