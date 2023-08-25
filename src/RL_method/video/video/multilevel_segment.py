import sys
import copy
import math
import inspect
import numpy as np
from src.consts.simulation_file_consts import *
from src.consts.grouper_configs_consts import BYTES_OPT
from src.utils.video.level import Level
from typing import List
from src.consts.manifest_representation_consts import *

M_IN_K = 1000.0
B_IN_BYTE = 8


MODES = ['STD', 'AUG', 'ALL']

def get_caller_name():
    return inspect.stack()[2][3]

## fragments is of the type list of "segment"
## result after the segmentation of Full Video
## segment must be run with all keyframe

#TYPEDEF
TypeLevel = List[Level]


class MultilevelSegment():
    
    def __init__(self, std_levels: TypeLevel, aug_levels=None, logger=None, dur=None):
        

        self.logger = logger
        self.std_levels = std_levels

        if aug_levels:
            self.aug_levels = aug_levels
        else:
            self.aug_levels = []

        self.levels = sorted( self.std_levels + self.aug_levels , key=lambda x: x.load_bitrate(0))
        self.resolutions_list = [ x.load_resolution(0) for x in self.levels ]
        
        try:
            self.duration = self.levels[0].load_duration(0)
        except:
            self.duration = dur

        self.simulation_data = None

        self.std_csv_data = None
        self.aug_csv_data = None
    


    #does not support multiple std levels at the same resolution
    def get_std_level(self, resolution):
        for l in self.std_levels:
            if l.load_resolution(-1) == resolution:
                return l.copy()
        None
    
    def debug_print_aug(self):
        debug_p = ''
        debug_p += 'segment_duration => {}\n'.format(self.duration)
        debug_p += 'standard levels:\n'
        for l in self.std_levels:
            debug_p += l.debug_print_aug()
        debug_p += 'augmented levels:\n'
        
        for l in self.aug_levels:
            debug_p += l.debug_print_aug()
        debug_p += 'augmented levels:\n'
         
        return debug_p

    def log_msg(self, msg, info=False):
        msg = "{} -> {}".format(get_caller_name(), msg)
        if self.logger is not None:
            if info:
                self.logger.info(msg)
            else:
                self.logger.debug(msg)

    def debug_print(self):
        msg = ''
        for resolution, level in zip(self.resolutions_list, self.levels):
            msg += "Resolution == {}\n".format(resolution)
            msg += level.debug_print()
        return msg

    def merge(self, other, idx):
        
        assert isinstance(other, MultilevelSegment), "data type error"
        assert len(self.resolutions_list) == len(other.resolutions_list), "Inconsistent number of levels"
        merged_levels = []
        
        for i, self_level in enumerate(self.levels):
            
            resolution_i = self.resolutions_list[i]
            other_level = None
            
            for j, o_l in enumerate(other.levels):
                if o_l.load_resolution(0) == resolution_i:
                    other_level = o_l
                    break

            self.log_msg("Merging resolutions {}".format(self.resolutions_list[i]))
            merged_levels.append(self_level.merge(other_level, idx))

        return MultilevelSegment(merged_levels, logger=self.logger)

    def load_augmented_bytes(self, idx):
        overhead = 0
        for level in self.aug_levels:
            overhead += level.load_bytes(idx)
        return overhead

    def add_levels(self, other_levels):
        copied_list_std_levels = [x.copy() for x in self.std_levels]
        copied_list_aug_levels = [x.copy() for x in self.aug_levels]
        return MultilevelSegment(copied_list_std_levels, aug_levels=copied_list_aug_levels+other_levels, logger=self.logger)
    

    def remove_levels(self, other_levels):
        copied_list_std_levels = [x.copy() for x in self.std_levels]
        copied_list_aug_levels = [x.copy() for x in self.aug_levels]
        dur = copied_list_std_levels[0].load_duration(0)

        for i, l in enumerate(other_levels):

            if l in copied_list_std_levels:
                copied_list_std_levels.remove(l)
            if l in copied_list_aug_levels:
                copied_list_aug_levels.remove(l)
        
        return MultilevelSegment(copied_list_std_levels, aug_levels=copied_list_aug_levels, logger=self.logger, dur=dur)
    

    def get_simulation_data(self, idx):
        if self.simulation_data:
           # assert self.simulation_data[SIM_FILE_CHUNK_PROGRESSIVE] == idx
            self.simulation_data[SIM_FILE_CHUNK_PROGRESSIVE] = idx
            return self.simulation_data

        s = {}
        s[SIM_FILE_CHUNK_PROGRESSIVE] = idx
        s[SIM_FILE_N_LEVELS] = len(self.levels)
        s[SIM_FILE_LEVELS] = []
        s[SIM_FILE_DURATION] = self.duration

        for res, lev in zip(self.resolutions_list, self.levels):
            s[SIM_FILE_LEVELS].append(lev.get_simulation_data(idx))
        s[SIM_FILE_LEVELS] = sorted(s[SIM_FILE_LEVELS], key=lambda x: x[SIM_FILE_BITRATE])
        self.simulation_data = s
        return self.simulation_data
    

    def load_std_csv_data(self, idx):
        if self.std_csv_data:
            self.std_csv_data[INDEX_CSV] = idx
            return self.std_csv_data
        
        self.std_csv_data = {}
        self.std_csv_data[INDEX_CSV] = idx
        self.std_csv_data[DURATION_CSV] = self.duration

        for lev in self.std_levels:
            self.std_csv_data.update(lev.get_level_csv_data_std(idx))
        return self.std_csv_data

    def load_aug_csv_data(self, idx):
        if self.aug_levels == []:
            return []
        
        dict_list_aug = []
        for lev in self.aug_levels:
            dict_list_aug.append(lev.get_level_csv_data_aug(idx))
        
        return dict_list_aug


    def load_vmaf_list_by_index(self, idx, level_index):
        assert level_index >= 0 and level_index < len(self.levels)
        return self.levels[level_index].load_vmaf(idx)

    def load_duration(self, idx):
        self.log_msg("Selected: load durations for segment {}".format(idx))
        return self.duration

    def mode(self, mode):
        if mode == MODES[0]:
            return self.std_levels
        elif mode == MODES[1]:
            return self.aug_levels
        elif mode == MODES[2]:
            return self.levels
        else:
            sys.exit(-1)
      

    def load_bytes(self, idx,  m=MODES[2]):
        self.log_msg("Selected: load bytes")
        l = self.mode(m)
        return [x.load_bytes(idx) for x in l]

    def load_bitrates(self, idx, m=MODES[2]):
        self.log_msg("Selected: load bitrates")
        l = self.mode(m)
        return [x.load_bitrate(idx) for x in l]
    
    def load_vmafs(self, idx, m=MODES[2]):
        self.log_msg("Selected: load bitrates")
        l = self.mode(m)
        return [x.load_vmaf(idx) for x in l]
    
    def load_total_frames(self, idx):
        self.log_msg("Selected: load frames for segment {}".format(idx))
        frames_array = [x.load_total_frames(idx) for x in self.levels]
        assert frames_array.count(frames_array[0]) == len(frames_array)
        return frames_array[0]

    def load_resolution(self):
        self.log_msg("Selected: load resolutions")
        return self.resolutions_list

    def copy(self):
        copied_std_level_list = [x.copy() for x in self.std_levels]
        try:
            copied_aug_level_list = [x.copy() for x in self.aug_levels]
        except:
            copied_aug_level_list = None

        return MultilevelSegment(copied_std_level_list, aug_levels=copied_aug_level_list,  logger=self.logger)
