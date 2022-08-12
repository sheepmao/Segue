import pandas as pd
from abc import ABC, abstractmethod
from src.grouper.grouping_policies.grouper_optimizer.grouper_optimizer import GrouperOptimizer
import numpy as np
import math
from datetime import datetime

LOOK_PAST_ALL = -1

class GrouperSimulationOptimizer(GrouperOptimizer):
    
    def __init__(   self, look_ahead, multi_res_fragments, logger_name, log_file, ss_set,
                    reward, look_past=LOOK_PAST_ALL, look_future=0, verbose=False):
        super().__init__(look_ahead, multi_res_fragments, logger_name, log_file, verbose=verbose)
        
        self.logger.debug("Creating grouper simulation optimizer")
        
        self.real_set = ss_set
        assert len(self.real_set.ss_set) > 0
        self.logger.debug("Simulation set contains {} traces".format(len(self.real_set.ss_set)))

        self.reward = reward
        assert self.reward is not None
        
        self.look_past = look_past
        self.look_future = look_future
        
        self.logger.debug("Computing with a look ahead of {}".format(look_ahead))
        self.logger.debug("Computing with a look at the future of  {}".format(look_future))
        self.logger.debug("Computing with a look past of {} (if negative, all)".format(look_past))
    

    def actions_on_not_merge(self):
        self.start_segment += 1
        self.real_set.step(self.fragments.get_simulation_data(start=0)) # sensitive

    def combo_reward(self, combo_args):
        combo_fragments = combo_args[0]
        combo = combo_args[1]
        
        sim_ss = self.real_set.copy()
        init_pos = sim_ss.get_chunk_index()
        sim_steps = combo.count(False) + 1
        
        self.logger.debug("Retrieving simulation data from {} and {}".format(0, init_pos + sim_steps + self.look_future))
        if self.look_past > 0:
            start_segment = max(0, init_pos - self.look_past)
        else:
            start_segment = 0
        
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
