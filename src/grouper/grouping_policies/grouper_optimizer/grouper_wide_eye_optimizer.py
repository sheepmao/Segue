import pandas as pd
from itertools import product
from abc import ABC, abstractmethod
from src.utils.logging.logging_segue import create_logger
from datetime import datetime
import sys

class GrouperWideEyeOptimizer(ABC):
    
    def __init__(self, look_ahead, step, combo_per_step, fragments, logger_name, log_file, verbose=False):
        
        self.look_ahead = look_ahead # how many keyframes I am considering
        self.step = step # how many step I'm moving on
        self.combos_per_step = combo_per_step # filtering cardinality: how many of the combos I'm considering

        self.fragments = fragments
        self.total_keyframes = self.fragments.chunks_no

        self.start_segment = 0
        self.logger = create_logger(logger_name, log_file, verbose=verbose)
        
        self.winning_reward = None
        self.winning_combo = None


    @abstractmethod
    def combo_reward(self, combo_args):
        pass
    
    def apply_combo(self, combo):
       return self.fragments.apply(self.start_segment, combo), combo

    @abstractmethod
    def compare_rewards(self, reward, combo):
        pass

    def apply_winning_combo(self):
        index_max = min(self.step, len(self.winning_combo))
        combo_to_apply = self.winning_combo[0:index_max]
        self.fragments = self.fragments.apply(self.start_segment, combo_to_apply, -1, -1)
        self.start_segment += combo_to_apply.count(False)
    
    @abstractmethod
    def initialize_reward(self):
        pass
    
    def effective_lookahead(self):
        return self.fragments.load_effective_lookahead(self.start_segment, self.look_ahead)
    
    def return_suboptimal(self):
        return self.fragments.load_delimiters()


    @abstractmethod
    def prefilter_combos(self, combos):
        pass
    
    def compute_suboptimal(self):
        self.logger.info("Starting suboptimal optimization")
        options = [True, False]
        
        iterator = 0

        if self.start_segment != 0:
            self.logger.debug("Already computed suboptimal")
            return
        while True:
                
            self.winning_reward = self.initialize_reward()
            self.winning_combo = None

            s_lookahead = self.effective_lookahead()
            
            if s_lookahead == 0:
                break
            
            combos = list(product(options,repeat=s_lookahead))
            effective_combos = self.prefilter_combos(combos, s_lookahead)
            self.logger.info("Prefiltering completed. {} combos have been computed".format(len(effective_combos)))
            for combo in effective_combos:
                self.logger.debug("Checking combo={}".format(combo))
                combos_args = self.apply_combo(combo)
                reward = self.combo_reward(combos_args)
                self.logger.debug("Combo reward={}  {}".format(reward, "best so far" if reward < self.winning_reward else "not best"))
                self.compare_rewards(reward, combo)
            self.logger.info("winning combo is {}".format(self.winning_combo))
            self.logger.info("Winning combo was ranked {}".format(effective_combos.index(self.winning_combo)))
            assert self.winning_combo != None
            self.apply_winning_combo()
            iterator += self.step
            self.logger.info("Iterator => {}, remaining => {}".format(iterator/self.step, (self.total_keyframes - iterator)/self.step))
