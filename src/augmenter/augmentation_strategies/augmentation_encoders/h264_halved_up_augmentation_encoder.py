from abc import ABC, abstractmethod
from src.utils.logging.logging_segue import create_logger
from src.consts.segments_composition_consts import *
from src.consts.splitter_consts import *
from src.consts.ladders_configs_consts import *
from src.utils.video_factory import Video, FullVideo, EXTENSION
import os
import json
from src.augmenter.augmentation_strategies.augmentation_encoders.augmentation_encoder import AugmentationEncoder
from src.utils.read_ladders.ladders import Ladders
import pandas as pd
from glob import glob
import tempfile
from src.augmenter.splitting_strategies.h264_splitter import H264Splitter



class H264HalvedUpAE(AugmentationEncoder):
    def __init__(   self, raw_video,
                    rescaled_videos, ss,
                    original_segments_dir,
                    augmented_template_dir,
                    splitting_module_args,
                    augmenter_encoding_args,
                    log_dir, figs_dir,
                    verbose=False):
        
        
        self.log_dir = log_dir
        self.figs_dir = figs_dir
        self.verbose = verbose
        log_file = os.path.join(log_dir, 'halved_up_augmenter.log')
        self.augmented_template_dir = augmented_template_dir
        self.logger = create_logger('Halved Up augmenter', log_file, verbose=verbose)
        self.raw_video = raw_video
        
        self.rescaled_video_sorted = sorted(rescaled_videos, key= lambda x: int(x.video().load_resolution().split('x')[0]))

        self.splitting_module_args = splitting_module_args
        self.ss = ss 
        chunks_no = len(glob(os.path.join(original_segments_dir, '*.{}'.format(EXTENSION))))
        self.original_chunks = []
        self.splitting_module_args = splitting_module_args

        for i in range(chunks_no):
            self.original_chunks.append(Video(os.path.join(original_segments_dir, "{}.{}".format(i, EXTENSION)), log_dir, verbose=verbose))
 

    def make_augmented_segments(self):
        self.logger.info("Starting augmented segments computation")
        augmented_videos = []

        for rescaled_video_down, rescaled_video_up in zip(self.rescaled_video_sorted, self.rescaled_video_sorted[1:]): 
            
            self.logger.info("Resolution Down: {}, Resolution UP: {}".format(   rescaled_video_down.video().load_resolution(),
                                                                                rescaled_video_up.video().load_resolution()))
            target_resolution = rescaled_video_up.video().load_resolution()
            fps = rescaled_video_up.video().load_fps()

            self.logger.info("Handling resolution {}".format(target_resolution))

            segments_down = rescaled_video_down.load_segments()
            segments_up = rescaled_video_up.load_segments()
            
            augmented_segments_dir = self.augmented_template_dir.format(target_resolution)
            
            file_list_t = "file '{}'\n"
            flist = ''


            for i, (s_down, s_up) in enumerate(zip(segments_down, segments_up)):

                b_down =  s_down.video().load_bitrate() 
                b_up =  s_up.video().load_bitrate()
                average_bitrate = (b_down + b_up) / 2
                self.logger.debug("Down bitrate ==> {}".format(b_down))
                self.logger.debug("Up bitrate ==> {}".format(b_up))
                self.logger.debug("Target bitrate ==> {}".format(average_bitrate))

                self.logger.info("Storing augmented segments in {}".format(augmented_segments_dir))
                ladders_df = {}
                
                ladders_df[K_LADDER_RESOLUTION] = target_resolution
                ladders_df[K_LADDER_FPS] = fps
                ladders_df[K_LADDER_TARGET_BR] = average_bitrate
                ladders_df[K_LADDER_MIN_BR] = average_bitrate
                ladders_df[K_LADDER_MAX_BR] = average_bitrate

                ladder = Ladders(pd.DataFrame([ladders_df]), "h264", target_resolution, fps, self.logger)
                
                segment_out = os.path.join(augmented_segments_dir, "segments_video/{}.{}".format(i,EXTENSION))
                
                segment = self.original_chunks[i]
                s = segment.rescale_h264_two_pass(ladder, segment_out)
                
                flist += file_list_t.format(segment_out)
                
            
            with tempfile.NamedTemporaryFile(dir=os.getcwd()) as temp:
                temp.write(bytes(flist, encoding='utf-8'))
                temp.flush()
                unfragmented_video = os.path.join(augmented_segments_dir, 'unfragmented.{}'.format(EXTENSION))
                unfragmented_video = FullVideo(Video(unfragmented_video, self.log_dir, verbose=self.verbose, concat_file=temp.name))
                augmented_videos.append(unfragmented_video)
        
        splitter = H264Splitter(    self.raw_video, augmented_videos,
                                    self.augmented_template_dir, self.ss, 
                                    self.splitting_module_args,
                                    self.verbose, self.log_dir, self.figs_dir )
        splitter.split_and_compute()
        return augmented_videos
                                    











