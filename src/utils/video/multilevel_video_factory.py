import sys
import copy
import math
import inspect
import numpy as np
from src.consts.simulation_file_consts import *
from src.consts.grouper_configs_consts import BYTES_OPT
from src.utils.video.level import Level
from src.utils.video.multilevel_segment import MultilevelSegment
from src.utils.video.multilevel_video import MultilevelVideo
from src.utils.video_factory import Video, FullVideo

class MultilevelVideoFactory():
    def __init__(self, logger, OPT=BYTES_OPT[1], enable_logging=False):
        self.logger = logger

        if enable_logging:
            self.pass_logger = logger
        else:
            self.pass_logger = None

        self.bytes_opt = OPT
    
    def multilevel_video_from_dict(self, std_segments):
        
        assert len(std_segments) > 0
        resolutions = list(std_segments.keys())
        chunks_no = len(std_segments[resolutions[0]])
        for res in resolutions:
            assert len(std_segments[res]) == chunks_no
        multilevel_segments = []
        for chunk_no in range(chunks_no):
            levels = []
            
            for res in resolutions:
                level = Level( [std_segments[res][chunk_no]], OPT=self.bytes_opt, logger=self.pass_logger)
                levels.append(level)

            multilevel_segment = MultilevelSegment(levels, logger=self.pass_logger)
            multilevel_segments.append(multilevel_segment)
        
        return MultilevelVideo(multilevel_segments, logger=self.pass_logger)
    
    def multilevel_video_from_full_videos(self, full_videos):
        videos_dict = {} 
        for full_video in full_videos:
            assert isinstance(full_video, FullVideo)
            videos_dict[full_video.video().load_resolution()] = full_video.load_segments()
        
        return self.multilevel_video_from_dict(videos_dict)

