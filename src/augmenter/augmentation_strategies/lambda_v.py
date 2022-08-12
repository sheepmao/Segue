from src.augmenter.augmentation_strategies.augmenter import Augmenter
from src.consts.augmenter_consts import *
from src.utils.video.level import Level
import numpy as np

class LambdaV(Augmenter):

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
        
        for video in self.rescaled_videos:
            resolution_list.append(video.video().load_resolution())

        resolution_list = sorted(resolution_list, key=lambda x: int(x.split('x')[0]))
        chunks_no = len(self.rescaled_videos[0].load_segments())
        self.logger.info("Chunks no is {}".format(chunks_no))
        augmented_map = {} 

        treshold = float(self.augmentation_module_args[K_AUGMENTER_VMAF_TH])
        self.logger.info("Threshold for lambda V is {} vmaf points".format(treshold))

        for video in self.rescaled_videos:

            self.logger.info("Handling resolution {}".format(video.video().load_resolution()))
            
            mean_vmaf = np.mean(video.vmaf())
            self.logger.info("Mean VMAF is {}".format(mean_vmaf))

            min_vmaf_allowed = mean_vmaf - treshold

            self.logger.info("Min VMAF allowed is {}".format(min_vmaf_allowed))

            for i, segment in enumerate(video.load_segments()):

                segment_vmaf = np.mean(segment.vmaf())

                self.logger.info("Segment {}-th at resolution {} has mean VMAF {}".format(i, video.video().load_resolution(), segment_vmaf))
                if segment_vmaf < min_vmaf_allowed:
                    
                    
                    self.logger.info("Segment {}-th at resolution {} needs to be augmented".format(i, video.video().load_resolution()))
                    try:
                        augmented_resolution = resolution_list[resolution_list.index(video.video().load_resolution()) + 1]
                        level = augmented_videos_map[augmented_resolution].load_segments()[i]
                        self.logger.info("Augmented segment vmaf is {}".format(np.mean(level.vmaf())))
                        level = Level([level])
                    
                        if i not in augmented_map.keys():
                            augmented_map[i] = []


                        if i == 0:
                            self.logger.info("Start segment doesn't get augmented")
                        else:
                            augmented_map[i].append(level)
                    
                    except:
                        self.logger.info("Augmented chunk {} at resolution {} +1 is not available".format(i, video.video().load_resolution()))

        multires_video = multiresolution_video.add_levels(augmented_map)
        return multires_video







