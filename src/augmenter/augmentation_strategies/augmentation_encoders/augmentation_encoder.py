from abc import ABC, abstractmethod
from src.utils.logging.logging_segue import create_logger
from src.consts.segments_composition_consts import *
from src.consts.splitter_consts import *
import os
import json

class AugmentationEncoder(ABC):
    def __init__(   self, raw_video, 
                    rescaled_videos, 
                    augmented_segments_template_dir,
                    vmaf_model, log_dir, verbose=False):
        
        
        log_file = os.path.join(log_dir, 'splitter.log')
        self.logger = create_logger('Splitter', log_file, verbose=verbose)
        self.raw_video = raw_video
        self.rescaled_videos = rescaled_videos
        self.vmaf_model = vmaf_model
        

    @abstractmethod
    def make_augmented_segments(self):
        pass
