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
    """
    Factory class for creating MultilevelVideo instances from various inputs.
    """

    def __init__(self, logger, OPT=BYTES_OPT[1], enable_logging=False):
        """
        Initializes the MultilevelVideoFactory.

        :param logger: Logger object
            Used to log messages and events.
        :param OPT: constant, optional (default is BYTES_OPT[1])
            Optimization option.
        :param enable_logging: bool, optional (default is False)
            If set to True, logging is enabled.
        """
        self.logger = logger

        # Conditionally sets the logger based on enable_logging
        if enable_logging:
            self.pass_logger = logger
        else:
            self.pass_logger = None

        self.bytes_opt = OPT
    
    def multilevel_video_from_dict(self, std_segments):
        """
        Constructs a MultilevelVideo instance from a dictionary of standard segments.

        :param std_segments: dict
            Dictionary containing standard segments. 
            Keys are resolutions and values are lists of segments.

        :return: MultilevelVideo
            An instance of the MultilevelVideo constructed from the provided segments.
        """
        # Ensures there are segments in the dictionary
        assert len(std_segments) > 0
        resolutions = list(std_segments.keys())
        chunks_no = len(std_segments[resolutions[0]])

        # Ensure all resolutions have the same number of chunks
        for res in resolutions:
            assert len(std_segments[res]) == chunks_no

        # Construct multilevel segments from the provided segments
        multilevel_segments = []
        for chunk_no in range(chunks_no):
            levels = []

            for res in resolutions:
                level = Level([std_segments[res][chunk_no]], OPT=self.bytes_opt, logger=self.pass_logger)
                levels.append(level)

            multilevel_segment = MultilevelSegment(levels, logger=self.pass_logger)
            multilevel_segments.append(multilevel_segment)
        
        return MultilevelVideo(multilevel_segments, logger=self.pass_logger)
    
    def multilevel_video_from_full_videos(self, full_videos):
        """
        Constructs a MultilevelVideo instance from a list of FullVideo instances.

        :param full_videos: list of FullVideo
            List containing FullVideo instances.

        :return: MultilevelVideo
            An instance of the MultilevelVideo constructed from the provided FullVideos.
        """
        videos_dict = {} 

        # Construct a dictionary with resolutions as keys and segments as values
        for full_video in full_videos:
            assert isinstance(full_video, FullVideo)
            #print("Current Resolution Video: ",full_video.video().load_resolution())
            videos_dict[full_video.video().load_resolution()] = full_video.load_segments()
        #print(videos_dict)
        # Use the previously defined method to construct a MultilevelVideo from the dictionary
        return self.multilevel_video_from_dict(videos_dict)