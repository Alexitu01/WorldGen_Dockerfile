FROM nvidia/cuda:12.4.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN echo "Acquire::http::Pipeline-Depth 0;" > /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::BrokenProxy    true;" >> /etc/apt/apt.conf.d/99custom

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
software-properties-common build-essential wget curl git ca-certificates && \
add-apt-repository ppa:deadsnakes/ppa && apt-get update && \
apt-get install -y --no-install-recommends python3.11 python3.11-dev python3.11-venv && \
apt-get clean && rm -rf /var/lib/apt/lists/*

# Use an isolated environment to avoid conflicts with apt-installed Python packages.
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install PyTorch, Torchvision, Torchaudio with CUDA 12.4 support
RUN pip install \
    torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 \
    --index-url https://download.pytorch.org/whl/cu124

RUN mkdir /workspace && pip install --no-cache-dir runpod
WORKDIR /workspace

COPY startup.py .

RUN git clone https://github.com/ZiYang-xie/WorldGen.git --depth 1 && \
    cd WorldGen && \
    git submodule update --init --recursive --depth 1 -- \
    submodules/UniK3D submodules/viser && \
    pip install . && \
    pip install git+https://github.com/facebookresearch/pytorch3d.git --no-build-isolation

ENV HF_HOME="/runpod-volume/huggingface/data_Cache"
ENV HF_HUB_CACHE="/runpod-volume/huggingface/model_Cache"
ENV TMPDIR="/runpod-volume/tmp"

RUN mkdir -p /runpod-volume/huggingface/data_Cache \
    /runpod-volume/huggingface/model_Cache

VOLUME [ "/runpod-volume" ]

CMD ["python3.11", "-u", "startup.py"]
