#!/bin/bash

mkdir -p /ffmpeg_build
mkdir -p /ffmpeg_sources

### BUILD aom
cd /ffmpeg_sources && \
git -C aom pull 2> /dev/null || git clone --depth 1 https://aomedia.googlesource.com/aom && \
mkdir -p aom_build && \
cd aom_build && \
PATH="/bin:$PATH" cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="/ffmpeg_build" -DENABLE_SHARED=off -DENABLE_NASM=on ../aom && \
PATH="/bin:$PATH" make -j 24 && \
make install
