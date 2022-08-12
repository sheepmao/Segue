from src.augmenter.augmentation_strategies.augmenter import Augmenter
from src.consts.augmenter_consts import *
from src.utils.video.level import Level

class LambdaB(Augmenter):

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
        for video in augmented_videos:
            augmented_videos_map[video.video().load_resolution()] = video

        chunks_no = len(self.rescaled_videos[0].load_segments())
        self.logger.info("Chunks no is {}".format(chunks_no))
        augmented_map = {} 

        treshold = float(self.augmentation_module_args[K_AUGMENTER_PERCENTAGE_TH_BR])
        self.logger.info("Threshold for lambda B is {}".format(treshold))

        for video in self.rescaled_videos:
            self.logger.info("Handling resolution {}".format(video.video().load_resolution()))
            mean_bitrate = video.video().load_bitrate()
            self.logger.info("Mean bitrate is {}".format(mean_bitrate))
            max_bitrate_allowed = (mean_bitrate*treshold)/100.0 + mean_bitrate
            self.logger.info("Max bitrate allowed is {}".format(max_bitrate_allowed))

            for i, segment in enumerate(video.load_segments()):

                segment_bitrate = segment.video().load_bitrate()
                self.logger.info("Segment {}-th at resolution {} is {}".format(i, video.video().load_resolution(), segment_bitrate))
                if segment_bitrate > max_bitrate_allowed:

                    self.logger.info("Segment {}-th at resolution {} added to augmentation levels".format(i, video.video().load_resolution()))
                    try:
                        
                        level = augmented_videos_map[video.video().load_resolution()].load_segments()[i]
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







