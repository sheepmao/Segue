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

class H264MeanSameAE(AugmentationEncoder):
    def __init__(   self, raw_video,
                    rescaled_videos, ss,
                    original_segments_dir,
                    augmented_template_dir,
                    splitting_module_args,
                    augmentation_module_args,
                    log_dir, figs_dir,
                    verbose=False):
        
        
        self.log_dir = log_dir
        self.figs_dir = figs_dir
        self.verbose = verbose
        log_file = os.path.join(log_dir,'halved_up_augmenter.log')
        self.augmented_template_dir = augmented_template_dir
        self.logger = create_logger('Mean same augmenter', log_file, verbose=verbose)
        self.raw_video = raw_video
        
        self.rescaled_videos = {}
        for video in rescaled_videos:
            self.rescaled_videos[video.video().load_resolution()] = video
        


        self.splitting_module_args = splitting_module_args
        self.ss = ss 
        chunks_no = len(glob(os.path.join(original_segments_dir, '*.{}'.format(EXTENSION))))
        assert chunks_no > 0
        self.original_chunks = []
        self.splitting_module_args = splitting_module_args

        for i in range(chunks_no):
            self.original_chunks.append(Video(os.path.join(original_segments_dir, "{}.{}".format(i, EXTENSION)), log_dir, verbose=verbose))
        

    def make_augmented_segments(self):
        self.logger.info("Starting augmented segments computation")
        augmented_videos = []
        for resolution, rescaled_video in self.rescaled_videos.items():
            
            
            self.logger.info("Handling resolution {}".format(resolution))
            average_bitrate = rescaled_video.video().load_bitrate()
            augmented_segments_dir = self.augmented_template_dir.format(resolution)
            self.logger.info("Storing augmented video in {}".format(augmented_segments_dir))
            self.logger.info("Target bitrate is {}".format(average_bitrate))
            ladders_df = {}
            
            ladders_df[K_LADDER_RESOLUTION] = resolution
            ladders_df[K_LADDER_FPS] = int(round(rescaled_video.video().load_fps()))
            ladders_df[K_LADDER_TARGET_BR] = average_bitrate
            ladders_df[K_LADDER_MIN_BR] = average_bitrate
            ladders_df[K_LADDER_MAX_BR] = average_bitrate
            ladder = Ladders(pd.DataFrame([ladders_df]), "h264", resolution, int(round(rescaled_video.video().load_fps())), self.logger)
            
            file_list_t = "file '{}'\n"
            flist = ''

            for i, segment in enumerate(self.original_chunks):
                segment_out = os.path.join(augmented_segments_dir, "segments_video/{}.{}".format(i, EXTENSION))
                s = segment.rescale_h264_two_pass(ladder, segment_out)
                self.logger.debug("Segment {} has bitrate {}".format(i, s.load_bitrate()))
                flist += file_list_t.format(segment_out)
            
            with tempfile.NamedTemporaryFile(dir=os.getcwd()) as temp:
                temp.write(bytes(flist, encoding='utf-8'))
                temp.flush()
                unfragmented_video = os.path.join(self.augmented_template_dir.format(resolution), 'unfragmented.{}'.format(EXTENSION))
                unfragmented_video = FullVideo(Video(unfragmented_video, self.log_dir, concat_file=temp.name, verbose=self.verbose))
                augmented_videos.append(unfragmented_video)

        splitter = H264Splitter( self.raw_video, augmented_videos,
                                self.augmented_template_dir, self.ss, 
                                self.splitting_module_args,
                                self.verbose, self.log_dir, self.figs_dir)
            
        splitter.split_and_compute()
        return augmented_videos
                                    











