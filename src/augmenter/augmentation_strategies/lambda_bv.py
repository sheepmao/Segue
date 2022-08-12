from src.augmenter.augmentation_strategies.augmenter import Augmenter
from src.consts.augmenter_consts import *
from src.utils.video.level import Level
import numpy as np

class LambdaBV(Augmenter):

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
        augmented_videos = self.ae.make_augmented_segments()
        augmented_videos_map = {}
        resolution_list  = []
        
        for video in augmented_videos:
            augmented_videos_map[video.video().load_resolution()] = video
        
        baseline_video_map = {}
        for video in self.rescaled_videos:
            baseline_video_map[video.video().load_resolution()] = video
            resolution_list.append(video.video().load_resolution())

        resolution_list = sorted(resolution_list, key=lambda x: int(x.split('x')[0]))
        chunks_no = len(self.rescaled_videos[0].load_segments())

        self.logger.info("Chunks no is {}".format(chunks_no))
        augmented_map = {} 
        

        br_treshold = float(self.augmentation_module_args[K_AUGMENTER_PERCENTAGE_TH_BR])
        vmaf_treshold = float(self.augmentation_module_args[K_AUGMENTER_VMAF_TH])
        
        self.logger.info("Threshold for lambda V is {} vmaf points".format(vmaf_treshold))
        self.logger.info("Threshold for lambda B is {} %".format(br_treshold))

        for video in self.rescaled_videos:

            self.logger.info("Handling resolution {}".format(video.video().load_resolution()))
            
            mean_bitrate = video.video().load_bitrate()
            self.logger.info("Mean bitrate is {}".format(mean_bitrate))
            max_bitrate_allowed = (mean_bitrate*br_treshold)/ 100.0 + mean_bitrate

            self.logger.info("Max bitrate allowed is {}".format(max_bitrate_allowed))

            for i, segment in enumerate(video.load_segments()):

                segment_vmaf = np.mean(segment.vmaf())
                segment_bitrate = segment.video().load_bitrate()
                self.logger.info("Segment {}-th at resolution {} has mean VMAF {} and mean bitrate".format(i, video.video().load_resolution(), segment_vmaf, segment_bitrate))

                if segment_bitrate > max_bitrate_allowed:
                    self.logger.info("Segment {}-th at resolution {} needs to be augmented".format(i, video.video().load_resolution()))
                    
                    try:
                        augment = False
                        lower_resolution_index = resolution_list.index(video.video().load_resolution()) - 1
                        if lower_resolution_index >= 0:
                            lower_resolution = resolution_list[lower_resolution_index]
                            lower_resolution_vmaf = np.mean(baseline_video_map[lower_resolution].load_segments()[i].vmaf())
                            self.logger.info("Segment {}-th at lower resolution {} has mean VMAF {}".format(i, lower_resolution, lower_resolution_vmaf))
                            delta_vmaf = segment_vmaf - lower_resolution_vmaf
                            if delta_vmaf > vmaf_treshold:
                                augment = True
                                self.logger.info("Delta vmaf is {} > {}. Marked for augmentation".format(delta_vmaf, vmaf_treshold))
                            else:
                                self.logger.info("Delta vmaf is {} < {}. Not marked for augmentation".format(delta_vmaf, vmaf_treshold))
                        else:
                            self.logger.info("Lower resolution is not present. Marked for augmentation")
                            augment = True
                        
                        if augment:
                            level = augmented_videos_map[video.video().load_resolution()].load_segments()[i]
                            self.logger.info("Augmented segment resolution is {}".format(level.video().load_resolution()))
                            self.logger.info("Augmented segment vmaf is {}".format(np.mean(level.vmaf())))
                            self.logger.info("Augmented segment bitrate is {}".format(level.video().load_bitrate()))
                            level = Level([level])
                    
                            if i not in augmented_map.keys():
                                augmented_map[i] = []

                            if i == 0:
                                self.logger.info("Start segment doesn't get augmented")
                            else:
                                augmented_map[i].append(level)
                    
                    except:
                        self.logger.info("Augmented chunk {} at resolution {} is not available".format(i, video.video().load_resolution()))

        multires_video = multiresolution_video.add_levels(augmented_map)
        return multires_video







