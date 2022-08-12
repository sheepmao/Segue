# cleanup all build files
apt-get clean
cd /libvpx && make clean
cd /vmaf && make clean
cd /ffmpeg_sources && make clean
cd /ffmpeg_sources/aom_build && make clean
