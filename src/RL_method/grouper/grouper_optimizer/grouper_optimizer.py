import pandas as pd
from itertools import product
from abc import ABC, abstractmethod
from src.utils.logging.logging_segue import create_logger
from datetime import datetime
import sys

class GrouperOptimizer(ABC):
    
    def __init__(self, look_ahead, fragments, logger_name, log_file, verbose=False):
        
        self.look_ahead = look_ahead
        self.fragments = fragments
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

    def actions_on_merge(self):
        self.fragments = self.fragments.apply(self.start_segment, [True])

    def actions_on_not_merge(self):
        self.start_segment += 1

    @abstractmethod
    def initialize_reward(self):
        pass
    
    def effective_lookahead(self):
        return self.fragments.load_effective_lookahead(self.start_segment, self.look_ahead)
    
    def return_suboptimal(self):
        return self.fragments.load_delimiters()
    
    def compute_suboptimal(self):
        self.logger.info("Starting suboptimal optimization")
        options = [True, False]
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
            for combo in combos:
                self.logger.debug("Checking combo={}".format(combo))
                #s1 = datetime.now()
                combos_args = self.apply_combo(combo)
                #s2 = datetime.now()
                reward = self.combo_reward(combos_args)
                s3 = datetime.now()
                self.logger.debug("Combo reward={}  {}".format(reward, "best so far" if reward < self.winning_reward else "not best"))
                self.compare_rewards(reward, combo)

            assert self.winning_combo != None
            self.logger.info("Winning combo is {} with reward {}".format(self.winning_combo, self.winning_reward))
            if self.winning_combo[0] == False: # do not merge checkpoint
                self.logger.info("Winning combo doesn't merge the first checkpoint")
                self.actions_on_not_merge()
            else:
                self.logger.info("Winning combo merges first checkpoint")
                self.actions_on_merge()

