import pandas as pd
from abc import ABC, abstractmethod
from src.grouper.grouping_policies.grouper_optimizer.grouper_wide_eye_optimizer import GrouperWideEyeOptimizer
import numpy as np
import math
from datetime import datetime

LOOK_PAST_ALL = -1

# Simulation Optimized - Time-Bytes Filtered ==> SOTBF

class GrouperWideEyeSOTBF(GrouperWideEyeOptimizer):
    
    def __init__(   self, look_ahead, step, combo_per_step, multi_res_fragments, logger_name, log_file, ss_set,
                    reward, target_time, target_bytes, template_res_index, look_past=LOOK_PAST_ALL, look_future=0, max_length=-1, verbose=False):
        super().__init__(look_ahead, step, combo_per_step, multi_res_fragments, logger_name, log_file, verbose=verbose)
        
        self.logger.debug("Creating grouper simulation optimizer")
        
        self.real_set = ss_set
        assert len(self.real_set.ss_set) > 0
        self.logger.debug("Simulation set contains {} traces".format(len(self.real_set.ss_set)))

        self.reward = reward
        assert self.reward is not None
        
        self.look_past = look_past
        self.look_future = look_future
        self.target_time = target_time
        self.target_bytes = target_bytes
        self.template_res_index = template_res_index
        self.max_length = max_length
        
        self.logger.debug("Computing with a look ahead of {}".format(look_ahead))
        self.logger.debug("Computing with a look at the future of  {}".format(look_future))
        self.logger.debug("Computing with a look past of {} (if negative, all)".format(look_past))
    
    
    def apply_winning_combo(self):
        index_max = min(self.step, len(self.winning_combo))
        combo_to_apply = self.winning_combo[0:index_max]
        self.fragments = self.fragments.apply(self.start_segment, combo_to_apply)
        seg_step =  combo_to_apply.count(False)
        
        if seg_step > 0:
            self.start_segment += seg_step
            sim_data = self.fragments.get_simulation_data(start=0, end=-1)
            self.real_set.step_n(sim_data, seg_step, -1, -1)
    
    

    def time_bytes_scored(self, combo, start_segment):
        
        combo_fragments = self.fragments.apply(start_segment, combo)
        merges_no = combo.count(True)
        combo_lookahead = len(combo) - merges_no 

        bytess = [x[self.template_res_index] for x in combo_fragments.load_bytes(start_segment, combo_lookahead)]
        timess = combo_fragments.load_durations(start_segment, combo_lookahead)
        
        if self.max_length > 0 and max(timess) > self.max_length:
            return float(math.inf)

        distance_from_minimum = 1 + abs(min(timess) - self.target_time)
        distance_from_maximum = 1 + abs(max(timess) - self.target_time)
        median = np.percentile(timess, 50)
        distance_from_median = 1 + abs(median - self.target_time)
        reward_time = distance_from_median + distance_from_minimum + 1.2*distance_from_maximum
        
        max_bytes = max(bytess)
        reward_bytes =  max_bytes/self.target_bytes

        reward = reward_bytes + reward_time

        return reward



    def prefilter_combos(self, combos, s_lookahead):
        data_combo = []
        
        for combo in combos:
            score = self.time_bytes_scored(combo, self.start_segment)
            data_combo.append( ( combo, score ) )
        
        sorted_combos = sorted(data_combo, key=lambda x: x[1])
        k = math.ceil(self.combos_per_step * pow(2, s_lookahead) / pow(2, self.look_ahead))
        combos_no = int(min(k, len(sorted_combos)))
        self.logger.info("Considering {} combos".format(combos_no))
        return [ c[0] for c in sorted_combos[:combos_no]]


    def combo_reward(self, combo_args):
        combo_fragments = combo_args[0]
        combo = combo_args[1]
        
        sim_ss = self.real_set.copy()
        init_pos = sim_ss.get_chunk_index()
        sim_steps = combo.count(False) + 1
        if self.look_past > 0:
            start_segment = max(0, init_pos - self.look_past)
        else:
            start_segment = 0
        
        self.logger.debug("Retrieving simulation data from {} and {}".format(0, init_pos + sim_steps + self.look_future))
        
        sim_data = combo_fragments.get_simulation_data(start=0, end=-1)
        end_segment = min(init_pos + sim_steps + self.look_future, len(sim_data))
        r = sim_ss.step_n(sim_data, sim_steps + self.look_future, start_segment, end_segment)
        return r
    




    def compare_rewards(self, reward, combo):
        if reward > self.winning_reward:
            self.winning_reward = reward
            self.winning_combo = combo


    def initialize_reward(self):
        return -1*float(math.inf)
