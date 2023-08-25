import re, sys, logging, argparse, traceback, ntpath
import matplotlib.pyplot as plt
import json, os, glob, subprocess
import numpy as np
import pandas as pd
import importlib.machinery
from pprint import pformat
from src.utils.logging.logging_segue import create_logger
from src.utils.video.multilevel_video_factory import MultilevelVideoFactory
from src.consts.video_configs_consts import *
from src.consts.manifest_representation_consts import *
from src.consts.splitter_consts import *
from src.consts.augmenter_consts import *
from src.utils.video.level import Level
from src.utils.video_factory import Video, FullVideo, EXTENSION
from src.augmenter.splitting_strategies.h264_splitter import H264Splitter

resolutions = ["640x360", "854x480", "960x540", "1024x576", "1280x720", "1920x1080", "3840x2160"]
video_extension = "mp4"
video_codec = "h264"
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

class SimulationFileHandler:
    def __init__(self, args):

        ## Inputs:
        self.logs_dir = args.logs_dir
        if os.path.exists(args.logs_dir):
            empty(args.logs_dir)
        pmkdir(args.logs_dir)
        
        log_file = os.path.join(args.logs_dir, 'make_simulation_file.log')
        self.logger = create_logger('Make Simulation File: Main', log_file, verbose=args.verbose)
        
        self.logger.info("Simulation file handler module initialized")
        self.logger.info("Logs file stored in {}".format(log_file))
        
        ## Outputs:
        self.simulation_file_out = args.simulation_file_out
        self.logger.info("Simulation file stored in {}".format(self.simulation_file_out))
        pmkdir(os.path.dirname(self.simulation_file_out))
        
        self.csv_std_segments_in = pd.read_csv(args.csv_std_segments_in, keep_default_na=False)
        self.logger.info("Reference segments csv in: {}".format(args.csv_std_segments_in))


        self.csv_std_segments_out = args.csv_std_segments_out
        self.logger.info("CSV of standard segments will be stored in {}".format(self.csv_std_segments_out))
        pmkdir(os.path.dirname(self.csv_std_segments_out))
        

        

        self.video_data = read_configs(args.video_configs)
        self.logger.info("Accounted video data stored = {}".format(args.video_configs))
        self.logger.debug("Accounted video data {}".format(self.video_data))

        self.segments_handler_data = read_configs(args.segments_handler_configs) # ex: configs/augmenter/bb_optimized/sigma_bv_sim_bb_h264.json
        self.logger.info("Accounted augmenter data stored = {}".format(self.segments_handler_data))
        self.logger.debug("Accounted augmenter data {}".format(self.segments_handler_data))

        
        self.simulation_file_data = read_configs(args.sim_file_configs) # ex: configs/simulation_file/simulation_file_vmaf_hdtv.json
        self.logger.info("Accounted simulation file data stored = {}".format(args.sim_file_configs))
        self.logger.debug("Accounted simulation file data {}".format(self.simulation_file_data))

        
        self.segments_structure_in = read_configs(args.segments_structure_in)
        self.logger.info("Accounted segments boundaries stored = {}".format(args.segments_structure_in))
       
        video_original_path = self.video_data[K_VIDEO_PATH]
        assert os.path.exists(video_original_path), "Original video does not exists"
        
        self.logger.debug("Creating raw video from {}".format(video_original_path))
        self.raw_video  = FullVideo(Video(video_original_path, self.logs_dir, verbose=self.verbose))
        
        self.logger.info("Raw video from {} created succesfully".format(video_original_path))
        self.logger.debug("Video {} has a total of {} frames for {} fps".format(self.raw_video.video().video_path(),
                                                                                self.raw_video.video().load_total_frames(),
                                                                                self.raw_video.video().load_fps()))
        #self.resolutions = self.video_data[K_RESOLUTIONS].split()
        self.resolutions = resolutions
        self.logger.debug("Original video resolution = {}".format(self.resolutions))
        

        self.rescaled_video_template = args.rescaled_video_template # ex: $(RESULT_DIR)/$(VIDEO_FOLDER)/$(GROUPING_POLICY_FOLDER)/video/{}/unfragmented.mp4
        self.logger.debug("Rescaled video template is {}".format(self.rescaled_video_template))

        self.multires_video = None

        self.rescaled_videos = []
        for res in self.resolutions:
            video_path = self.rescaled_video_template.format(res)
            self.logger.debug("Looking for {}".format(video_path))
            assert os.path.exists(video_path), video_path
            self.rescaled_videos.append(FullVideo(Video(video_path, self.logs_dir, verbose=self.verbose)))
            self.logger.info("Video {} found".format(video_path))
        
        



        try:
            splitting_module_args = self.simulation_file_data[K_SPLITTING_MODULE_ARGS]
            self.logger.debug("Splitting module args = {}".format(splitting_module_args))
        except:
            splitting_module_args = {}
            self.logger.warning("No splitting module argument has been passed")
        
        
        SplittingPolicy = H264Splitter()
        try:
            self.logger.debug("Instantiating splitting policy")
            self.splitting_policy_std = H264Splitter(   self.raw_video,
                                                           self.rescaled_videos,
                                                           os.path.dirname(self.rescaled_video_template),
                                                           self.segments_structure_in,
                                                           splitting_module_args,
                                                           args.verbose,
                                                           args.logs_dir,
                                                           args.figs_dir)

            self.logger.info("Splitting policy instantiated correctly")
        except:
            self.logger.error("Something went wrong in the instantiation of the class")
            self.logger.exception("message")
            sys.exit(-1)





    def compute_splitting(self):
        self.logger.info("Starting video splitting and computation: std segments")
        self.splitting_policy_std.split_and_compute()
        self.logger.info("Video splitting computed succesfully")
        fact = MultilevelVideoFactory(self.logger, enable_logging=self.verbose)
        self.multires_video = fact.multilevel_video_from_full_videos(self.rescaled_videos)
        
        # check if there have been some removal #
        
        remove_map = {}
        self.logger.info("Checking if std segments present removal")
        
        for i, row in self.csv_std_segments_in.iterrows():
            for res in self.resolutions:
                if BITRATE_CSV_STD.format(res) not in row.keys() or row[BITRATE_CSV_STD.format(res)] == '':
                    if i not in remove_map.keys():
                        remove_map[i] = []
                    remove_map[i].append(self.multires_video.get_std_level(res, i))

        self.multires_video = self.multires_video.remove_levels(remove_map)
        if self.splitting_policy_aug:
            self.logger.info("Starting video splitting and computation: aug segments")
            self.splitting_policy_aug.split_and_compute()



    def log_results(self):
        
        std_dataframe = self.multires_video.load_std_dataframe()
        sim_data = self.multires_video.get_simulation_data()
        std_dataframe.to_csv(self.csv_std_segments_out)

        
        with open(self.simulation_file_out, 'w') as fout:
            json.dump(sim_data, fout)


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_configs', help='video configurations', required=True)
    parser.add_argument('--segments_handler_configs', help='configurations of the rescaler and aug module', required=True)
    parser.add_argument('--sim_file_configs', help='configurations of the rescaler and aug module', required=True)
    parser.add_argument('--segments_structure_in', help='indicator for the splitting', required=True)
    parser.add_argument('--logs_dir', help='where the logs are gonna be stored', required=True)
    parser.add_argument('--figs_dir', help='where the figs are gonna be stored', required=True)
    parser.add_argument('--simulation_file_out', help='output: json file for the simulation', required=True)
    parser.add_argument('--csv_std_segments_in', help='output: recap csv for segments std', required=True)
    parser.add_argument('--csv_aug_segments_in', help='output: recap csv for segments aug')
    parser.add_argument('--csv_std_segments_out', help='output: recap csv for segments std', required=True)
    parser.add_argument('--csv_aug_segments_out', help='output: recap csv for segments aug')
    parser.add_argument('--rescaled_video_template', help='rescaled video template', required=True)
    parser.add_argument('--augmented_video_template', help='rescaled video template', required=True)
    parser.add_argument('--verbose', action="store_true")
    
    args = parser.parse_args()
    # ex: RESCALED_VIDEO_TEMPLATE = $(RESULT_DIR)/$(VIDEO_FOLDER)/$(GROUPING_POLICY_FOLDER)/video/{}/unfragmented.{}
    args.rescaled_video_template = args.rescaled_video_template.format('{}', EXTENSION)
    ra = SimulationFileHandler(args)
    ra.compute_splitting()
    ra.log_results()