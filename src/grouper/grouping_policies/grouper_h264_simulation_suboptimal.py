from src.utils.video_factory import Video, FullVideo, EXTENSION
from src.simulator.sim_state import createSimStateSet
from src.utils.video.multilevel_video_factory import MultilevelVideoFactory

import pandas as pd
import tempfile, os, sys
from src.consts.keys_consts import *

from src.consts.grouper_configs_consts import *
from src.consts.video_configs_consts import *
from src.consts.reward_consts import *
from src.consts.simulation_configs_consts import *

from src.grouper.grouping_policies.grouper_policy import GrouperPolicy
from src.grouper.grouping_policies.grouper_optimizer.grouper_simulation_optimizer import GrouperSimulationOptimizer

from shutil import copyfile
from pathlib import Path
import json

M_IN_K = 1000.0
B_IN_BYTES = 8

class SimulationOptimizedGrouperPolicy(GrouperPolicy):
    def __init__(   self, 
                    grouper_data,
                    video_data,
                    video_obj,
                    rescaled_dir_template,
                    verbose,
                    logs_dir,
                    figs_dir):
        
        super().__init__(   grouper_data,
                            video_data,
                            video_obj,
                            rescaled_dir_template,
                            verbose,
                            logs_dir,
                            figs_dir)
        
        try:

            self.logger.info("Simulation optimizer grouper created")
            gp = grouper_data[K_PARAMETERS_GROUPER]

            self.bitrate_ladders_file = gp[K_BITRATE_LADDERS_GROUPER]
            self.logger.info("Bitrate ladders retrieved at {}".format(self.bitrate_ladders_file))
            
            
            self.gop_seconds = float(gp[K_GOP_SECONDS_GROUPER])
            self.logger.info("Desired gop : {}".format(self.gop_seconds))
            
            
            self.opt_lookahead = int(gp[K_OPTIMIZATION_LOOKAHEAD_GROUPER])
            self.logger.info("Lookahead is : {}".format(self.opt_lookahead)) 

            sim_configs = gp[K_SIMULATION_CONFIGS]
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

            try:
                self.reward_look_future = gp[K_SIMULATION_REWARD_LOOK_FUTURE_GROUPER]
                assert self.reward_look_future >= 0
                self.logger.info("Look future is {}".format(self.reward_look_future))
            except:
                self.reward_look_future = 0
            
            try:
                self.bytes_option = gp[K_BYTES_MODE_GROUPER]
                self.logger.debug("Bytes optioon selected = {}".format(BYTES_OPT[0]))
            except:
                self.logger.debug("Bytes mode option not found.")
                self.logger.debug("Default byte mode = {}".format(BYTES_OPT[1]))
                self.bytes_option = BYTES_OPT[1]

            try:
                self.reward_look_past = gp[K_SIMULATION_REWARD_LOOK_PAST_GROUPER]
                assert self.reward_look_past >= -1
                self.logger.info("Look past is {}".format(self.reward_look_past))
            except:
                self.reward_look_past = -1
            
            self.vmaf_model = gp[K_SIMULATION_REWARD_VMAF_MODEL_GROUPER]

            traces_set = sim_data[SIM_CONFIGS_TRACES_PATH]
            assert os.path.exists(traces_set)
            self.logger.info("Traces set is {}".format(traces_set))
            
            self.fragments_dir_template = gp[K_OPTIMIZATION_FRAGMENTS_DIR_TEMPLATE_GROUPER].format(self.video_data[K_NAME_VIDEO], '{}')

            self.real_ss, self.reward_module, self.abr_module = createSimStateSet(  abr_module, qoe_module, 
                                                                                    qoe_class_name, qoe_parameters, 
                                                                                    traces_set, self.video_obj.load_fps())

        
        except:
            self.logger.error("Something went wrong in parsing the parameters")
            self.logger.exception("message")
            sys.exit(-1)


    def load_expected_keyframes(self):

        if not self.segments_keys_indexes or not self.segments_keys_timestamps:
            self.logger.debug("Keyframes not yet loaded --> run make groups before")
            sys.exit(-1)

    def make_groups(self):
        

        self.logger.info("Starting grouping routine. Method: simulation optimizer")
        

        if not K_OPTIMIZATION_FRAGMENTS_DIR_TEMPLATE_GROUPER in self.grouper_data[K_PARAMETERS_GROUPER].keys():
            self.logger.error("Fragments dir must be specified")
            sys.exit(-1)

        resolutions = self.video_data[K_RESOLUTIONS].split()
        template_res = resolutions[0]
        self.logger.debug("Handling template resolution {}".format(template_res))
        
        self.logger.info("Creating GOP rescaling method")
        method = self.create_gop_rescaling_method()
        self.logger.debug("GOP rescaling method --> {}".format(method))
        
        file_out = os.path.join(self.rescaled_dir_template.format(template_res), 'unfragmented.{}'.format(EXTENSION))
        self.logger.debug("Rescaled output  stored at {}".format(file_out))
        
        cache_file = self.get_cache_file(template_res)
        if cache_file:
            self.logger.debug("Cache file selected: {}".format(cache_file))

        self.logger.info("Starting rescaling of template resolution")
        video_template_resolution = self.video_obj.rescale_at_resolution(file_out, template_res, 'h264', self.bitrate_ladders_file,
                                                                        method, cache=self.cache, cache_file=cache_file)
         
        self.logger.info("Rescaling of template resolution computed succesfully")
        

        self.segments_keys_indexes, self.segments_keys_timestamps = video_template_resolution.load_keyframes()
        self.create_forced_keys_rescaling_method()
        self.logger.debug("Forcing other resolution with: ")
        self.logger.debug("Keyframes indexes: {}".format(self.segments_keys_indexes))
        self.logger.debug("Keyframes timestamps: {}".format(self.segments_keys_timestamps))
        
        method = self.create_forced_keys_rescaling_method()
        self.logger.debug("Forced keys rescaling method --> {}".format(method))

        rescaled_videos = [ FullVideo(video_template_resolution) ]

        for resolution in resolutions[1:]:
            file_out = os.path.join(self.rescaled_dir_template.format(resolution), 'unfragmented.{}'.format(EXTENSION))
            self.logger.debug("Rescaled output  stored at {}".format(file_out))
            
            cache_file = self.get_cache_file(resolution)
            if cache_file:
                self.logger.debug("Cache file selected: {}".format(cache_file))

            self.logger.info("Starting rescaling of template resolution")
            video = self.video_obj.rescale_at_resolution(   file_out, resolution, 'h264', self.bitrate_ladders_file,
                                                            method, cache=self.cache, cache_file=cache_file)
            rescaled_videos.append(FullVideo(video))
     
        
        self.logger.info("Rescaling operations computed succesfully.")
        self.logger.info("Handling VMAF and FFPROBE calculation.")
        
        reference = FullVideo(self.video_obj)
        for video, res in zip(rescaled_videos, resolutions):
            vmaf_file_out = os.path.join(self.rescaled_dir_template.format(res), 'unfragmented.{}'.format(self.vmaf_model))
            self.logger.debug("Storing VMAF in {}".format(vmaf_file_out))
            
            cache_file = self.get_cache_file(res)
            if cache_file:
                f1 = Path(cache_file)
                f2 = f1.with_suffix('')
                cache_file = f2.with_suffix('.{}'.format(self.vmaf_model))
                self.logger.debug("Storing vmaf cache file in {}".format(cache_file))
            
            video.load_vmaf(reference, vmaf_file_out, self.vmaf_model, cache=self.cache, cache_file=cache_file)
            self.logger.info("VMAF of resolution {} computed succesfully".format(res))
            
            if self.bytes_option == BYTES_OPT[0]:
                ffprobe_file_out = os.path.join(self.rescaled_dir_template.format(res), 'unfragmented.ffprobe')
                self.logger.debug("Storing FFprobe in {}".format(ffprobe_file_out))
                
                cache_file = self.get_cache_file(res)
                if cache_file:
                    f1 = Path(cache_file)
                    f2 = f1.with_suffix('')
                    cache_file = f2.with_suffix('.ffprobe')
                    self.logger.debug("Storing ffprobe cache file in {}".format(cache_file))
                
                video.load_ffprobe(ffprobe_file_out, cache=self.cache, cache_file=cache_file)
                self.logger.info("FFPROBE of resolution {} computed succesfully".format(res))

        self.logger.info("Vmaf operation computed succesfully")
        self.logger.info("Handling segmentation operations")
           
        
        for video, res in zip(rescaled_videos, resolutions):
            self.logger.debug("Handling resolution {}".format(res))
            fragments_dir = self.fragments_dir_template.format(res)
            self.logger.debug("Fragments will be stored in {}".format(fragments_dir))
            
            video.segment_h264(self.segments_keys_indexes, self.segments_keys_timestamps, fragments_dir)
            self.logger.info("Fragmentation computed correctly for resolution {}".format(res))
            self.logger.info("Assigning VMAF to fragments for resolution {}".format(res))
            video.assign_vmaf_to_segments(os.path.join(fragments_dir, 'vmaf'))
            self.logger.info("Vmaf assigned correctly to segment for resolution {}".format(res))
            if self.bytes_option == BYTES_OPT[0]:
                video.assign_ffprobe_to_segments(os.path.join(fragments_dir, 'ffprobe'))
                self.logger.info("FFPROBE assigned correctly to segment for resolution {}".format(res))

        self.logger.debug("Creating fragments objects for optimization")
        factory = MultilevelVideoFactory(self.logger, OPT=self.bytes_option, enable_logging=self.verbose)
        multires_fragments = factory.multilevel_video_from_full_videos(  rescaled_videos )
        self.logger.debug("Fragments objects created correctly")


        
        log_file_optimizer = os.path.join(self.logs_dir, 'sim_optimizer.logs')
        self.logger.debug("Logging optimization output to {}".format(log_file_optimizer))
        
        self.logger.info("Creating simulation optimizer")

        grouper_simulation_optimizer = GrouperSimulationOptimizer(  self.opt_lookahead, multires_fragments, 'Grouper Sim Optimizer', 
                                                                    log_file_optimizer, self.real_ss, self.reward_module, 
                                                                    look_past=self.reward_look_past, look_future=self.reward_look_future,
                                                                    verbose=self.verbose)
        self.logger.info("Simulation optimizer object created succesfully")

        
        self.logger.info("Starting simulation optimization")
        grouper_simulation_optimizer.compute_suboptimal()
        self.logger.info("Simulation optimization computed succesfully")


        self.logger.debug("Retrieving keyframes boundaries")
        self.segments_keys_indexes, self.segments_keys_timestamps = grouper_simulation_optimizer.return_suboptimal()
        
        scene_df = self.format_dataframe_segments()
        return scene_df

