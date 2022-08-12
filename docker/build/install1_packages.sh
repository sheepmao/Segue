#!/bin/bash
# set noninteractive installation
mkdir -p /ffmpeg_sources
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y tzdata
ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime
dpkg-reconfigure --frontend noninteractive tzdata
apt-get install -y \
  git make python3-pip libglib2.0-0 libsm6 libxext6 \
  libxrender-dev libavresample4 libavdevice58 vim \
  python3-dev python3-setuptools python3-tk ninja-build

# ffmpeg build dependencies
apt-get install -y \
  autoconf \
  automake \
  build-essential \
  cmake \
  git-core \
  libass-dev \
  libfreetype6-dev \
  libsdl2-dev \
  libtool \
  libva-dev \
  libvdpau-dev \
  libvorbis-dev \
  libxcb1-dev \
  libxcb-shm0-dev \
  libxcb-xfixes0-dev \
  pkg-config \
  texinfo \
  wget \
  nasm \
  yasm \
  libx264-dev \
  libx265-dev \
  libnuma-dev \
  libvpx-dev \
  libfdk-aac-dev \
  libopus-dev \
  libmp3lame-dev \
  libfreetype-dev \
  mkvtoolnix \
  zlib1g-dev 

pip3 install seaborn youtube-dl scenedetect[opencv,progress_bar] \
     numpy scipy matplotlib notebook pandas sympy nose scikit-learn \
     scikit-image h5py sureal meson stable-baselines


