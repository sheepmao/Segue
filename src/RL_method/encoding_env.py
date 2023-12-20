## standard libraries import
import tempfile
import glob, json, os, subprocess, datetime, subprocess
import pandas as pd 
from dateutil import parser
import argparse, sys
import numpy as np
import importlib.machinery
import traceback
import shutil
from multiprocessing import Process

## custom logger
from src.utils.logging.logging_segue import create_logger

## utils
from src.utils.video.level import Level
from src.utils.video_factory import Video, FullVideo, EXTENSION
from src.utils.video.multilevel_video_factory import MultilevelVideoFactory
from src.augmenter.splitting_strategies.h264_splitter import H264Splitter
## constants reused across the system
from src.consts.grouper_configs_consts import *
from src.consts.video_configs_consts import *
from src.consts.keys_consts import *
from src.consts.segments_composition_consts import *
import traceback
## ABR algorithms
## QoE metrics

## Simulator modules
import src.simulator.fixed_env as env
import src.simulator.load_trace as load_trace
from src.simulator.sim_state import SimState, SimStateSet, createSimStateSet, RESULTS_DUMP
#from src.grouper.grouping_policies.grouper_h264_RL import RLGrouperPolicy

def pmkdir(kdir):
    if not os.path.exists(kdir):
        os.makedirs(kdir)

def read_configs(configs):
    with open(configs, 'r') as fin:
        data = json.load(fin)
    return data


def empty(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print("Error in empyting log folder")
            sys.exit(-1)
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
    return scene_df
def chunketize_video_segments(segement_df,raw_video,crf_list,file_out_path,Force= True):
    """
    Splits a video into chunks based on segment data.
    Args:
        segment_df (pd.DataFrame): DataFrame containing segment information.
        raw_video (Video): Video object to be chunketized.
        crf_list (list): List of CRF values for each segment.
        file_out_path (str): Output path for the chunked segments.
        force (bool): Force overwrite existing files.
    Returns:
        Video: Video object after chunketization.
    """
    # Create the output directories
    chunk_out_dir = os.path.join(file_out_path,'segments') # the output dir for the chunked segments
    ffprobe_out_dir = os.path.join(file_out_path,'ffprobe') # the output dir for the ffprobe output
    video_unfragmented_out_dir = os.path.join(file_out_path,'unfragmented') # the output dir for the unfragmented video
 
    pmkdir(chunk_out_dir)
    pmkdir(ffprobe_out_dir)
    pmkdir(video_unfragmented_out_dir)
    
    main_video_unfragmented = os.path.join(video_unfragmented_out_dir, 'unfragmented.mp4')
    forced_key_frames = segement_df['Start Frame'].tolist()
    forced_key_times_stamps = segement_df['Start Time'].tolist()

    # TODO : change the  rescale_h264_constant_quality to rescale_h264_constant_quality_list to support different crf for each segment
    # DEBUG: the rescale_h264_constant_quality_list is not working Try to fix it

    # rescaled_video = raw_video.rescale_h264_constant_quality_list(video_out_path=main_video_unfragmented,\
    #                                                          crf_values = crf_list, \
    #                                                          gop = -1, \
    #                                                          forced_key_frames = forced_key_frames, \
    #                                                          force = Force
    #                                                                 )
    rescaled_video = raw_video.rescale_h264_constant_quality(video_out_path=main_video_unfragmented,\
                                                            crf = 23, \
                                                            gop = -1, \
                                                            forced_key_frames = forced_key_frames, \
                                                            force = Force
                                                                )

    raw_video_encoded = FullVideo(rescaled_video)

    ## Split the unfragmented video into segments
    frames_count_total = raw_video_encoded.segment_h264(forced_keyframes_indexes=forced_key_frames,\
                                                        forced_keyframes_timestamps=forced_key_times_stamps,\
                                                        assembled_chunks_dir=chunk_out_dir)
    print(f"Total frames count Before segment: {raw_video.load_total_frames()}")
    print(f"Total frames count After segment: {frames_count_total}")
    print ("Segmentation done. Check the output folder for the segments.")

    return raw_video_encoded

def build_segment_composition(segment_df,out_dir):
    """
    Builds segment composition and saves it as a JSON file.
    Args:
        segment_df (pd.DataFrame): DataFrame containing segment information.
        out_dir (str): Directory to save the segment composition file.
    """
    segment_data = {}
    for i, chunk in scene_df.iterrows():
        time_absolute_start = chunk['Start Time']
        time_absolute_end = chunk['End Time']
        frame_absolute_start = chunk['Start Frame']
        frame_absolute_end = chunk['End Frame']

        time_relative_start = 0.0
        time_relative_end = time_absolute_end - time_absolute_start
        frame_relative_start = 0
        frame_relative_end = frame_absolute_end - frame_absolute_start

        segment_data[i] = {}
        segment_data[i]["segment_start_time_absolute"] = time_absolute_start
        segment_data[i]["segment_end_time_absolute"] = time_absolute_end
        segment_data[i]["segment_start_time_relative"] = time_relative_start
        segment_data[i]["segment_end_time_relative"] = time_relative_end

        segment_data[i]["segment_start_frame_absolute"] = frame_absolute_start
        segment_data[i]["segment_end_frame_absolute"] = frame_absolute_end
        segment_data[i]["segment_start_frame_relative"] = frame_relative_start
        segment_data[i]["segment_end_frame_relative"] = frame_relative_end

    with open(out_dir, 'w') as fout:
        pd_dataframe = pd.DataFrame(segment_data)
        pd_dataframe.to_json(fout)
    print(f"Segments structure json file saved to {out_dir}")

def load_video_properties(VIDEO_PROPERTIES_FILE):
    """
    Loads video properties from a JSON file.
    Args:
        video_properties_file (str): Path to the video properties JSON file.
    Returns:
        dict: Dictionary containing video properties.
    """
    with open(VIDEO_PROPERTIES_FILE, "r") as fin:
        data = json.load(fin)
    ss = {}
    for idx in range(len(data.keys())):
        ss[idx] = data[str(idx)]
    return ss

if __name__ == "__main__":
    # Configs data
    # video_data = {	"resolutions": "2560x1440 1920x1080 1280x720 854x480 640x360 ",
	#                 "video_extension": "mp4",
	#                 "video_codec": "h264"}
    video_data = {	"resolutions": "2560x1440 854x480 ",
	                "video_extension": "mp4",
	                "video_codec": "h264"}
    vmaf_model = "vmaf_4k"
    QoE_config = {
        	        "simulation_reward_module" : "src/utils/reward/std_reward_estimator.py",
                    "simulation_reward_class" : "STDRewardEstimator",
                    "reward_id": "linear_standard_param",
                    "simulation_reward_parameters" : {
            				"unit_time": 1.0,
            				"rebuffering_penalty": 100.0 ,
            				"switching_penalty": 1,
            				"vmaf_gain": 1 ,
            				"time_normalization_factor" : 4.0,
					"aggregate_mean": True}      
                    }
    ABR_config = {
        "BBA1": "src/simulator/simulator_policies/abr/BBA1_v8_h264.py",
        "RB:" :"src/simulator/simulator_policies/abr/rb_bitmovin.py",
        "RMPC": "rmpc5_quick.py"
    }
    # Directories data
    bitrate_ladder_file = "./resources/bitmovin_bitrate_settings.csv"
    video_dir_path = "./video_source"
    raw_segment_output_template = "./RL/{}/raw_segment_output"
    log_dir_template = "./RL/{}/logs"
    segment_structure_store_dir_template = "./RL/{}/segment_structure_store_dir"
    segments_structure_out_template = "./RL/{}/segment_structure_store_dir/segments_structure_out.json"
    Verbose = True # -> Debug mode
    Force = False # -> Force overwrite the existed output files
    TRACE_FILE_PATH = "./traces/oboe_traces/"

    video_path_list = glob.glob(os.path.join(video_dir_path, "*"))
    raw_video_list = []
    encoded_video_list = []


    # read video and create video object for each video
    for video_path in video_path_list:
        # Create the output directories
        video_name = os.path.basename(video_path)
        log_dir = log_dir_template.format(video_name.split('.')[0])
        raw_segment_output = raw_segment_output_template.format(video_name.split('.')[0])
        segment_structure_store_dir = segment_structure_store_dir_template.format(video_name.split('.')[0])
        segments_structure_out = segments_structure_out_template.format(video_name.split('.')[0])
        pmkdir(raw_segment_output)  
        pmkdir(log_dir)
        pmkdir(segment_structure_store_dir)

        ## Create logger
        print(f"Create logger for {video_name} at {log_dir}")
        main_logger = create_logger("main_logger", os.path.join(log_dir, "main.log"),Verbose)



        #### RL grouper policy ####
        ## Run RL and get the segments structure
        # TODO: run RL grouper policy to get following data
        segments_keys_timestamps = [0.0, 5.0, 10.0, 20.75, 28.042, 33.042, 38.042, 47.709, 52.709, 56.084, 63.793000000000006, 68.793, 75.54400000000001, 79.96100000000001, 84.96100000000001, 91.42000000000002, 99.75400000000002, 103.92100000000002, 108.92100000000002, 112.67100000000002, 117.67100000000002, 120.88000000000002, 123.46400000000003, 126.88100000000003, 131.88100000000003, 136.88100000000003, 141.88100000000003, 146.38100000000003, 149.09000000000003, 154.09000000000003, 156.00700000000003, 160.84100000000004, 166.21700000000004, 168.00900000000004, 176.13500000000005, 180.51000000000005, 185.51000000000005, 189.34400000000005, 196.92900000000006, 204.18000000000006, 208.88900000000007, 213.80600000000007, 220.51500000000007, 226.26600000000008, 232.47500000000008, 237.47500000000008, 243.5180000000001, 248.5180000000001, 255.3520000000001, 259.5200000000001, 262.8540000000001, 270.3550000000001, 277.9390000000001, 284.7320000000001, 289.7320000000001, 297.1500000000001, 300.3590000000001, 305.2340000000001, 312.52600000000007, 317.23500000000007, 319.23500000000007, 322.1940000000001, 323.73600000000005, 328.73600000000005, 334.36100000000005, 339.778, 344.778, 349.778, 354.778, 359.778, 364.778, 369.778, 375.404, 381.197, 386.197, 390.822, 394.531, 399.74, 404.699, 410.45, 416.159, 421.911, 427.538, 433.747, 442.248, 449.91499999999996, 456.78999999999996, 462.04099999999994, 467.04099999999994, 472.9169999999999, 480.2089999999999, 490.5019999999999, 495.5019999999999, 502.5019999999999, 512.502, 522.502, 532.502, 537.502, 542.502, 547.502, 552.502, 557.502, 562.502, 567.502, 572.502, 577.502, 580.9609999999999, 585.9609999999999, 590.9609999999999]
        segments_keys_indexes = [0, 120.0, 240.0, 498.0, 673.0, 793.0, 913.0, 1145.0, 1265.0, 1346.0, 1531.0, 1651.0, 1813.0, 1919.0, 2039.0, 2194.0, 2394.0, 2494.0, 2614.0, 2704.0, 2824.0, 2901.0, 2963.0, 3045.0, 3165.0, 3285.0, 3405.0, 3513.0, 3578.0, 3698.0, 3744.0, 3860.0, 3989.0, 4032.0, 4227.0, 4332.0, 4452.0, 4544.0, 4726.0, 4900.0, 5013.0, 5131.0, 5292.0, 5430.0, 5579.0, 5699.0, 5844.0, 5964.0, 6128.0, 6228.0, 6308.0, 6488.0, 6670.0, 6833.0, 6953.0, 7131.0, 7208.0, 7325.0, 7500.0, 7613.0, 7661.0, 7732.0, 7769.0, 7889.0, 8024.0, 8154.0, 8274.0, 8394.0, 8514.0, 8634.0, 8754.0, 8874.0, 9009.0, 9148.0, 9268.0, 9379.0, 9468.0, 9593.0, 9712.0, 9850.0, 9987.0, 10125.0, 10260.0, 10409.0, 10613.0, 10797.0, 10962.0, 11088.0, 11208.0, 11349.0, 11524.0, 11771.0, 11891.0, 12059.0, 12299.0, 12539.0, 12779.0, 12899.0, 13019.0, 13139.0, 13259.0, 13379.0, 13499.0, 13619.0, 13739.0, 13859.0, 13942.0, 14062.0, 14182.0]
        crf_list = np.ones(len(segments_keys_timestamps))*23


        # Create Video object from the video path and log the video info
        # Video object is the wrapper of the video file containing FFmpeg and FFprobe functionalities
        raw_video = Video(video_path,logdir=log_dir,verbose=Verbose)
        print(f'Video obj for {video_name} created, \
                total frames: {raw_video.load_total_frames()}, \
                fps: {raw_video.load_fps()}')

                
        # Add the end frame and end timstamp of the video to indicate the end of the last segment
        segments_keys_indexes.append(raw_video.load_total_frames())
        segments_keys_timestamps.append(raw_video.load_duration())

        # Format the segments structure into a pandas DataFrame 
        scene_df = format_dataframe_segments(segments_keys_timestamps,segments_keys_indexes)
        # build the segments structure json file
        build_segment_composition(scene_df,segments_structure_out)
        ### After getting the segments structure, we can do real encoding


        #### Start processing the video ####
        # get the video resolution list
        resolutions = video_data["resolutions"].split()
        reference = FullVideo(raw_video)
        rescaled_video_list = []
        # Create the rescaled videos
        for i,res in enumerate(resolutions):
            print(f"res {i}: {res}")
            # Create the output directories for different resolutions
            rescaled_video_dir_path = os.path.join(raw_segment_output,"videos/{res}/".format(res=res))
            pmkdir(rescaled_video_dir_path)


            # # parameter for rescaleing
            forced_key_frames = scene_df['Start Frame'].tolist() 
            method = {}
            method["keyframes_method"] = "force_keys"
            method["keyframes_indexes_list"] = forced_key_frames
            ## Transcoding the video to the target resolution
            rescaled_video = raw_video.rescale_at_resolution(file_out=os.path.join(rescaled_video_dir_path,"unframented.mp4"),\
                resolution=res,codec='h264',ladders_df=bitrate_ladder_file,method = method,cache =False,cache_file=None )
            rescaled_resolution = rescaled_video.video_path()
            print(f'After rescaling, the video resolution is {rescaled_resolution}')


            ## Chunktize_raw_video into segment
            assert scene_df is not None, "Segment structure data -> scene_df is None"
            rescaled_video = chunketize_video_segments(segement_df=scene_df,raw_video=rescaled_video,crf_list=crf_list,\
                            file_out_path=rescaled_video_dir_path,Force=Force)
            rescaled_video_list.append(rescaled_video)


        # Calculate VMAF for the rescaled videos
        for rescaled_video,res in zip(rescaled_video_list,resolutions):
            ## VMAF computing
            vmaf_file_out = os.path.join(raw_segment_output,f'videos/{res}/',"vmaf/vmaf.json")
            rescaled_video.load_vmaf(reference,vmaf_file_out,vmaf_model)
            print("VMAF computed for rescaled video at resolution {}".format(res))
            print("Assign VMAF to segments")
            segment_vmaf_file_out = os.path.join(raw_segment_output,f'videos/{res}/',"segments/segments_vmaf.json")
            rescaled_video.assign_vmaf_to_segments(segment_vmaf_file_out)
            # FFprobe data collecting
            ffprobe_file_out = os.path.join(raw_segment_output,f'videos/{res}/',"ffprobe/ffprobe.json")
            rescaled_video.load_ffprobe(ffprobe_file_out)
            print("ffprobe computed for rescaled video at resolution {}".format(res))
            print("Assign ffprobe to segments")
            segment_ffprobe_file_out = os.path.join(raw_segment_output,f'videos/{res}/',"segments/segments_ffprobe.json")
            rescaled_video.assign_ffprobe_to_segments(segment_ffprobe_file_out)

        ## Create the multilevel video obj  with rescaled videos
        Video_fact = MultilevelVideoFactory(main_logger)
        MultiResVideo = Video_fact.multilevel_video_from_full_videos(rescaled_video_list)

        ## Log the results
        std_dataframe = MultiResVideo.load_std_dataframe()
        std_dataframe.to_csv(os.path.join(raw_segment_output,"videos","std_dataframe.csv"),index=False)

        sim_data = MultiResVideo.get_simulation_data()
        sim_file_out = os.path.join(raw_segment_output,"videos","sim_data.json")
        with open(sim_file_out, 'w') as fout:
            json.dump(sim_data, fout)
        #### Video processing done ####


        #### Start Simulating ABR ####
        print("SIM data:",sim_data)
        VIDEO_PROPERTIES = load_video_properties(sim_file_out)
        print("VIDEO_PROPERTIES:",VIDEO_PROPERTIES)
        

        fps = round(len(VIDEO_PROPERTIES[0]['levels'][0]['vmaf_per_frame'])) / VIDEO_PROPERTIES[0]['duration'] #segment frame number/segment duration
        ## Setup the QoE module
        qoe_module = QoE_config["simulation_reward_module"]
        assert os.path.exists(qoe_module), "QoE module does not exist"
        QoE_class_name = QoE_config["simulation_reward_class"]
        QoE_parameters = QoE_config["simulation_reward_parameters"]
        QoE_module_str = qoe_module.replace("/", ".").replace(".py", "")
        main_logger.info(f'Loading QoE module{qoe_module}, Class name: {QoE_class_name}')
        qoe_module = getattr(importlib.import_module(QoE_module_str), QoE_class_name)
        QoE_module = qoe_module(main_logger, fps, QoE_parameters)

        ## Setup the ABR module
        ABR_module = importlib.machinery.SourceFileLoader('abr',ABR_config["BBA1"]).load_module()

        ### Create the simulator
        for trace in os.listdir(TRACE_FILE_PATH):
            trace_path = os.path.join(TRACE_FILE_PATH,trace)
            print("Trace path:",trace_path)
            sim_state_set = SimStateSet(ABR_module, QoE_module, [load_trace.load_trace(trace_path)])

            ## Run the simulator
            start_segment = 0
            end_segment = len(VIDEO_PROPERTIES) -1
            sim_state_set.step_till_end(VIDEO_PROPERTIES, start_segment, end_segment,use_pool = False)

            sim_state = sim_state_set.ss_set[0]

            ## Log the results of the simulation with trace
            simulation_results_dir_path = os.path.join(raw_segment_output,"videos","simulation_results")
            pmkdir(simulation_results_dir_path)
            file_name = trace.split('.')[0] + ".csv"
            simulation_results_file_path = os.path.join(simulation_results_dir_path,file_name)
            simulation_df = pd.DataFrame(columns=RESULTS_DUMP)
            for idx in range(len(VIDEO_PROPERTIES)):
                simulation_df = simulation_df.append(sim_state.log_dict(idx), ignore_index=True)
            simulation_df.to_csv(simulation_results_file_path)
