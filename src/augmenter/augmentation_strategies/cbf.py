from src.augmenter.augmentation_strategies.augmenter import Augmenter
from src.consts.augmenter_consts import *
from src.utils.video.level import Level
import numpy as np

class CBF(Augmenter):

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

    def augment(self, multiresolution_video):

        self.logger.info("Initializing augmentation")
        self.logger.info("First, launching encoding process")
        resolution_list  = []
        
        augmented_videos = self.ae.make_augmented_segments()
        augmented_videos_map = {}
        for video in augmented_videos:
            augmented_videos_map[video.video().load_resolution()] = video


        baseline_video_map = {}
        for video in self.rescaled_videos:
            baseline_video_map[video.video().load_resolution()] = video
            resolution_list.append(video.video().load_resolution())

        resolution_list = sorted(resolution_list, key=lambda x: int(x.split('x')[0]))
        chunks_no = len(self.rescaled_videos[0].load_segments())
        
        add_all_map = {}

        
        for video in self.rescaled_videos:
            for i, segment in enumerate(video.load_segments()):
                level = augmented_videos_map[video.video().load_resolution()].load_segments()[i]
                level = Level([level])
                    
                if i not in add_all_map.keys():
                    add_all_map[i] = []

                add_all_map[i].append(level)
    
        multires_video = multiresolution_video.add_levels(add_all_map)
        
        remove_map = {}

        self.logger.info("Chunks no is {}".format(chunks_no))

        vmaf_treshold = float(self.augmentation_module_args[K_AUGMENTER_VMAF_TH])
        
        self.logger.info("Threshold for cbf V is {} vmaf points".format(vmaf_treshold))

        for i, segment in enumerate(multires_video.segments()):
            
            closest_to_target_index = -1
            closest_to_target_delta = 100
            for j, l in reversed(list(enumerate(segment.levels))):
                segment_vmaf = np.mean(l.load_vmaf(i))
                delta = abs(vmaf_treshold - segment_vmaf)
                self.logger.info("Segment {}-th,  level {} at res {} has mean VMAF {}. Delta is {}".format(i, j, l.load_resolution(i), segment_vmaf, delta))
                if delta < closest_to_target_delta:
                    closest_to_target_delta = delta
                    closest_to_target_index = j

            self.logger.info("Closest to target {} for segment {} is track {} with vmaf {}".format(vmaf_treshold, i, closest_to_target_index, closest_to_target_delta))
            if i == 0 and closest_to_target_index == 0:
                closest_to_target_index = 1

            for j, l in reversed(list(enumerate(segment.levels))):
                if j > closest_to_target_index:
                    if i not in remove_map.keys():
                            remove_map[i] = []
                    remove_map[i].append(l)
                    
            
        multires_video = multires_video.remove_levels(remove_map)
        return multires_video







