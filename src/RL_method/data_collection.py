#This code used to read segment vmaf and parameter from encoded segment
#Also, it will use Resnet50 to extract the feature of each segment

import os
import json
#import cv2
import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew
from siti_tools.siti import SiTiCalculator
import subprocess
# from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
# from tensorflow.keras.preprocessing import image
# from tensorflow.keras.models import Model

# Initialize ResNet50 model
# base_model = ResNet50(weights='imagenet')
# model = Model(inputs=base_model.input, outputs=base_model.get_layer('avg_pool').output)

def run_ffprobe_command(command):
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
    return json.loads(result.stdout)

def extract_features_with_ffprobe(file_path):
    command = f'ffprobe -f lavfi -i "movie={file_path},entropy,scdet,signalstats" -show_frames -show_streams -select_streams v -of json'
    print("Extract feature command:",command)
    data = run_ffprobe_command(command)
    # Extract desired features from data
    # Example: Extracting luminance ('lum')
    lum_values = [float(frame['tags']['lavfi.signalstats.YAVG']) for frame in data['frames']]
    # Example: Extracting chrominance ('chr')
    chr_values = [float(frame['tags']['lavfi.signalstats.UAVG']) for frame in data['frames']]
    # Example: Extracting saturation ('sat')
    sat_values = [float(frame['tags']['lavfi.signalstats.VAVG']) for frame in data['frames']]
    # Example: Extracting Hue ('hue')
    hue_values = [float(frame['tags']['lavfi.signalstats.HUEAVG']) for frame in data['frames']]
    # Example: Extracting entropy ('entropy')
    frame_rates = [float(streams['r_frame_rate'].split('/')[0]) for streams in data['streams']]
    # print the value
    print("lum_values:",lum_values)
    print("chr_values:",chr_values)
    print("sat_values:",sat_values)
    print("hue_values:",hue_values)
    print("frame_rates:",frame_rates)
    return lum_values, chr_values, sat_values, hue_values,frame_rates

def calculate_statistics(values):
    mean = np.mean(values)
    std_dev = np.std(values)
    kurt = kurtosis(values)
    skewness = skew(values)
    return mean, std_dev, kurt, skewness

def extract_features_with_siti(file_path):
    # Initialize SiTi calculator with format = 420p
    si_ti_calculator = SiTiCalculator()
    si, ti = si_ti_calculator.calculate(file_path)
    return si, ti


def extract_features_from_frame(frame):
    img_array = preprocess_input(frame)
    features = model.predict(np.expand_dims(img_array, axis=0))
    return features.flatten()

def get_middle_frame(video_path):
    '''Extracts the middle frame from a video file and resizes it to 224x224 pixels'''
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count // 2)
    success, frame = cap.read()
    frame = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_AREA)
    cap.release()
    if success:
        return frame
    else:
        raise ValueError("Could not read frame from video")

def process_directory(directory):
    segments_dir = os.path.join(directory, 'segments')
    vmaf_file_dir = os.path.join(directory, 'segments/segments_vmaf.json')



    features, durations, crfs, vmafs ,frame_rates = [], [], [], [],[]
    #print("segments_dir:",segments_dir)
    for segment_filename in os.listdir(segments_dir):
        if not segment_filename.endswith('.mp4'):
            continue
        segment_path = os.path.join(segments_dir, segment_filename)
        #print(f'segment number :{segment_filename}')

        vmaf_path = os.path.join(vmaf_file_dir, segment_filename)
        vmaf_path = vmaf_path.replace('.mp4', '.vpf')
        #print("vmaf_path:",vmaf_path)
        # Load VMAF scores
        with open(vmaf_path, 'r') as file:
            vmaf_data = json.load(file)
        #print(f"{vmaf_path} : vmaf_data:",vmaf_data)
        # Compute average VMAF for the segment
        segment_index = int(segment_filename.split('.')[0])  # assuming filename format is "1.mp4", "2.mp4", etc.
        segment_vmaf = np.mean(vmaf_data['vmaf_per_frame'])
        # print segment index and average vmaf
        print(f"segment index:{segment_index} , segment_vmaf:{segment_vmaf}")
        vmafs.append(segment_vmaf)

        # Extract features from the segment using FFprobe
        lum_values, chr_values, sat_values, hue_values,frame_rate = extract_features_with_ffprobe(segment_path)
        frame_rates.append(frame_rate)
        
        lum_mean, lum_std_dev, lum_kurt, lum_skew = calculate_statistics(lum_values)
        chr_mean, chr_std_dev, chr_kurt, chr_skew = calculate_statistics(chr_values)
        sat_mean, sat_std_dev, sat_kurt, sat_skew = calculate_statistics(sat_values)
        hue_mean, hue_std_dev, hue_kurt, hue_skew = calculate_statistics(hue_values)

        # # Extract features from the segment using SiTi
        # si, ti = extract_features_with_siti(segment_path)
        # # calculate_statistics(si)
        # si_mean, si_std_dev, si_kurt, si_skew = calculate_statistics(si)
        # ti_mean, ti_std_dev, ti_kurt, ti_skew = calculate_statistics(ti)


        # Append features to list
        features.append([lum_mean, lum_std_dev, lum_kurt, lum_skew,
                            chr_mean, chr_std_dev, chr_kurt, chr_skew,
                            sat_mean, sat_std_dev, sat_kurt, sat_skew,
                            hue_mean, hue_std_dev, hue_kurt, hue_skew])
                            # si, ti,
                            # ti_mean, ti_std_dev, ti_kurt, ti_skew])
        #Print the features shape
        print("features shape:",np.array(features).shape)

        # # Extract middle frame from the segment
        # frame = get_middle_frame(segment_path)

        # # Extract features from the frame
        # segment_features = extract_features_from_frame(frame)
        # features.append(segment_features)

        # Extract duration and CRF from directory name
        # Example name ./data_generation/YachtRide_3840x2160_120fps_420_8bit_HEVC_RAW/raw_segment_output/videos/426x240/15x2
        print("directory:",directory)
        duration,crf = directory.split('/')[-1].split('x')
        print("duration:",duration)
        print("crf:",crf)
        durations.append(duration)
        crfs.append(crf)





    return features, durations, crfs, vmafs,frame_rates



# Process all directories in the 'generation_data' folder
segment_folder_template = 'raw_segment_output/videos/426x240/'
video_data_folder = './RL/data_generation'
all_features, all_durations, all_crfs, all_vmafs,all_frame_rates = [], [], [], [],[]

for video_dir_name in os.listdir(video_data_folder):
    print("video_dir_name:",video_dir_name)
    print("video_data_folder:",video_data_folder)
    seg_dir_path = os.path.join(video_data_folder, video_dir_name,segment_folder_template)
    print("seg_dir_path:",seg_dir_path)
    for segment_dir_name in os.listdir(seg_dir_path):
        dir_path = os.path.join(seg_dir_path, segment_dir_name)
        print("dir_path:",dir_path)
        if os.path.isdir(dir_path):
            features, durations, crfs, vmafs,frame_rates = process_directory(dir_path)
            all_features.extend(features)
            all_durations.extend(durations)
            all_crfs.extend(crfs)
            all_vmafs.extend(vmafs)
            all_frame_rates.extend(frame_rates)
            # Check lengths
    print(f'Lengths: Features={len(all_features)}, Durations={len(all_durations)}, \
          CRFs={len(all_crfs)}, VMAFs={len(all_vmafs)}, Frame Rates={len(all_frame_rates)}')
    # Create DataFrame and save to CSV
    video_df = pd.DataFrame({
        'features': all_features,
        'duration': all_durations,
        'crf': all_crfs,
        'vmaf': all_vmafs,
        'frame_rate': all_frame_rates

    })
    video_name = video_dir_name.split('.')[0]
    video_df.to_csv(f'{video_name}_segment_data.csv', index=False)

