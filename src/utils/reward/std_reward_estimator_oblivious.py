from src.consts.reward_consts import *
import numpy as np
from src.consts.simulation_file_consts import *
from src.utils.reward.reward_estimator import RewardEstimator
THREADS =  24
from itertools import product
from multiprocessing import Pool

def reward_helper(ss, args):
    reward_module, state, start_segment, end_segment = args
    hist = ss.history[start_segment:end_segment]
    downloaded_sequence = [x['level'] for x in hist]
    rebuffering_time = [x['rebuf'] for x in hist]
    reward = reward_module.evaluate_reward_per_unit_time([  state.vmaf_list(downloaded_sequence, start_segment),
                                                            rebuffering_time ])
    return reward

class STDRewardEstimatorOblivious(RewardEstimator):

    def __init__(self, logger, fps, args):
        
        super().__init__(logger)
        
        self.logger.debug("Reward module initialization")
        
        self.fps = fps
        assert self.fps > 0
        
        self.logger.debug("fps = {}".format(self.fps))

        
        self.unit_time = args[REWARD_UNIT_TIME]
        assert self.unit_time > 0
        self.logger.debug("Unit time = {}".format(self.unit_time))


        self.rebuffering_penalty = args[REWARD_REBUFFERING_PENALTY]
        assert self.rebuffering_penalty > 0
        self.logger.debug("Rebuffering penalty = {}".format(self.rebuffering_penalty))

        
        self.switching_penalty = args[REWARD_SWITCHING_PENALTY]
        assert self.switching_penalty > 0
        self.logger.debug("Switching penalty = {}".format(self.switching_penalty))
        
        self.vmaf_gain = args[REWARD_VMAF_GAIN]
        assert self.vmaf_gain > 0
        self.logger.debug("VMAF gain = {}".format(self.vmaf_gain))
        
        
        self.time_normalization_factor = args[REWARD_TIME_NORMALIZATION_FACTOR]
        assert self.time_normalization_factor > 0
        self.logger.debug("Time normalization factor = {}".format(self.time_normalization_factor))
        

        self.rebuffering_penalty_bitrate = args[REWARD_REBUFFERING_PENALTY_BITRATE]
        self.switching_penalty_bitrate = args[REWARD_SWITCHING_PENALTY_BITRATE]
        self.bitrate_gain = args[REWARD_BITRATE]
        
        assert self.rebuffering_penalty_bitrate > 0
        assert self.switching_penalty_bitrate > 0
        assert self.bitrate_gain > 0
        
        if REWARD_AGGREGATE_MEAN in args.keys():
            self.reward_aggregate_mean = args[REWARD_AGGREGATE_MEAN]
            self.logger.debug("Aggregate mean: {}".format(self.reward_aggregate_mean))
        else:
            self.reward_aggregate_mean = False
            self.logger.debug("Aggregate mean: {}".format(self.reward_aggregate_mean))



    def copy(self):
        args = {}
        args[REWARD_UNIT_TIME] = self.unit_time
        args[REWARD_REBUFFERING_PENALTY] =  self.rebuffering_penalty 
        args[REWARD_SWITCHING_PENALTY] = self.switching_penalty 
        args[REWARD_VMAF_GAIN] = self.vmaf_gain  
        args[REWARD_TIME_NORMALIZATION_FACTOR] =  self.time_normalization_factor
        args[REWARD_REBUFFERING_PENALTY_BITRATE] = self.rebuffering_penalty_bitrate
        args[REWARD_SWITCHING_PENALTY_BITRATE] = self.switching_penalty_bitrate
        args[REWARD_BITRATE] = self.bitrate_gain
        args[REWARD_AGGREGATE_MEAN] =  self.reward_aggregate_mean
        return STDRewardEstimatorOblivious(self.logger, self.fps, args)
    

    def evaluate_reward_from_simulation_set(self, sim_set, state,
                                            start_segment, end_segment, use_pool = False):
        
        rewards = []
        self.logger.debug("Evaluating reward from simulation set. Cardinality: {}".format(len(sim_set.ss_set)))
        tasks = product(sim_set.ss_set, [(self, state, start_segment, end_segment)])
        if use_pool:
            with Pool(THREADS) as pool:
                rewards = pool.starmap(reward_helper, tasks)
        else:
            rewards = [ reward_helper(ss, args) for ss, args in tasks ]
        return self.aggregate_rewards(rewards)

    
    def aggregate_rewards(self, rewards):
        if self.reward_aggregate_mean:
            return np.mean(rewards)
        else:
            return np.percentile(rewards, 1) + np.percentile(rewards, 50)

    
    # oblivious RMPC
    # per second, it evaluates with the selected VMAF model
    # per segment, it evaluates with bitrate constraints

    def evaluate_reward_per_segment(self, args, debug=False):
        
        level_current = args[0]
        level_previous = args[1]
        segment = args[2]
        rebuf = args[3]


        if level_previous is not None:
            bitrate_diff_curr = (np.abs(level_previous[SIM_FILE_BITRATE] - level_current[SIM_FILE_BITRATE]))/1000.0 #mbits
        else:
            bitrate_diff_curr = 0

        segment_duration =  segment[SIM_FILE_DURATION]
        
        bitrate_reward_normalization = self.bitrate_gain*segment_duration/self.time_normalization_factor
        
        reward =    level_current[SIM_FILE_BITRATE]*bitrate_reward_normalization/1000.0 \
                    - self.rebuffering_penalty_bitrate * rebuf \
                    - self.switching_penalty_bitrate * bitrate_diff_curr

        return reward


    def evaluate_reward_per_unit_time(  self, args, return_list=False):
        vmaf_sequence = args[0]
        rebuffering = args[1]

        total_seconds = 0
        total_vmaf = 0
        frames_count = 0

        previous_vmaf = -1
        vmaf_list = []
        vmaf_switch = []
        regroup_each =  self.fps*self.unit_time
        

        for i, vmaf in enumerate(vmaf_sequence):
            frames_count += 1
            total_vmaf += vmaf

            if  frames_count >= regroup_each or i == len(vmaf_sequence) - 1:
                normalization_factor_last_segment = frames_count/regroup_each

                vmaf_second_unweighted = total_vmaf/frames_count
                vmaf_second = total_vmaf/frames_count*normalization_factor_last_segment
                vmaf_list.append(vmaf_second)
                
                if previous_vmaf > 0:
                    s = abs(vmaf_second_unweighted - previous_vmaf)*normalization_factor_last_segment
                    vmaf_switch.append(s)

                previous_vmaf = vmaf_second
                frames_count = 0
                total_vmaf = 0

        time_normalization = self.unit_time / self.time_normalization_factor
        assert len(vmaf_list) == len(vmaf_switch) + 1
        reward = self.vmaf_gain*time_normalization *sum(vmaf_list) - self.switching_penalty*sum(vmaf_switch) - self.rebuffering_penalty*sum(rebuffering)
        if return_list:
            return vmaf_list, vmaf_switch, reward
        else:
            return reward
