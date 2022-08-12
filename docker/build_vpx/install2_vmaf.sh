#!/bin/bash

### BUILD LIBVMAF
cd / && \
  git clone https://github.com/Netflix/vmaf.git && \
  cd vmaf && \
  PYTHONPATH=/vmaf/python/src:/vmaf:$PYTHONPATH PATH=/vmaf:/vmaf/src/libvmaf:$PATH make -j 24 && \
  make install

