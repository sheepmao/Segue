import pandas as pd
from abc import ABC, abstractmethod
import numpy as np
import math
from datetime import datetime
import os, json
from src.utils.logging.logging_segue import create_logger
import importlib.machinery
from src.consts.augmenter_consts import *
from src.consts.reward_consts import *
LOOK_PAST_ALL = -1
from src.simulator.sim_state import createSimStateSet
from src.consts.simulation_configs_consts import *

class LambdaSim(ABC):
    
    def __init__(   self, raw_video,
                    rescaled_videos, ss,
                    original_segments_dir,
                    augmented_dir_out,
                    augmentation_module_args,
                    splitting_module_args,
                    log_dir, figs_dir,
                    verbose=False):
 
        
        self.log_dir = log_dir
        self.figs_dir = figs_dir
        self.verbose = verbose
        log_file = os.path.join(log_dir, 'Lambda_Sim.log')
        self.logger = create_logger('Lambda Sim Augmenter', log_file, verbose=verbose)
        self.raw_video = raw_video
        
        self.start_segment = 0

        augmenter_encoding_name =  augmentation_module_args[K_AUGMENTER_ENCODING_NAME]
        augmenter_encoding_module = augmentation_module_args[K_AUGMENTER_ENCODING_MODULE].replace('/','.').replace('.py', '')
        augmenter_encoding_class = augmentation_module_args[K_AUGMENTER_ENCODING_CLASS]

        self.logger.info("Augmenter encoding name = {}".format(augmenter_encoding_name))
        self.logger.info("Augmenter encoding module = {}".format(augmenter_encoding_module))
        self.logger.info("Augmenter encoding class = {}".format(augmenter_encoding_class))

        try:
            augmenter_encoding_args = augmentation_module_args[K_AUGMENTER_ENCODING_ARGS]
            self.logger.debug("Augmenter encoding module args = {}".format(augmenter_encoding_args))
        except:
            augmenter_encoding_args = {}
            self.logger.warning("No splitting module argument has been passed")
        
        try:
            self.logger.debug("Retrieving augmenter encoding policy")
            AEPolicy = getattr(importlib.import_module(augmenter_encoding_module), augmenter_encoding_class)
            self.logger.info("Augmenter policy retrieved correctly")
        except:
            self.logger.error("{} doesn't contain class name {}, or some errors are present in module".format(augmenter_encoding_module,
                                                                                                              augmenter_encoding_class))
            self.logger.exception("message") 
            sys.exit(-1)
        

        try:
            self.logger.debug("Instantiating augmenter encoding policy")
            augmented_dir_out = os.path.join(augmented_dir_out, augmenter_encoding_name, '{}')
            self.ae = AEPolicy(   raw_video,
                                  rescaled_videos, ss,
                                  original_segments_dir,
                                  augmented_dir_out,
                                  splitting_module_args, augmenter_encoding_args,
                                  log_dir, figs_dir, verbose=verbose)

            self.logger.info("Augmenter encoding policy instantiated correctly")
        except:
            self.logger.error("Something went wrong in the instantiation of the class")
            self.logger.exception("message")
            sys.exit(-1)
        
        self.rescaled_videos = rescaled_videos
        self.args = augmentation_module_args

        
        self.logger.debug("Creating grouper simulation optimizer")
        
        sim_configs = self.args[K_AUGMENTER_SIM_CONFIGS]
        
        assert os.path.exists(sim_configs)
        with open(sim_configs, 'r') as fin:
                sim_data = json.load(fin)

        abr_module = sim_data[SIM_CONFIGS_ABR_MODULE]
        assert os.path.exists(abr_module)
        self.logger.info("Abr module is : {}".format(abr_module))
            
        try:
            abr_module_parameters = sim_data[SIM_CONFIGS_ABR_MODULE_PARAMETERS]
            self.logger.info("Abr module parameters is {}".format(abr_module_parameters))

        except:
            abr_module_parameters = {}
            

        qoe_configs_file = sim_data[SIM_CONFIGS_REWARD_CONFIGS]
 
        assert os.path.exists(qoe_configs_file)
        with open(qoe_configs_file, 'r') as fin:
            qoe_data = json.load(fin)

        qoe_module = qoe_data[REWARD_MODULE]
        assert os.path.exists(qoe_module)
        qoe_class_name = qoe_data[REWARD_CLASS]

        self.logger.info("Qoe module = {}, Class name = {}".format(qoe_module, qoe_class_name))

        try:
            qoe_parameters = qoe_data[REWARD_PARAMETERS]
            self.logger.info("Reward parameters are {}".format(qoe_parameters))
        except:
            qoe_parameters = {}
        
        self.look_ahead = self.args[K_AUGMENTER_SIM_OPT_LOOKAHEAD]

        try:
            self.reward_look_future = self.args[K_AUGMENTER_SIM_REWARD_LOOK_FUTURE]
            assert self.reward_look_future >= 0
            self.logger.info("Look future is {}".format(self.reward_look_future))
        except:
            self.reward_look_future = 0
            
        try:
            self.reward_look_past = self.args[K_AUGMENTER_SIM_REWARD_LOOK_PAST]
            assert self.reward_look_past >= -1
            self.logger.info("Look past is {}".format(self.reward_look_past))
        except:
            self.reward_look_past = -1
            
        
        traces_set = sim_data[SIM_CONFIGS_TRACES_PATH]
        assert os.path.exists(traces_set)
        self.logger.info("Traces set is {}".format(traces_set))
            
        self.real_set, self.reward, self.abr_module = createSimStateSet(  abr_module, qoe_module, 
                                                                                qoe_class_name, qoe_parameters, 
                                                                                traces_set, self.raw_video.video().load_fps())

        assert len(self.real_set.ss_set) > 0
        self.logger.debug("Simulation set contains {} traces".format(len(self.real_set.ss_set)))
        
        ## Instantiate Reward module

        assert self.reward is not None
        
        self.logger.debug("Computing with a look ahead of {}".format(self.look_ahead))
        self.logger.debug("Computing with a look at the future of  {}".format(self.reward_look_future))
        self.logger.debug("Computing with a look past of {} (if negative, all)".format(self.reward_look_past))

        self.parameters_opt = None


    def augment(self, multiresolution_video):

        self.logger.info("Initializing augmentation")
        self.logger.info("First, launching encoding process")
        self.augmented_videos = self.ae.make_augmented_segments()

        self.augmented_videos_map = {}
        self.resolution_list  = []
        
        for video in self.augmented_videos:
            self.augmented_videos_map[video.video().load_resolution()] = video
        
        self.baseline_video_map = {}
        for video in self.rescaled_videos:
            self.baseline_video_map[video.video().load_resolution()] = video
            self.resolution_list.append(video.video().load_resolution())

        self.resolution_list = sorted(self.resolution_list, key=lambda x: int(x.split('x')[0]))
        self.chunks_no = len(self.rescaled_videos[0].load_segments())

        multiresolution_video = self.compute_suboptimal(multiresolution_video)
        return multiresolution_video
    

    def param_reward(self, augmented_segments, s_lookahead):
        
        sim_ss = self.real_set.copy()
        init_pos = sim_ss.get_chunk_index()
        sim_steps = s_lookahead
        
        self.logger.debug("Retrieving simulation data from {} and {}".format(0, init_pos + sim_steps + self.reward_look_future))
        if self.reward_look_past > 0:
            start_segment = max(0, init_pos - self.reward_look_past)
        else:
            start_segment = 0
        
        
        sim_data = augmented_segments.get_simulation_data(start=0, end=-1)
        end_segment = min(init_pos + sim_steps + self.reward_look_future, len(sim_data))
        r = sim_ss.step_n(sim_data, sim_steps + self.reward_look_future, start_segment, end_segment)
        
        return r
    
   
    @abstractmethod
    def apply_params(self, param):
        pass

    @abstractmethod
    def apply_winning(self, winning_parameters, rewards_map):
        pass

    @abstractmethod
    def compare_rewards(self, rewards_map):
        pass

    def effective_lookahead(self):
        return self.segments.load_effective_lookahead(self.start_segment, self.look_ahead)
 
    def initialize_reward(self):
        return -1*float(math.inf)

    def compute_suboptimal(self, multiresolution_videos):
        
        self.logger.info("Starting suboptimal optimization")
        self.segments = multiresolution_videos

        assert self.parameters_opt is not None

        if self.start_segment != 0:
            self.logger.debug("Already computed suboptimal")
            return
        while True:
            
            self.winning_reward = self.initialize_reward()
            self.winning_parameters_opt = None
            s_lookahead = self.effective_lookahead()
            
            if s_lookahead == 0:
                break
            
            rewards_map = {}

            for param in self.parameters_opt:
                self.logger.debug("Checking parameters={}".format(param))
                augmented_segments = self.apply_params(param, s_lookahead)
                reward = self.param_reward(augmented_segments, s_lookahead)
                rewards_map[param] = (reward, augmented_segments)
            
            self.winning_parameters_opt = self.compare_rewards(rewards_map, s_lookahead)

            assert self.winning_parameters_opt != None
            self.apply_winning(self.winning_parameters_opt)
        return self.segments
