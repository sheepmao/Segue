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

class Nonee(AugmentationEncoder):
    def __init__(   self, raw_video,
                    rescaled_videos, ss,
                    original_segments_dir,
                    augmented_template_dir,
                    splitting_module_args,
                    augmentation_module_args,
                    log_dir, figs_dir,
                    verbose=False):
        pass

    def make_augmented_segments(self):
        self.logger.info("Nothing to do here")
        return None
                                    











