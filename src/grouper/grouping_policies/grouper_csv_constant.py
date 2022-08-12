#from src.utils.ffmpeg.ffmpeg_utils import *

from src.utils.video_factory import Video, FullVideo, EXTENSION
import pandas as pd
import tempfile, os
from src.consts.keys_consts import *

from src.consts.grouper_configs_consts import *
from src.consts.video_configs_consts import *

from src.grouper.grouping_policies.grouper_policy import GrouperPolicy


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
        

        self.segment_seconds = float(grouper_data[K_PARAMETERS_GROUPER][K_SEGMENT_SECONDS_GROUPER])
        self.segment_multiplier = float(grouper_data[K_PARAMETERS_GROUPER]['multiplier'])

        self.logger.info("Fixed length gouper created correctly")
        self.logger.info("Desired constant length : {}".format(self.segment_seconds))
        self.logger.info("Desired multiplier from file : {}".format(self.segment_multiplier))
    


    def load_expected_keyframes(self):

        if self.segments_keys_indexes and self.segments_keys_timestamps:
            self.logger.debug("Keyframes already loaded")
            return self.segments_keys_indexes, self.segments_keys_timestamps
        

        seg_path = self.video_obj._video_path.replace('fqa', 'sqa')
        segment_obj = pd.read_csv(seg_path)
        key_obj = pd.read_csv(self.video_obj._video_path)
        

        time_iterator = 0
        frame_iterator = 0

        self.segments_keys_indexes, self.segments_keys_timestamps = [], []

        for i, row in segment_obj.iterrows():
            
            if (i % self.segment_multiplier == 0):
                pts = row['StartPTS']
                frame_num = list(key_obj.loc[key_obj['PTS'] == pts]['FrameNum'])[0]

                self.segments_keys_indexes.append(frame_num)
                self.segments_keys_timestamps.append(pts/1000000000.0)

        
        return self.segments_keys_indexes, self.segments_keys_timestamps


    def make_groups(self):
        
        resolutions = self.video_data[K_RESOLUTIONS].split()
        method = self.create_constant_rescaling_method()

        self.logger.info("Starting grouping routine. Method: constant. Length -> {}".format(self.segment_seconds))

        for res in resolutions:
            self.logger.debug("Handling resolution {}".format(res))
            file_out = os.path.join(self.rescaled_dir_template.format(res), 'unfragmented.{}'.format(EXTENSION))
            self.logger.debug("File stored at {}".format(file_out))
            
            cache_file = self.get_cache_file(res)
            video_res = self.video_obj.rescale_at_resolution(   file_out, res, 'h264', '',
                                                                method, cache=self.cache, cache_file=cache_file)
            
            self.logger.debug("Video at resolution {} re-encoded succesfully".format(res))
            file_keys_out = os.path.join(self.rescaled_dir_template.format(res), 'unfragmented.keys')
            self.logger.debug("Checking if all needed keyframes are presents")
            self.check(video_res, file_keys_out)
            self.logger.debug("Keyframes check completed succesfully")
             
        scene_df = self.format_dataframe_segments()
        return scene_df
