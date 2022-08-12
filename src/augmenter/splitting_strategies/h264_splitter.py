from src.augmenter.splitting_strategies.splitter import Splitter
from src.consts.splitter_consts import *
import os

class H264Splitter(Splitter):
    def __init__(self,  raw_video, 
                        rescaled_videos,
                        rescaled_dir_template,
                        segments_structure,
                        splitting_module_args, 
                        verbose, log_dir, figs_dir):

        super().__init__(raw_video, 
                        rescaled_videos,
                        rescaled_dir_template,
                        segments_structure,
                        splitting_module_args, 
                        verbose, log_dir, figs_dir)

        self.logger.info("h264 splitter initialized")
    
    def split_and_compute(self):

        self.logger.info("Handling Splitting, VMAF and FFPROBE calculation.")
        
        for video in self.rescaled_videos:
            res = video.video().load_resolution()
            vmaf_file_out = os.path.join(self.rescaled_dir_template.format(res), 'unfragmented.{}'.format(self.vmaf_model))
            self.logger.debug("Storing VMAF in {}".format(vmaf_file_out))
            
            video.load_vmaf(self.raw_video, vmaf_file_out, self.vmaf_model)
            self.logger.info("VMAF of resolution {} computed succesfully".format(res))
            
            ffprobe_file_out = os.path.join(self.rescaled_dir_template.format(res), 'unfragmented.ffprobe')
            self.logger.debug("Storing FFprobe in {}".format(ffprobe_file_out))
            video.load_ffprobe(ffprobe_file_out)
            self.logger.info("FFPROBE of resolution {} computed succesfully".format(res))
            
            segments_dir = os.path.join(self.rescaled_dir_template.format(res), 'segments_video')
            self.logger.debug("Segments will be stored in {}".format(segments_dir))
            
            video.segment_h264(self.imposed_keyframe_indexes, self.imposed_keyframe_timestamps, segments_dir)

            self.logger.info("Fragmentation computed correctly for resolution {}".format(res))
            self.logger.info("Assigning VMAF to fragments for resolution {}".format(res))
            
            
            vmaf_dir = os.path.join(self.rescaled_dir_template.format(res), 'segments_{}'.format(self.vmaf_model))
            video.assign_vmaf_to_segments(vmaf_dir)
            self.logger.info("Vmaf assigned correctly to segment for resolution {}".format(res))
            
            ffprobe_dir = os.path.join(self.rescaled_dir_template.format(res), 'segments_ffprobe')
            video.assign_ffprobe_to_segments(ffprobe_dir)
            self.logger.info("FFPROBE assigned correctly to segment for resolution {}".format(res))


