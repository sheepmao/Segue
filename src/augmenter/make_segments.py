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
from src.consts.splitter_consts import *
from src.consts.augmenter_consts import *
from src.utils.video_factory import Video, FullVideo, EXTENSION

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


class SegmentsHandler:
    def __init__(self, args):
        ## parameter check

        assert os.path.exists(args.video_configs), "Video configuration file doesn't exist"
        assert os.path.exists(args.segments_handler_configs), "Grouper configuration file doesn't exist"
        assert os.path.exists(args.raw_segments_in), "Video RAW segments do not exists"
        assert os.path.exists(args.segments_structure_in), "Video RAW segments do not exists"

        self.verbose = args.verbose
        
        self.logs_dir = args.logs_dir
        if os.path.exists(args.logs_dir):
            empty(args.logs_dir)
        
        pmkdir(args.logs_dir)
        log_file = os.path.join(args.logs_dir, 'make_segments.log')
        self.logger = create_logger('Rescaler-Augmenter: Main', log_file, verbose=args.verbose)
        
        self.logger.info("Rescaler-Augmenter module initialized")
        self.logger.info("Logs file stored in {}".format(log_file))
        

        ## Outputs:

        self.csv_std_segments = args.csv_std_segments
        self.logger.info("CSV of standard segments will be stored in {}".format(self.csv_std_segments))
        pmkdir(os.path.dirname(self.csv_std_segments))
        
        if args.csv_aug_segments:
            self.csv_aug_segments = args.csv_aug_segments
            pmkdir(os.path.dirname(self.csv_aug_segments))
            self.logger.info("CSV of augmented segments will be stored in {}".format(self.csv_aug_segments))


        ## creation of figsdir
        pmkdir(args.figs_dir)
        self.figs_dir = args.figs_dir
        self.logger.info("Figs will be stored in {}".format(self.figs_dir))
        
        self.raw_segments_in = args.raw_segments_in
        self.logger.info("Accounted raw segments stored = {}".format(self.raw_segments_in))

        self.video_data = read_configs(args.video_configs)
        self.logger.info("Accounted video data stored = {}".format(args.video_configs))
        self.logger.debug("Accounted video data {}".format(self.video_data))

        self.segments_handler_data = read_configs(args.segments_handler_configs)
        self.logger.info("Accounted augmenter data stored = {}".format(self.segments_handler_data))
        self.logger.debug("Accounted augmenter data {}".format(self.segments_handler_data))

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
        self.resolutions = self.video_data[K_RESOLUTIONS].split()
        self.logger.debug("Original video resolution = {}".format(self.resolutions))
        
        # $(RESULT_DIR)/$(VIDEO_FOLDER)/$(GROUPING_POLICY_FOLDER)/video/{}/unfragmented.{}
        self.rescaled_video_template = args.rescaled_video_template.format('{}', EXTENSION) 
        self.logger.debug("Rescaled video template is {}".format(self.rescaled_video_template))

        self.multires_video = None

        self.rescaled_videos = []
        for res in self.resolutions:
            video_path = self.rescaled_video_template.format(res)
            self.logger.debug("Looking for {}".format(video_path))
            assert os.path.exists(video_path)
            self.rescaled_videos.append(FullVideo(Video(video_path, self.logs_dir, verbose=self.verbose)))
            self.logger.info("Video {} found".format(video_path))
        
        splitting_module = self.segments_handler_data[K_SPLITTING_MODULE].replace('/','.').replace('.py', '')
        splitting_class = self.segments_handler_data[K_SPLITTING_CLASS]
        self.logger.info("Splitting module = {}".format(splitting_module))
        self.logger.info("Splitting class = {}".format(splitting_class))

        try:
            splitting_module_args = self.segments_handler_data[K_SPLITTING_MODULE_ARGS]
            self.logger.debug("Splitting module args = {}".format(splitting_module_args))
        except:
            splitting_module_args = {}
            self.logger.warning("No splitting module argument has been passed")
        
        try:
            self.logger.debug("Retrieving splitting policy")
            SplittingPolicy = getattr(importlib.import_module(splitting_module), splitting_class)
            self.logger.info("Splitting policy retrieved correctly")
        except:
            self.logger.error("{} doesn't contain class name {}, or some errors are present in module".format(splitting_module, splitting_class))
            self.logger.exception("message") 
            sys.exit(-1)
        

        try:
            self.logger.debug("Instantiating splitting policy")
            self.splitting_policy = SplittingPolicy(    self.raw_video,
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


        try:
            augmenter_module = self.segments_handler_data[K_AUGMENTER_MODULE_AUGMENTER].replace('/','.').replace('.py', '')
            augmenter_class = self.segments_handler_data[K_AUGMENTER_CLASS_AUGMENTER]
            
            self.logger.info("Augmentation module = {}".format(augmenter_module))
            self.logger.info("Augmentation class = {}".format(augmenter_class))
            assert self.csv_aug_segments
            try:
                augmenter_module_args = self.segments_handler_data[K_AUGMENTER_MODULE_ARGS]
                self.logger.debug("Augmenter module args = {}".format(augmenter_module_args))
            except:
                augmenter_module_args = {}
                self.logger.warning("No augmenter module argument has been passed")
        
            try:
                AugmenterPolicy = getattr(importlib.import_module(augmenter_module), augmenter_class)
            except:
                self.logger.error("{} doesn't contain class name {}, or some errors are present in module".format(augmenter_module, augmenter_class))
                self.logger.exception("message") 
                sys.exit(-1)
            

            ## Instantiating the class
            try:
                self.augmenter_policy = AugmenterPolicy(    self.raw_video,
                                                            self.rescaled_videos,
                                                            self.segments_structure_in,
                                                            self.raw_segments_in,
                                                            args.augmented_segments_out_root,
                                                            augmenter_module_args,
                                                            splitting_module_args,
                                                            args.logs_dir, args.figs_dir, verbose=args.verbose)                                                
            except:
                self.logger.error("Something went wrong in the instantiation of the class")
                self.logger.exception("message")
                sys.exit(-1)
        except:
            self.augmenter_policy = None
            self.logger.info("No augmentation policy selected. Processing video unaugmented")
            #self.logger.exception("message") 

    def compute_splitting(self):
        self.logger.info("Starting video splitting and computation")
        self.splitting_policy.split_and_compute()
        self.logger.info("Video splitting computed succesfully")
        fact = MultilevelVideoFactory(self.logger, enable_logging=self.verbose)
        self.multires_video = fact.multilevel_video_from_full_videos(self.rescaled_videos)

    def compute_augmentation(self):
        
        assert self.multires_video

        if self.augmenter_policy:
            self.logger.info("Starting video splitting and computation")
            self.multires_video = self.augmenter_policy.augment(self.multires_video)
        else:
            self.logger.info("augmentation policy is None")

    def log_results(self):
        
        std_dataframe = self.multires_video.load_std_dataframe()
        aug_dataframe = self.multires_video.load_aug_dataframe()
        
        std_dataframe.to_csv(self.csv_std_segments)
        if aug_dataframe is not None:
            aug_dataframe.to_csv(self.csv_aug_segments)


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_configs', help='video configurations', required=True)
    parser.add_argument('--segments_handler_configs', help='configurations of the rescaler and aug module', required=True)
    parser.add_argument('--raw_segments_in', help='raw segments of the video', required=True)
    parser.add_argument('--augmented_segments_out_root', help='where to store augmented segments', required=True)
    parser.add_argument('--segments_structure_in', help='indicator for the splitting', required=True)
    parser.add_argument('--logs_dir', help='where the logs are gonna be stored', required=True)
    parser.add_argument('--figs_dir', help='where the figs are gonna be stored', required=True)
    parser.add_argument('--csv_std_segments', help='output: recap csv for segments std', required=True)
    parser.add_argument('--csv_aug_segments', help='output: recap csv for segments aug')
    parser.add_argument('--rescaled_video_template', help='rescaled video template', required=True)
    parser.add_argument('--verbose', action="store_true")
    
    args = parser.parse_args()
    ra = SegmentsHandler(args)
    ra.compute_splitting()
    ra.compute_augmentation()
    ra.log_results()
