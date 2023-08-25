
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
from src.utils.video_factory import Video, FullVideo, EXTENSION

## constants reused across the system
from src.consts.grouper_configs_consts import *
from src.consts.video_configs_consts import *
from src.consts.keys_consts import *
from src.consts.segments_composition_consts import *
import traceback

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


class Grouper():
    def __init__(self, args):
        
        ## parameter check
        assert os.path.exists(args.video_configs), "Video configuration file doesn't exist"
        assert os.path.exists(args.grouper_configs), "Grouper configuration file doesn't exist"
        assert args.specific_raw_crf > 0, "CRF value must be greater than 0"
        
        self.specific_raw_crf = args.specific_raw_crf
        self.verbose = args.verbose
        ## use RL grouper policy or not
        self.use_rl_policy = args.use_rl_policy
        self.use_rl_policy = False
        if self.use_rl_policy:
            self.logger.info("Using RL grouper policy")
            self.rl_grouper_policy = RLGrouperPolicy()
            #TODO

        ## creation of the logger
        self.logs_dir = args.logs_dir
        if os.path.exists(args.logs_dir):
            empty(args.logs_dir)
        pmkdir(args.logs_dir)
        log_file = os.path.join(args.logs_dir, 'make_chunks_group.log')
        self.logger = create_logger('Grouper: Main', log_file, verbose=args.verbose)

        ## creation of figsdir
        pmkdir(args.figs_dir)
        
        self.raw_segments_out = args.raw_segments
        pmkdir(self.raw_segments_out)

        ## read configurations
        self.video_data = read_configs(args.video_configs)
        self.grouper_data = read_configs(args.grouper_configs) 
        video_original_path = self.video_data[K_VIDEO_PATH]

        assert os.path.exists(video_original_path), "Original video does not exists"

        ## creation of the Ffmpeg wrapper

        self.raw_video  = Video(video_original_path, self.logs_dir, verbose=self.verbose)

        ## gather fps and total frames for debug purpose
        self.logger.debug("Video {} has a total of {} frames for {} fps".format(self.raw_video.video_path(),
                                                                                self.raw_video.load_total_frames(),
                                                                                self.raw_video.load_fps()))

        ## output: json file with the description of the segments
        self.segment_structure_store_dir = os.path.dirname(args.segments_structure_out)
        self.segments_structure_out = args.segments_structure_out
        self.logger.debug("Storing segment structure in {}".format(self.segment_structure_store_dir))
        pmkdir(self.segment_structure_store_dir)
        
        ## creation of the grouper policy class
        grouping_policy_module = self.grouper_data[K_MODULE_GROUPER]
        assert os.path.exists(grouping_policy_module), "Grouper module doesn't exists"

        grouping_policy_module = grouping_policy_module.replace('/', '.').replace('.py', '')
        grouping_policy_class_name = self.grouper_data[K_CLASS_GROUPER]
        

        ## Retieving the class
        try:
            GrouperPolicy = getattr(importlib.import_module(grouping_policy_module), grouping_policy_class_name)
        except:
            self.logger.error("{} doesn't contain class name {}, or some errors are present in module".format(grouping_policy_module, grouping_policy_class_name))
            self.logger.exception("message") 
            sys.exit(-1)
        

        ## Instantiating the class
        try:
            self.grouper_policy = GrouperPolicy(    self.grouper_data,
                                                    self.video_data,
                                                    self.raw_video,
                                                    args.rescaled_video_template,
                                                    args.verbose,
                                                    args.logs_dir,
                                                    args.figs_dir)
        except:
            self.logger.error("Something went wrong in the instantiation of the class")
            self.logger.exception("message")
            sys.exit(-1)

        self.groups = None



    ## run the grouping policy

    def make_groups(self):
        self.logger.info("Determining the groups")

        try:
            if self.use_rl_policy:
                self.logger.info("RL groupers")
                self.groups = self.rl_grouper_policy.make_groups() # -> return a pd dataframe contain the segments structure
            else:
                self.logger.info("Original groupers")
                self.groups = self.grouper_policy.make_groups()# -> return a pd dataframe contain the segments structure
        except:
            self.logger.error("Something went wrong while computing the groups")
            self.logger.exception("message")
            sys.exit(-1)

        self.logger.info("Groups determined succesfully")
        return self.groups

   
   ## apply the grouper decision to the raw video
    def chunketize_raw_segments(self):
        
        assert self.groups is not None, "Groups have not been determined. Did you run this method before make_groups?"
        self.logger.info("Applying grouping policy to the raw video")
        
        ## creating the folders that will store all the informations

        chunk_out_dir = os.path.join(self.raw_segments_out, 'video') # --> video chunks
        ffprobe_out_dir = os.path.join(self.raw_segments_out, 'ffprobe_original') # --> ffprobe file
        video_unfragmented_out_dir = os.path.join(self.raw_segments_out, 'unfragmented') # --> raw video needs to be re-encoded with the proper keyframes. 

        
        self.logger.debug("Storing out chunks in {}".format(chunk_out_dir))
        self.logger.debug("Storing ffprobe in {}".format(ffprobe_out_dir))
        self.logger.debug("Storing video unfragmented in {}".format(video_unfragmented_out_dir))

        
        pmkdir(chunk_out_dir)
        pmkdir(ffprobe_out_dir)
        pmkdir(video_unfragmented_out_dir) 

        
        total_frames = 0 ## --> for debug purpose 
        ffprobe_file_out = os.path.join(ffprobe_out_dir, 'packets_original.json') ## --> ffprobe
        main_video_unfragmented = os.path.join(video_unfragmented_out_dir, 'unfragmented.{}'.format(EXTENSION))
        self.logger.debug("Rescaling video {} in constant quality to {}".format(self.raw_video.video_path(), main_video_unfragmented))
        forced_key_frames = list(self.groups[KSF])
        forced_key_frames_timestamps = list(self.groups[KST])
        self.logger.debug("Forcing key frames at {}".format(forced_key_frames))
        self.logger.debug("Forcing key frames at timestamps {}".format(forced_key_frames_timestamps)) 
        
        ## rescale the video at constant quality with the given forced keyframes


        rescaled_video = self.raw_video.rescale_h264_constant_quality(  main_video_unfragmented, 
                                                                        self.specific_raw_crf, 
                                                                        int(self.raw_video.load_fps()/2), 
                                                                        forced_key_frames=forced_key_frames, 
                                                                        force=False)
        self.raw_video_keys_forced = FullVideo(rescaled_video)
        ## splits the given video according to some keyframes
        
        frames_count_total = self.raw_video_keys_forced.segment_h264(   forced_key_frames, 
                                                                        forced_key_frames_timestamps, 
                                                                        chunk_out_dir) 

        self.logger.info("Video has {} frames while in chunks we have {} frames".format(self.raw_video.load_total_frames(), frames_count_total))
        self.logger.info("Chunketization completed succesfully!.")
 
    
    def build_segment_composition(self):
        
        segments_data = {}
        self.logger.info("Logging segments structure in {}".format(self.segments_structure_out))
        for i, chunk in self.groups.iterrows():
            
            time_absolute_start = chunk[KST]
            time_absolute_end = chunk[KET]
            frame_absolute_start = chunk[KSF]
            frame_absolute_end = chunk[KEF]

            time_relative_start = 0.0 
            time_relative_end = time_absolute_end - time_absolute_start
            frame_relative_start = 0
            frame_relative_end = frame_absolute_end - frame_absolute_start
            
            self.logger.debug('SEGMENT {}: Relative. Time: {} to {}. Frame range {} - {}'.format(    i,
                                                                                                time_relative_start, 
                                                                                                time_relative_end, 
                                                                                                frame_relative_start, 
                                                                                                frame_relative_end))

            self.logger.debug('SEGMENT {}: Absolute. Time: {} to {}. Frame range {} - {}'.format(    i,
                                                                                                time_absolute_start,
                                                                                                time_absolute_end,
                                                                                                frame_absolute_start,
                                                                                                frame_absolute_end))
            segments_data[i] = {}
            segments_data[i][K_SSTA] = time_absolute_start
            segments_data[i][K_SETA] = time_absolute_end
            
            segments_data[i][K_SSTR] = time_relative_start
            segments_data[i][K_SETR] = time_relative_end
            
            segments_data[i][K_SSFA] = frame_absolute_start
            segments_data[i][K_SSFR] = frame_relative_start
            segments_data[i][K_SEFA] = frame_absolute_end
            segments_data[i][K_SEFR] = frame_relative_end 
        
        with open(self.segments_structure_out, 'w') as fout:
            pd_dataframe = pd.DataFrame(segments_data)
            pd_dataframe.to_json(fout)

        self.logger.info("Segment structure logging: done")



        
    


if __name__=="__main__":
   

    parser = argparse.ArgumentParser()
    parser.add_argument('--use_rl_policy', action='store_false', help='Use RL grouper policy')
    parser.add_argument("--video_configs", help="json file with the video configurations", type=str, required=True)
    parser.add_argument("--grouper_configs", help="json file with the grouper configurations", type=str, required=True)
    parser.add_argument("--raw_segments", help="directory in which the raw segments are gonna be stored: useful for augmentation", type=str, required=True)
    parser.add_argument("--rescaled_video_template", help="grouper usually computes the rescaled videos: template directory, {} for resolution", type=str, required=True)

    parser.add_argument("--logs_dir", help="logs directory", type=str, required=True)
    parser.add_argument("--figs_dir", help="if some graphs need to be computed, this is the directory in which they will be stored", type=str, required=True)
    parser.add_argument("--segments_structure_out",  help="Json file that describes a segment in terms of time and frames" , type=str, required=True)
    parser.add_argument("--specific_raw_crf", type=int, help="Strive to keep a certain quality for raw segments, default is 15", default=15)
    parser.add_argument("--verbose",  action="store_true", help="Enables logging level debug")

    args = parser.parse_args()
    grouper = Grouper(args)

    grouper.make_groups()
    grouper.chunketize_raw_segments()
    grouper.build_segment_composition()




