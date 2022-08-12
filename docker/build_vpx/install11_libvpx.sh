#!/bin/bash

### BUILD LIBVPX
cd / && \
  git clone https://chromium.googlesource.com/webm/libvpx && \
  cd libvpx &&
  ./configure --prefix=/usr \
  	--enable-pic \
	--enable-shared \
	--disable-install-bins \
	--disable-install-srcs \
	--size-limit=16384x16384 \
	--enable-postproc \
	--enable-multi-res-encoding \
	--enable-temporal-denoising \
	--enable-vp9-temporal-denoising \
	--enable-vp9-postproc \
	--target=x86_64-linux-gcc \
	--enable-webm-io \
	--enable-libyuv &&
  make -j 24 &&
  make install
