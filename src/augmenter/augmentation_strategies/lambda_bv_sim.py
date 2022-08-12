from src.augmenter.augmentation_strategies.lambda_sim import LambdaSim
from src.consts.augmenter_consts import *
from src.utils.video.level import Level
import numpy as np
import os

class LambdaBVSim(LambdaSim):

    def __init__(   self, raw_video,
                    rescaled_videos, ss,
                    original_segments_dir,
                    augmented_dir_out,
                    augmentation_module_args,
                    splitting_module_args,
                    log_dir, figs_dir,
                    verbose=False):
    
        super().__init__(   raw_video,
                            rescaled_videos, ss,
                            original_segments_dir,
                            augmented_dir_out,
                            augmentation_module_args,
                            splitting_module_args,
                            log_dir, figs_dir,
                            verbose=False)

        vmaf_min = self.args[K_AUGMENTER_SIM_VMAF_MIN]
        vmaf_max = self.args[K_AUGMENTER_SIM_VMAF_MAX]  
        vmaf_step = self.args[K_AUGMENTER_SIM_VMAF_STEP]  

        perc_br_min = self.args[K_AUGMENTER_SIM_PERC_MIN]  
        perc_br_max = self.args[K_AUGMENTER_SIM_PERC_MAX]  
        perc_br_step = self.args[K_AUGMENTER_SIM_PERC_STEP]
        

        self.parameters_opt =[(None, None)]

        vmaf_range = np.arange(vmaf_min, vmaf_max, vmaf_step)
        np.append(vmaf_range, vmaf_max)
        bitrate_range = np.arange(perc_br_min, perc_br_max, perc_br_step)
        np.append(bitrate_range, perc_br_max)

        for v in vmaf_range:
            for b in bitrate_range:
                self.parameters_opt.append((v, b))
    
    
    def apply_winning(self, winning_parameters):
        
        self.logger.info("Winning params are {}".format(winning_parameters))
        self.segments = self.apply_params(winning_parameters, 1)
        self.start_segment += 1
        self.real_set.step(self.segments.get_simulation_data(start=0)) # sensitive

    
    def compare_rewards(self, rewards_map, lookahead):
        r = 0
        winning_params = None

        reward_no_aug = rewards_map[(None, None)][0]
        winning_params = (None, None)
        
        if self.start_segment == 0:
            self.logger.info("Initial segment: returning unaugmented winning param")
            return winning_params

        for params, (reward, mv) in rewards_map.items():
            augmented_bytes = mv.load_augmented_bytes(start=self.start_segment, end=self.start_segment + lookahead)
            if params == (None, None):
                self.logger.info("No augmentation reward {}, augmented bytes: {}".format(reward, augmented_bytes))
                continue
            self.logger.info("Params : {}, Reward: {}, Augmented Bytes: {}".format(params, reward, augmented_bytes))
            
            if augmented_bytes == 0:
                impro = 0
            else:
                impro = (reward - reward_no_aug)/augmented_bytes
            
            if impro > r:
                winning_params = params
                r = impro
        return winning_params



    def apply_params(self, param, lookahead):
        if param[0] == None and param[1] == None:
            return self.segments
        else:
        
            br_treshold = param[1]
            vmaf_treshold = param[0]

            self.logger.debug("Threshold for lambda V is {} vmaf points".format(vmaf_treshold))
            self.logger.debug("Threshold for lambda B is {} %".format(br_treshold))
            
            augmented_map = {}

            for video in self.rescaled_videos:

                self.logger.debug("Handling resolution {}".format(video.video().load_resolution()))
            
                mean_bitrate = video.video().load_bitrate()
                self.logger.debug("Mean bitrate is {}".format(mean_bitrate))
                max_bitrate_allowed = (mean_bitrate*br_treshold)/ 100.0 + mean_bitrate

                self.logger.debug("Max bitrate allowed is {}".format(max_bitrate_allowed))

                for iterr, segment in enumerate(video.load_segments()[self.start_segment:self.start_segment+lookahead]):
                    
                    i = iterr + self.start_segment

                    segment_vmaf = np.mean(segment.vmaf())
                    segment_bitrate = segment.video().load_bitrate()
                    self.logger.debug("Segment {}-th at resolution {} has mean VMAF {} and mean bitrate {}".format(i, video.video().load_resolution(), segment_vmaf, segment_bitrate))

                    if segment_bitrate > max_bitrate_allowed:
                        self.logger.debug("Segment {}-th at resolution {} needs maybe to be augmented".format(i, video.video().load_resolution()))
                    
                        try:
                            augment = False
                            lower_resolution_index = self.resolution_list.index(video.video().load_resolution()) - 1
                            if lower_resolution_index >= 0:
                                lower_resolution = self.resolution_list[lower_resolution_index]
                                lower_resolution_vmaf = np.mean(self.baseline_video_map[lower_resolution].load_segments()[i].vmaf())
                                self.logger.debug("Segment {}-th at lower resolution {} has mean VMAF {}".format(i, lower_resolution, lower_resolution_vmaf))
                                delta_vmaf = segment_vmaf - lower_resolution_vmaf
                                if delta_vmaf > vmaf_treshold:
                                    augment = True
                                    self.logger.debug("Delta vmaf is {} > {}. Marked for augmentation".format(delta_vmaf, vmaf_treshold))
                                else:
                                    self.logger.debug("Delta vmaf is {} < {}. Not marked for augmentation".format(delta_vmaf, vmaf_treshold))
                            else:
                                self.logger.debug("Lower resolution is not present. Marked for augmentation")
                                augment = True
                        
                            if augment:
                                level = self.augmented_videos_map[video.video().load_resolution()].load_segments()[i]
                                self.logger.debug("Augmented segment resolution is {}".format(level.video().load_resolution()))
                                self.logger.debug("Augmented segment vmaf is {}".format(np.mean(level.vmaf())))
                                self.logger.debug("Augmented segment bitrate is {}".format(level.video().load_bitrate()))
                                level = Level([level])
                    
                                if i not in augmented_map.keys():
                                    augmented_map[i] = []
                                augmented_map[i].append(level)
                    
                        except:
                            self.logger.debug("Augmented chunk {} at resolution {} is not available".format(i, video.video().load_resolution()))
            multires_video = self.segments.add_levels(augmented_map)
            return multires_video







