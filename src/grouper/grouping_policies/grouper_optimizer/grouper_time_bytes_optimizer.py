import pandas as pd
from abc import ABC, abstractmethod
from src.grouper.grouping_policies.grouper_optimizer.grouper_optimizer import GrouperOptimizer
import numpy as np
import math

class GrouperTimeBytesOptimizer(GrouperOptimizer):
    
    def __init__(self, look_ahead, fragments, logger_name, log_file, target_time, target_bytes, verbose=False):
        super().__init__(look_ahead, fragments, logger_name, log_file, verbose=verbose)
        self.target_time = target_time
        self.target_bytes = target_bytes
    
    def combo_reward(self, combo_args):
        
        combo_fragments = combo_args[0]
        combo = combo_args[1]
        
        merges_no = combo.count(True)
        combo_lookahead = self.look_ahead - merges_no

        bytess = [x[0] for x in combo_fragments.load_bytes(self.start_segment, combo_lookahead)]
        timess = combo_fragments.load_durations(self.start_segment, combo_lookahead)

        
        self.logger.debug("Bytes are {}".format(bytess))
        self.logger.debug("Times are {}".format(timess))

        distance_from_minimum = 1 + abs(min(timess) - self.target_time)
        self.logger.debug("Distance from minimum (time) = {}".format(distance_from_minimum))

        distance_from_maximum = 1 + abs(max(timess) - self.target_time)
        self.logger.debug("Distance from maximum (time) = {}".format(distance_from_maximum))
        
        median = np.percentile(timess, 50)
        distance_from_median = 1 + abs(median - self.target_time)
        self.logger.debug("Distance from median (time) = {}".format(distance_from_median))

        
        reward_time = distance_from_median + distance_from_minimum + 1.2*distance_from_maximum
        self.logger.debug("Reward (time) = {}".format(reward_time))
        
        max_bytes = max(bytess)
        self.logger.debug("Max bytes of sequence = {}".format(max_bytes))

        reward_bytes =  max_bytes/self.target_bytes
        self.logger.debug("Reward (bytes) = {}".format(reward_bytes))

        reward = reward_bytes + reward_time
        self.logger.debug("Reward = {}".format(reward))

        return reward


    def compare_rewards(self, reward, combo):
        if reward < self.winning_reward:
            self.winning_reward = reward
            self.winning_combo = combo


    def initialize_reward(self):
        return float(math.inf)
