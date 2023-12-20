#This file is used to generate the data for training the RL model.
#The data will through the following steps:
#1. Split the video into segments with different CRF values and durations by create Video object and use the segment_h264 function.
#2. Calculate the VMAF score of each segment by load_vmaf function.
#3. Save the data into the training dataset.
#4. Repeat the above steps for each video.

import subprocess
import os
import glob
import pandas as pd
import json
from src.utils.video_factory import Video, FullVideo, EXTENSION
from src.utils.video.multilevel_video_factory import MultilevelVideoFactory

## custom logger
from src.utils.logging.logging_segue import create_logger
def pmkdir(kdir):
    if not os.path.exists(kdir):
        os.makedirs(kdir)

# 計算VMAF的函數（需要根據實際情況實現）
def calculate_vmaf(video_file):
    # 實現VMAF計算邏輯
    pass

# 保存數據的函數
def save_data(crf, duration, vmaf_score):
    # 將數據寫入文件或數據庫
    pass
def format_dataframe_segments(segments_keys_timestamp,segments_keys_indexes):
    """
    Formats the segments structure into a pandas DataFrame.
    Args:
        segments_keys_timestamp (list): List of segment key timestamps.
        segments_keys_indexes (list): List of segment key indexes.
    Returns:
        pd.DataFrame: DataFrame with segment information.
    """
    assert len(segments_keys_timestamp) == len(segments_keys_indexes), "The number of segments keys timestamps and indexes must be the same."
    #print("the total frames",len(segments_keys_indexes))
    if len (segments_keys_timestamp) == 0:
        print("No segments found. Run the RL grouper first.")
        return None
    
    ## check if the first segment is the first frame of the video, if so, delete it
    ## Not sure why
    if segments_keys_indexes[0] ==0:
        del segments_keys_indexes[0]
        del segments_keys_timestamp[0]

    previous_end_timestamp = 0
    previous_end_frame = 0
    scene_df = pd.DataFrame(columns=['End Time', 'Start Time', 'End Frame', 'Start Frame'])

    for index , k in enumerate(segments_keys_indexes):
        end_frame = segments_keys_indexes[index]
        end_time = segments_keys_timestamp[index]

        d = {'End Time': [end_time], 'Start Time': [previous_end_timestamp], 'End Frame': [end_frame], 'Start Frame': [previous_end_frame]}
        line = pd.DataFrame(data=d)
        scene_df = scene_df.append(line, ignore_index=True)

        previous_end_timestamp = end_time
        previous_end_frame = end_frame
    print("scene_df number",len(scene_df))
    return scene_df

if __name__== "__main__":
    #
    raw_segment_output_template = "./RL/data_generation/{}/raw_segment_output"
    log_dir_template = "./RL/data_generation/{}/logs"

    Verbose = True
    # 2560x1440 1920x1080 1280x720 854x480 640x360 426x240
    video_data = {	"resolutions": " 1920x1080 426x240",
	                "video_extension": "mp4",
	                "video_codec": "h264"}
    vmaf_model = "vmaf_hdtv"
    # 設定CRF值和segment duration的範圍
    crf_values = [15,17,21, 23, 27, 29,31, 34, 40, 46,52,55]  
    segment_durations = [0.5, 1.0,2,3.0,4.0,5]

    # 視頻文件路徑
    video_folder_path = "./video_source"
    if not os.path.exists(video_folder_path):
        raise FileNotFoundError("Video file not found")
    # 輸出目錄
    output_dir = "path/to/output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)   # 創建目錄

    # 遍歷視頻文件
    for video_name in os.listdir(video_folder_path):
        # folder dir creation
        log_dir = log_dir_template.format(video_name.split('.')[0])
        raw_segment_output = raw_segment_output_template.format(video_name.split('.')[0])
        video_path = os.path.join(video_folder_path, video_name)
    # 處理每個CRF值和duration組合
        for crf in crf_values:
            for duration in segment_durations:
                # 定義輸出文件名
                #output_file = os.path.join(output_dir, f"video_crf{crf}_dur{duration}.mp4")
                pmkdir(raw_segment_output)  
                pmkdir(log_dir)
                ## Create logger
                print(f"Create logger for {video_name} at {log_dir}")
                main_logger = create_logger("main_logger", os.path.join(log_dir, "main.log"),Verbose)
                # print path
                print(f"Video path: {video_path}")
                # Create video object
                raw_video = Video(video_path,logdir=log_dir,verbose=Verbose)

                print(f'Video obj for {video_path} created, \
                total frames: {raw_video.load_total_frames()}, \
                fps: {raw_video.load_fps()}')
                total_frames = raw_video.load_total_frames()
                fps = raw_video.load_fps()
                # Create segment structure
                segments_key_frame_indexes = [x for x in range(0, int(total_frames), int(duration * fps))]
                segments_keys_timestamps = [float(x) / fps for x in segments_key_frame_indexes]
        
                # Add the end frame and end timstamp of the video to indicate the end of the last segment
                segments_key_frame_indexes.append(raw_video.load_total_frames())
                segments_keys_timestamps.append(raw_video.load_duration())

                # Save segment structure
                scene_df = format_dataframe_segments(segments_keys_timestamps,segments_key_frame_indexes)

                resolutions = video_data["resolutions"].split()
                reference = FullVideo(raw_video)
                rescaled_video_list = []
                forced_key_frames = scene_df['Start Frame'].tolist() 
                forced_key_times_stamps = scene_df['Start Time'].tolist()
                #print(f"Forced key frames: {forced_key_frames}")
                #print(f"Forced key timestamps: {forced_key_times_stamps}")
                # Create the rescaled videos
                for i,res in enumerate(resolutions):
                    print(f"res {i}: {res}")
                    # character to string to int
                    width,height = int(res.split('x')[0]),int(res.split('x')[1])
                    # Create the output directories for different resolutions
                    rescaled_video_dir_path = os.path.join(raw_segment_output,"videos/{res}/{crf}x{duration}".format(res=res,crf=crf,duration=duration))
                    pmkdir(rescaled_video_dir_path)




                    ## Transcoding the video to the target resolution
                    rescaled_video = raw_video.rescale_h264_constant_quality(video_out_path=os.path.join(rescaled_video_dir_path,"unframented.mp4"),\
                    width=width,height=height,crf=crf,forced_key_frames=forced_key_frames)

                    rescaled_resolution = rescaled_video.video_path()
                    print(f'After rescaling, the video resolution is {rescaled_resolution}')

                    ## Chunktize_raw_video into segment
                    chunk_out_dir = os.path.join(rescaled_video_dir_path,'segments')
                    pmkdir(chunk_out_dir)
                    rescaled_video = FullVideo(rescaled_video)
                    frames_count_total = rescaled_video.segment_h264(forced_keyframes_indexes=forced_key_frames,\
                                                        forced_keyframes_timestamps=forced_key_times_stamps,\
                                                        assembled_chunks_dir=chunk_out_dir)
                    # print(f"Total frames count Before segment: {raw_video.load_total_frames()}")
                    # print(f"Total frames count After segment: {frames_count_total}")
                    # print ("Segmentation done. Check the output folder for the segments.")

                    # save the video object
                    rescaled_video_list.append(rescaled_video)


                # Calculate VMAF for the rescaled videos
                for rescaled_video,res in zip(rescaled_video_list,resolutions):
                    ## VMAF computing
                    vmaf_file_out = os.path.join(raw_segment_output,f'videos/{res}/{crf}x{duration}/',"vmaf/vmaf.json")
                    rescaled_video.load_vmaf(reference,vmaf_file_out,vmaf_model)
                    print("VMAF computed for rescaled video at resolution {}".format(res))
                    print("Assign VMAF to segments")
                    segment_vmaf_file_out = os.path.join(raw_segment_output,f'videos/{res}/{crf}x{duration}/',"segments/segments_vmaf.json")
                    rescaled_video.assign_vmaf_to_segments(segment_vmaf_file_out)
            


                # TODO: 計算VMAF分數
                # vmaf_score = calculate_vmaf(output_file)

                # TODO: 將結果保存至訓練數據集
                # save_data(crf, duration, vmaf_score)