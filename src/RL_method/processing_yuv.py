#Convert the 4K yuv file to MP4 file

import os
import sys
import subprocess
import time
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt

# Path: sheepmao/Segue/src/RL_method/processing_yuv.py

def convert_yuv_to_mp4(yuv_file, mp4_file, width, height, fps):
    # Convert the 4K yuv file to MP4 file
    cmd = 'ffmpeg -i {} -c:v libx264 -crf 18 -pix_fmt yuv420p -s {}x{} -r {} {}' \
          .format(yuv_file,width, height, fps, mp4_file)
    print("cmd:",cmd)
    # call the command 
    proc = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    outs, errs = proc.communicate()
if __name__ == '__main__':
    # Convert the 4K yuv file to MP4 file
    video_source_dir = './4K_video'
    video_target_dir = './video_target/4K_video'
    video_list = os.listdir(video_source_dir)
    if not os.path.exists(video_target_dir):
        os.makedirs(video_target_dir)
    for video in video_list:
        print('processing:',video)
        video_name = video.split('.')[0]
        yuv_file = os.path.join(video_source_dir, video)
        mp4_file = os.path.join(video_target_dir, video_name + '.mp4')
        convert_yuv_to_mp4(yuv_file, mp4_file, 3840, 2160, 60)
        #check if the file exists
        if os.path.exists(mp4_file):
            print('success:',video)
        else:
            print('fail:',video)