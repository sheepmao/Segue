from src.augmenter.augmentation_strategies.augmenter import Augmenter
from src.consts.augmenter_consts import *
from src.utils.video.level import Level
import numpy as np

class BetaVA(Augmenter):

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
        
        self.logger.info("Threshold for beta V is {} vmaf points".format(vmaf_treshold))

        for i, segment in enumerate(multires_video.segments()):
            for j, l in reversed(list(enumerate(segment.levels))):

                segment_vmaf = np.mean(l.load_vmaf(i))
                self.logger.info("Segment {}-th,  level {} at res {} has mean VMAF {}".format(i, j, l.load_resolution(i), segment_vmaf))
                    
                try:
                    remove = False
                    lower_level_index = j-1
                    if lower_level_index >= 0:
                        lower_level_resolution = segment.levels[lower_level_index].load_resolution(i)
                        lower_level_vmaf = np.mean(segment.levels[lower_level_index].load_vmaf(i))
                        self.logger.info("Segment {}-th level {} at lower resolution {} has mean VMAF {}".format(i, lower_level_index, lower_level_resolution, lower_level_vmaf))
                        delta_vmaf = segment_vmaf - lower_level_vmaf
                        if delta_vmaf < vmaf_treshold:
                            remove = True
                            self.logger.info("Delta vmaf is {} < {}. Marked for removal".format(delta_vmaf, vmaf_treshold))
                        else:
                            self.logger.info("Delta vmaf is {} > {}. Not marked for removal".format(delta_vmaf, vmaf_treshold))
                    else:
                        self.logger.info("Lower resolution is not present. Not marked for removal")
                        remove = False

                    if remove:
                        if i not in remove_map.keys():
                            remove_map[i] = []
                        remove_map[i].append(l)
                    
                except:
                        import traceback
                        traceback.print_exc()
                        self.logger.info("Augmented chunk {} at resolution {} is not available".format(i, video.video().load_resolution()))
            
        multires_video = multires_video.remove_levels(remove_map)
        return multires_video







