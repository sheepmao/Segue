from abc import ABC, abstractmethod

class RewardEstimator(ABC):
    def __init__(self, logger):
        self.logger = logger
        pass
    

    @abstractmethod
    def copy():
        pass

    @abstractmethod
    def evaluate_reward_from_simulation_set(self, sim_set, state):
        pass

    @abstractmethod
    def evaluate_reward_per_unit_time(self, args):
        pass

    @abstractmethod
    def evaluate_reward_per_segment(self, args):
        pass
