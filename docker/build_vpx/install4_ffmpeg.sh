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

cd /ffmpeg_sources && \
wget -O ffmpeg-snapshot.tar.bz2 https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 && \
tar xjvf ffmpeg-snapshot.tar.bz2 && \
cd ffmpeg && \
PATH="/bin:$PATH" PKG_CONFIG_PATH="/ffmpeg_build/lib/pkgconfig" ./configure \
  --prefix="/ffmpeg_build" \
  --pkg-config-flags="--static" \
  --extra-cflags="-I/ffmpeg_build/include" \
  --extra-ldflags="-L/ffmpeg_build/lib" \
  --extra-libs="-lpthread -lm" \
  --bindir="/bin" \
  --enable-gpl \
  --enable-libaom \
  --enable-libass \
  --enable-libfdk-aac \
  --enable-libfreetype \
  --enable-libmp3lame \
  --enable-libopus \
  --enable-libvorbis \
  --enable-libvpx \
  --enable-libx264 \
  --enable-libx265 \
  --enable-libvmaf \
  --enable-version3 \
  --enable-libfreetype \
  --enable-nonfree && \
PATH="/bin:$PATH" make -j 24 && \
make install && \
hash -r
