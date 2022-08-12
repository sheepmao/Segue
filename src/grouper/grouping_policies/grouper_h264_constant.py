

import pandas as pd
import tempfile, os
from src.consts.keys_consts import *

from src.consts.grouper_configs_consts import *
from src.consts.video_configs_consts import *

from src.grouper.grouping_policies.grouper_policy import GrouperPolicy





## Determines the keyframes position given the video properties
## Already rescales at all resolutions, checks if keyframes are aligned


class FixedSegmentsGrouperPolicy(GrouperPolicy):
    def __init__(   self, 
                    grouper_data,
                    video_data,
                    video_obj,
                    rescaled_dir_template,
                    verbose,
                    logs_dir,
                    figs_dir):
        
        super().__init__(   grouper_data,
                            video_data,
                            video_obj,
                            rescaled_dir_template,
                            verbose,
                            logs_dir,
                            figs_dir)
        

        self.bitrate_ladders_file = grouper_data[K_PARAMETERS_GROUPER][K_BITRATE_LADDERS_GROUPER]
        self.segment_seconds = float(grouper_data[K_PARAMETERS_GROUPER][K_SEGMENT_SECONDS_GROUPER])

        self.logger.info("Fixed length gouper created correctly")
        self.logger.info("Bitrate ladders retrieved at {}".format(self.bitrate_ladders_file))
        self.logger.info("Desired constant length : {}".format(self.segment_seconds))
    


    def load_expected_keyframes(self):

        if self.segments_keys_indexes and self.segments_keys_timestamps:
            self.logger.debug("Keyframes already loaded")
            return self.segments_keys_indexes, self.segments_keys_timestamps

        video_fps = self.video_obj.load_fps()
        video_total_frames = self.video_obj.load_total_frames()
        segments_time = float(self.grouper_data[K_PARAMETERS_GROUPER][K_SEGMENT_SECONDS_GROUPER])
        
        time_iterator = 0
        frame_iterator = 0

        self.segments_keys_indexes, self.segments_keys_timestamps = [], []

        while frame_iterator < video_total_frames:
            
            self.segments_keys_indexes.append(frame_iterator)
            self.segments_keys_timestamps.append(time_iterator)

            time_iterator += segments_time
            frame_iterator = int(max(time_iterator * video_fps, 0.0))
        
        return self.segments_keys_indexes, self.segments_keys_timestamps


    def make_groups(self):
        
        resolutions = self.video_data[K_RESOLUTIONS].split()
        method = self.create_constant_rescaling_method()

        self.logger.info("Starting grouping routine. Method: constant. Length -> {}".format(self.segment_seconds))

        for res in resolutions:
            self.logger.debug("Handling resolution {}".format(res))
            file_out = os.path.join(self.rescaled_dir_template.format(res), 'unfragmented.mp4')
            self.logger.debug("File stored at {}".format(file_out))
            
            cache_file = self.get_cache_file(res)
            video_res = self.video_obj.rescale_at_resolution(   file_out, res, 'h264', self.bitrate_ladders_file,
                                                                method, cache=self.cache, cache_file=cache_file)
            
            self.logger.debug("Video at resolution {} re-encoded succesfully".format(res))
            file_keys_out = os.path.join(self.rescaled_dir_template.format(res), 'unfragmented.keys')
            self.logger.debug("Checking if all needed keyframes are presents")
            self.check(video_res, file_keys_out)
            self.logger.debug("Keyframes check completed succesfully")
             
        scene_df = self.format_dataframe_segments()
        return scene_df
