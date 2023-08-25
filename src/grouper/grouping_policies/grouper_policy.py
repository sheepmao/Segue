from abc import ABC, abstractmethod
from src.utils.logging.logging_segue import create_logger
from src.consts.grouper_configs_consts import *
from src.consts.video_configs_consts import *
from src.consts.rescaling_method_consts import *
from src.consts.keys_consts import *
import pandas as pd

import os, sys

class GrouperPolicy(ABC):
    def __init__(   self, 
                    grouper_data,
                    video_data,
                    video_obj,
                    rescaled_dir_template,
                    verbose,
                    logs_dir,
                    figs_dir):
        
        self.grouper_data = grouper_data
        self.video_data = video_data
        self.video_obj = video_obj
        self.rescaled_dir_template = rescaled_dir_template
        self.logs_dir = logs_dir        
        self.verbose = verbose
        # creation of the logger

        grouper_name = grouper_data[K_NAME_GROUPER]

        log_file = os.path.join(logs_dir, '{}.log'.format(grouper_name))
        self.logger = create_logger('Grouper Policy {}'.format(grouper_name), log_file, verbose=verbose)

        self.figs_dir = figs_dir
        
        self.cache_file = None
        self.cache_folder_template = None
        self.cache = False

        if K_CACHE_STORE_FOLDER_TEMPLATE_GROUPER in self.grouper_data[K_PARAMETERS_GROUPER].keys():
            assert K_CACHE_STORE_NAME_GROUPER in self.grouper_data[K_PARAMETERS_GROUPER].keys(), "If cache folder is specified, so must be the file"
            self.cache_folder_template = self.grouper_data[K_PARAMETERS_GROUPER][K_CACHE_STORE_FOLDER_TEMPLATE_GROUPER]
            self.cache_file = self.grouper_data[K_PARAMETERS_GROUPER][K_CACHE_STORE_NAME_GROUPER]
            self.cache = True

            self.logger.debug("Cache option selected")
            self.logger.debug("Cache folder template is {}".format(self.cache_folder_template))
            self.logger.debug("Cache file is {}".format(self.cache_file))


        self.segments_keys_indexes = []
        self.segments_keys_timestamps = []


    def create_constant_rescaling_method(self):
        method = {}
        if K_SEGMENT_SECONDS_GROUPER not in self.grouper_data[K_PARAMETERS_GROUPER]:
            self.logger.error("{} not in parameters. Rescaling method is not correct, selected constant length".format(K_SEGMENT_SECONDS))
            sys.exit(-1)

        method[K_RESCALING_METHOD_KEYFRAMES_APPROACH] = K_RESCALING_METHOD_KEYFRAMES_CONSTANT
        g = float(self.grouper_data[K_PARAMETERS_GROUPER][K_SEGMENT_SECONDS_GROUPER])
        method[K_RESCALING_METHOD_SEGMENT_SECONDS] = g 
        return method


    def create_forced_keys_rescaling_method(self):
        method = {}
        
        if not self.segments_keys_indexes or not self.segments_keys_timestamps:
            self.logger.error("Forced keys not computed")
            sys.exit(-1)

        method[K_RESCALING_METHOD_KEYFRAMES_APPROACH] = K_RESCALING_METHOD_KEYFRAMES_FORCE_KEYS
        method[K_RESCALING_METHOD_FORCED_INDEXES_LIST] = self.segments_keys_indexes
        method[K_RESCALING_METHOD_FORCED_TIMESTAMPS_LIST] = self.segments_keys_timestamps

        return method


    
    def create_gop_rescaling_method(self):
        
        method = {}
        if K_GOP_SECONDS_GROUPER not in self.grouper_data[K_PARAMETERS_GROUPER]:
            self.logger.error("{} not in parameters. Rescaling method is not correct, selected gop".format(K_GOP_SECONDS_GROUPER))
            sys.exit(-1)

        method[K_RESCALING_METHOD_KEYFRAMES_APPROACH] = K_RESCALING_METHOD_KEYFRAMES_GOP
        g = float(self.grouper_data[K_PARAMETERS_GROUPER][K_GOP_SECONDS_GROUPER])
        method[K_RESCALING_METHOD_GOP_SECONDS] = g # K_RESCALING_METHOD_GOP_SECONDS = 'gop_seconds' specified in src/consts/rescaling_method_consts.py
        return method



    def check(self, video, cache_keys_out):
        
        self.logger.debug("Checking if video {} presents all the forced keyframes".format(video.video_path()))
        self.logger.debug("Caching keyframes in {}".format(cache_keys_out))

        video_keyframes_indexes, video_keyframes_timestamps = video.load_keyframes(cache=True, cache_file=cache_keys_out)
        self.load_expected_keyframes()

        assert len(self.segments_keys_indexes) > 0, "Key indexes have not yet been initialized!"
        assert len(self.segments_keys_timestamps) > 0, "Key timestamps have not yet been initialized!"

        for key_frame_index, key_frame_timestamp in zip(self.segments_keys_indexes, self.segments_keys_timestamps):
            assert key_frame_index in self.segments_keys_indexes
            assert key_frame_timestamp in self.segments_keys_timestamps

        
        self.logger.debug("Video {} has all the wanted keyframes".format(video.video_path()))


    def get_cache_file(self, resolution):
        cache_file = None
        if self.cache:
            cache_file = os.path.join(self.cache_folder_template.format(self.video_data[K_NAME_VIDEO], resolution), self.cache_file)
        return cache_file

    def format_dataframe_segments(self):
        
        logged_keys_indexes = self.segments_keys_indexes.copy()
        logged_keys_timestamps = self.segments_keys_timestamps.copy()

        logged_keys_indexes.append(self.video_obj.load_total_frames())
        logged_keys_timestamps.append(self.video_obj.load_duration())
        
        assert len(logged_keys_indexes) == len(logged_keys_timestamps)
        
        self.logger.debug("Logged key frames indexes: {}".format(logged_keys_indexes))
        self.logger.debug("Logged key frames timestamps: {}".format(logged_keys_timestamps))

        if len(logged_keys_indexes) == 0:
            self.logger.error("Empty segments structure. Run \"make_groups\" before!")
            return None

        if logged_keys_indexes[0] == 0:
            del logged_keys_indexes[0]
            del logged_keys_timestamps[0]
        
        previous_end_time = 0
        previous_end_frame = 0
        scene_df = pd.DataFrame(columns=[KET, KST, KEF, KSF])

        for index, k in enumerate(logged_keys_indexes):

            end_frame = logged_keys_indexes[index]
            end_time = logged_keys_timestamps[index]

            d = {KST: [previous_end_time], KET: [end_time], KSF: [previous_end_frame], KEF: [end_frame]}
            line = pd.DataFrame(data=d)
            scene_df = scene_df.append(line, ignore_index=True)
            previous_end_time = end_time
            previous_end_frame = end_frame

        return scene_df
    
    @abstractmethod
    def load_expected_keyframes(self):
        pass

    @abstractmethod
    def make_groups(self):
        pass



