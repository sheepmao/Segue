import sys
import copy
import math
import inspect
import numpy as np
from src.consts.simulation_file_consts import *
from src.consts.grouper_configs_consts import BYTES_OPT

def get_caller_name():
    return inspect.stack()[2][3]



class MultilevelVideo:
    def __init__(self, multilevel_segments, logger=None):
        self.logger = logger
        self.multilevel_segments = multilevel_segments
        self.chunks_no = len(self.multilevel_segments)
    

    def get_std_level(self, res, no):
        return self.multilevel_segments[no].get_std_level(res)
    
    def debug_print_aug(self):
        debug_p = ''
        for i, segment in enumerate(self.multilevel_segments):
            debug_p += 'segment {}\n'.format(i)
            debug_p += segment.debug_print_aug()
        return debug_p
            

    def log_msg(self, msg, info=False):
        msg = "{} -> {}".format(get_caller_name(), msg)
        if self.logger is not None:
            if info:
                self.logger.info(msg)
            else:
                self.logger.debug(msg)
    
    
    
    def load_augmented_bytes(self, start=0, end=-1):
        if end < 0:
            end = self.chunks_no
        assert start >= 0 and end <= self.chunks_no
        overhead = 0
        for i, s in enumerate(self.multilevel_segments[start:end]):
            overhead += s.load_augmented_bytes(i + start)
        return overhead

    def load_std_dataframe(self):
        import pandas as pd
        dataframe_std = []
        
        for i, seg in enumerate(self.multilevel_segments):
            dataframe_std.append(seg.load_std_csv_data(i))

        return pd.DataFrame(dataframe_std)

    
    def load_aug_dataframe(self):
        import pandas as pd
        dataframe_aug = []
        
        for i, seg in enumerate(self.multilevel_segments):
            dataframe_aug += seg.load_aug_csv_data(i)
        
        if dataframe_aug != []:
            return pd.DataFrame(dataframe_aug)
        else:
            return None

    def chunks_no(self):
        return self.chunks_no

    def segments(self):
        return self.multilevel_segments
    
    
    def debug_print(self):
        msg = ''
        for fr in self.multilevel_segments:
            msg += fr.debug_print()
        return msg


    
    def apply_on_window(self, start_index, combo):
        
        combo_s = []     
        assert combo is not None and len(combo) > 0

        self.log_msg("Assemble combo is {}".format(combo))
        self.log_msg("Start index is {}".format(start_index))

        self.log_msg("Total segments are {}".format(self.chunks_no))
        
        combo_length = len(combo)
        self.log_msg("Combo length is {}".format(combo_length))

        remaining_s = self.chunks_no - start_index

        assert remaining_s > 0
        self.log_msg("Remaining segments are {}".format(remaining_s))

        assert combo_length < remaining_s
        #sliding_window = [ fr.copy() for fr in self.multilevel_segments[start_index:(start_index + combo_length + 1)] ]
        sliding_window = [ fr for fr in self.multilevel_segments[start_index:(start_index + combo_length + 1)] ]
        
        assert len(sliding_window) == combo_length + 1
   
        current_s = sliding_window[0]

        for i, merge in enumerate(combo):
            next_s = sliding_window[i+1]
            if merge:
                current_s = current_s.merge(next_s, start_index + len(combo_s))
            else:
                combo_s.append(current_s)
                current_s = next_s

            if i == len(combo) - 1:
                combo_s.append(current_s)
        
        return combo_s
 



    def apply(self, start_index, assemble_combo):
        #past_s = [ s.copy() for s in self.multilevel_segments[0: start_index]]
        # past_s is a list of segments past the start_index
        past_s = [ s for s in self.multilevel_segments[0: start_index]]
        self.log_msg("Previous segments are {}".format(len(past_s)))

        # apply_on_window returns a list of segments that are the result of merging the segments in the window
        combo_s = self.apply_on_window(start_index, assemble_combo)
        self.log_msg("Combi segments are {}".format(len(combo_s)))
        #future_s = [ s.copy() for s in self.multilevel_segments[ (start_index + len(assemble_combo) + 1):]]

        # future_s is a list of original segments after the end of the window 
        future_s = [ s for s in self.multilevel_segments[ (start_index + len(assemble_combo) + 1):]]
        self.log_msg("Future segments are {}".format(len(future_s)))
        
        no_merges = assemble_combo.count(True)
        self.log_msg("Number of merges are {}".format(no_merges))
        
        self.log_msg("Past( {} ) + Combo ( {} ) + Future ( {} ) == Pre Combi ( {} ) - N. merges ( {} ) ??".format(len(past_s), len(combo_s), len(future_s), len(self.multilevel_segments), no_merges))
        assert len(past_s) + len(combo_s) + len(future_s) == len(self.multilevel_segments) - no_merges
        

        # return a new MultilevelVideo object with the merged segments list
        return MultilevelVideo( past_s + combo_s + future_s, logger=self.logger)




    def get_simulation_data(self, start=0, end=-1):
        
        assert start >= 0
        
        if end < 0:
            end = self.chunks_no
       
        assert end >= start
        assert end <= self.chunks_no
        simulation_data = {}
        self.log_msg("Loading simulation data {} - {}".format(start, end))
        # get segments simulation data from start to end
        for c in range(start, end):
            s = self.multilevel_segments[c].get_simulation_data(c)  
            simulation_data[c] = s

        return simulation_data
    


    def remove_levels(self, levels_map):
        
        multilevel_segments = []
        
        for c in range(self.chunks_no):
            if c not in levels_map.keys():
                multilevel_segments.append(self.multilevel_segments[c].copy())
            else:
                multilevel_segments.append(self.multilevel_segments[c].remove_levels(levels_map[c]))

        return MultilevelVideo(multilevel_segments, logger=self.logger)

    def add_levels(self, levels_map):
        
        multilevel_segments = []
        
        for c in range(self.chunks_no):
            if c not in levels_map.keys():
                multilevel_segments.append(self.multilevel_segments[c].copy())
            else:
                multilevel_segments.append(self.multilevel_segments[c].add_levels(levels_map[c]))

        return MultilevelVideo(multilevel_segments, logger=self.logger)


    def load_effective_lookahead(self, start_index, lookahead):
        
        self.log_msg("Start index is {}".format(start_index))
        self.log_msg("Lookahead is {}".format(lookahead))
        self.log_msg("Total segments are {}".format(self.chunks_no))
        remaining_s = self.chunks_no - start_index
        self.log_msg("Remaining segments are {}".format(remaining_s))
        effective_lookahead = min(lookahead, remaining_s - 1)
        return effective_lookahead
    


    ### this lookahead is the number of delimiters considered, NOT the number of segments
    ### lookahead =  no_segments - 1
    
    def load_window(self, start_index, lookahead):

        effective_lookahead = self.load_effective_lookahead(start_index, lookahead)
        assert effective_lookahead >= 0
        self.log_msg("Effective lookahead is {}".format(effective_lookahead))
        sliding_window = self.multilevel_segments[start_index:(start_index + effective_lookahead + 1)]

        return sliding_window
 

    def load_durations(self, start_index, lookahead):
        self.log_msg("Selected: load durations")
        self.log_msg("Start index is {}".format(start_index))
        self.log_msg("Lookahead is {}".format(lookahead))

        sliding_window = self.load_window(start_index, lookahead)
        durations = []
  
        for idx, fr in enumerate(sliding_window):
            durations.append(fr.load_duration(idx+start_index))

        return durations

    def load_bytes(self, start_index, lookahead):
        self.log_msg("Selected: load bytes")
        self.log_msg("Start index is {}".format(start_index))
        self.log_msg("Lookahead is {}".format(lookahead))

        sliding_window = self.load_window(start_index, lookahead)
        bytess = []
        
        for idx, fr in enumerate(sliding_window):
            bytess.append(fr.load_bytes(idx+start_index))

        return bytess

    def load_bitrates(self, start_index, lookahead):
        self.log_msg("Selected: load bitrates")
        self.log_msg("Start index is {}".format(start_index))
        self.log_msg("Lookahead is {}".format(lookahead))

        sliding_window = self.load_window(start_index, lookahead)
        bitrates = []
        
        for idx, fr in enumerate(sliding_window):
            bitrates.append(fr.load_bitrate(idx + start_index))

        return bitrates
    
    def load_frames(self, start_index, lookahead):
        self.log_msg("Selected: load frames")
        self.log_msg("Start index is {}".format(start_index))
        self.log_msg("Lookahead is {}".format(lookahead))

        sliding_window = self.load_window(start_index, lookahead)
        framess = []
        
        for idx, fr in enumerate(sliding_window):
            framess.append(fr.load_total_frames(idx + start_index))

        return framess


    def load_delimiters(self):
        self.log_msg("Selected: load delimiters")
        segment_delimiters_timestamps = []
        segment_delimiters_indexes = []

        time_iterator = 0.0
        key_iterator = 0

        for idx, fr in enumerate(self.multilevel_segments):
            segment_delimiters_timestamps.append(time_iterator)
            segment_delimiters_indexes.append(key_iterator)
            
            time_iterator += fr.load_duration(idx)
            key_iterator += fr.load_total_frames(idx)

        return segment_delimiters_indexes, segment_delimiters_timestamps


    def vmaf_list(self, downloaded_sequence, start_segment):
        concat_vmafs = []
        assert start_segment >=0
        end = start_segment + len(downloaded_sequence)
        assert end >= start_segment
        assert end <= self.chunks_no
        for i, c in enumerate(range(start_segment, start_segment + len(downloaded_sequence))):
            level_for_segment_c = downloaded_sequence[i]
            vmaf_list = self.multilevel_segments[c].load_vmaf_list_by_index(c, level_for_segment_c)
            concat_vmafs += vmaf_list
        return concat_vmafs
 
