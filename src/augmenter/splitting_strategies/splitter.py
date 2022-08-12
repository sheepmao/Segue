from abc import ABC, abstractmethod
from src.utils.logging.logging_segue import create_logger
from src.consts.segments_composition_consts import *
from src.consts.splitter_consts import *
import os
import json

class Splitter(ABC):
    def __init__(self,  raw_video, 
                        rescaled_videos,
                        rescaled_dir_template,
                        ss,
                        splitting_module_args, 
                        verbose, log_dir, figs_dir):
        
        
        log_file = os.path.join(log_dir, 'splitter.log')
        self.logger = create_logger('Splitter', log_file, verbose=verbose)
        
        self.raw_video = raw_video
        self.rescaled_videos = rescaled_videos
        self.rescaled_dir_template = rescaled_dir_template


        self.imposed_keyframe_indexes = [ int(ss[str(s)][K_SSFA]) for s in range(len(ss)) ]
        self.imposed_keyframe_timestamps = [ float(ss[str(s)][K_SSTA]) for s in range(len(ss)) ]
        self.splitting_module_args = splitting_module_args
        self.vmaf_model = splitting_module_args[K_SPLITTING_VMAF_MODULE]

    @abstractmethod
    def split_and_compute(self):
        pass
