from src.augmenter.augmentation_strategies.augmenter import Augmenter
from src.consts.augmenter_consts import *
from src.utils.video.level import Level
import numpy as np

class BetaV(Augmenter):

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
        baseline_video_map = {}
        for video in self.rescaled_videos:
            baseline_video_map[video.video().load_resolution()] = video
            resolution_list.append(video.video().load_resolution())

        resolution_list = sorted(resolution_list, key=lambda x: int(x.split('x')[0]))
        chunks_no = len(self.rescaled_videos[0].load_segments())
        
        remove_map = {}

        self.logger.info("Chunks no is {}".format(chunks_no))

        vmaf_treshold = float(self.augmentation_module_args[K_AUGMENTER_VMAF_TH])
        
        self.logger.info("Threshold for beta V is {} vmaf points".format(vmaf_treshold))

        for video in self.rescaled_videos:

            self.logger.info("Handling resolution {}".format(video.video().load_resolution()))
            for i, segment in enumerate(video.load_segments()):

                segment_vmaf = np.mean(segment.vmaf())
                self.logger.info("Segment {}-th at resolution {} has mean VMAF {}".format(i, video.video().load_resolution(), segment_vmaf))
                    
                try:
                    remove = False
                    lower_resolution_index = resolution_list.index(video.video().load_resolution()) - 1
                    if lower_resolution_index >= 0:
                        lower_resolution = resolution_list[lower_resolution_index]
                        lower_resolution_vmaf = np.mean(baseline_video_map[lower_resolution].load_segments()[i].vmaf())
                        self.logger.info("Segment {}-th at lower resolution {} has mean VMAF {}".format(i, lower_resolution, lower_resolution_vmaf))
                        delta_vmaf = segment_vmaf - lower_resolution_vmaf
                        if delta_vmaf < vmaf_treshold:
                            remove = True
                            self.logger.info("Delta vmaf is {} < {}. Marked for removal".format(delta_vmaf, vmaf_treshold))
                        else:
                            self.logger.info("Delta vmaf is {} > {}. Not marked for removal".format(delta_vmaf, vmaf_treshold))
                    else:
                        self.logger.info("Lower resolution is not present. Marked for augmentation")
                        remove = False

                    if remove:
                        level = baseline_video_map[video.video().load_resolution()].load_segments()[i]
                        level = Level([level])
                    
                        if i not in remove_map.keys():
                            remove_map[i] = []

                        remove_map[i].append(level)
                    
                except:
                        self.logger.info("Augmented chunk {} at resolution {} is not available".format(i, video.video().load_resolution()))

        multires_video = multiresolution_video.remove_levels(remove_map)
        return multires_video







