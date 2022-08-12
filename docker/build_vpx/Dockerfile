# Choose and name our temporary image.
FROM ubuntu:20.04 

# Install dependencies required to git clone.
ADD install1_packages.sh /install1_packages.sh
RUN /install1_packages.sh

ADD install11_libvpx.sh /install11_libvpx.sh
RUN /install11_libvpx.sh

ADD install2_vmaf.sh /install2_vmaf.sh
RUN /install2_vmaf.sh

ADD install3_aom.sh /install3_aom.sh
RUN /install3_aom.sh

ADD install4_ffmpeg.sh /install4_ffmpeg.sh
#RUN /install4_ffmpeg.sh
#
#ADD install99_clean.sh /install99_clean.sh
#RUN /install99_clean.sh
#
#RUN ln -s /usr/local/lib/x86_64-linux-gnu/libvmaf.so /usr/lib/libvmaf.so
#RUN ln -s /usr/local/lib/x86_64-linux-gnu/libvmaf.so.0 /usr/lib/libvmaf.so.0
#RUN ln -s /usr/local/lib/x86_64-linux-gnu/libvmaf.so.0.0.0 /usr/lib/libvmaf.so.0.0.0
