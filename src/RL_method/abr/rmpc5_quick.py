import numpy as np
import itertools, logging
MPC_FUTURE_CHUNK_COUNT = 5 #  Normally 5
PAST_SAMPLES = 8
M_IN_K = 1000.0
B_IN_MB = 1000000.0


class Abr():
    def __init__(self, qoe_module, **kwargs):
        self.logger = logging.getLogger("ABR")
        self.logger.setLevel(logging.ERROR)
        self.qoe_module = qoe_module
        self.past_bandwidth_ests = np.empty(PAST_SAMPLES)
        self.past_bandwidth_ests.fill(-1)
        self.past_errors = np.empty(PAST_SAMPLES)
        self.past_errors.fill(-1)
        self.past_bandwidths = np.empty(PAST_SAMPLES)
        self.past_bandwidths.fill(-1)

    def copy(self):
        cop = Abr(self.qoe_module)
        cop.past_bandwidth_ests = self.past_bandwidth_ests.copy()
        cop.past_errors = self.past_errors.copy()
        cop.past_bandwidths = self.past_bandwidths.copy()
        return cop

    def retrieve_bandwidth_estimate(self, video_chunk_size, delay):

        raw_bandwidth_estimate = float(video_chunk_size) / float(delay) / M_IN_K 
        curr_error = 0 # defualt assumes that this is the first request so error is 0 since we have never predicted bandwidth
        
        if ( self.past_bandwidth_ests[-1] > 0.0 ):
            curr_error  = abs(self.past_bandwidth_ests[-1] - raw_bandwidth_estimate )/raw_bandwidth_estimate
        
        #self.logger.info("Current error is {}, while raw bandwidth is {}".format(curr_error, raw_bandwidth_estimate))


        self.past_errors = np.roll(self.past_errors, -1)
        self.past_errors[-1] = curr_error
        self.past_bandwidths = np.roll(self.past_bandwidths, -1)
        self.past_bandwidths[-1] = raw_bandwidth_estimate
        
        bandwidth_sum = 0
        n_samples = 0

        for past_val in self.past_bandwidths:
            if past_val > 0:
                bandwidth_sum += (1/float(past_val))
                n_samples += 1

        
        harmonic_bandwidth = 1.0/(bandwidth_sum/n_samples)
        
        # future bandwidth prediction
        # divide by 1 + max of last 8 (previous 5)

        max_error = float(max(self.past_errors))


        if max_error < 0.0:
            max_error = 0

        future_bandwidth = harmonic_bandwidth/(1+max_error)  # robustMPC here
        
        self.past_bandwidth_ests = np.roll(self.past_bandwidth_ests, -1)
        self.past_bandwidth_ests[-1] = harmonic_bandwidth
        
        return future_bandwidth #MBYTES/S


    def recursive_reward(self, available_levels, video_properties, index, layer, curr_buffer, last_quality, future_bandwidth, reward_prev, debug):
        
        if layer == len(available_levels):
            return reward_prev, []
        else:
            previous_vc_level = video_properties[index-1]['levels'][last_quality]
            layer_available_quality = available_levels[layer]
            list_rewards = []
            list_combos = []

            for qual in layer_available_quality:
                temp_buffer = curr_buffer

                current_vc = video_properties[index]
                current_vc_level =  video_properties[index]['levels'][qual]

                download_time = (current_vc_level["bytes"])/future_bandwidth/B_IN_MB # this is MB/MB/s --> seconds
                
                #if debug:
                    #print(download_time, future_bandwidth)
                if ( temp_buffer < download_time ):
                    curr_rebuffer_time = (download_time - temp_buffer)
                    temp_buffer = 0 
                else:
                    temp_buffer -= download_time
                    curr_rebuffer_time = 0
                    
                temp_buffer += current_vc["duration"]
                #self.logger.debug("Current buffer is {}, while rebuffer was {}. Segment added is {}".format(temp_buffer, curr_rebuffer_time, current_vc["duration"]))
                
                
                reward_chunk_current = reward_prev + self.qoe_module.evaluate_reward_per_segment([current_vc_level, previous_vc_level, current_vc, curr_rebuffer_time], debug=False)
                reward_chunk_future = self.recursive_reward(available_levels, video_properties, index +1, layer + 1, temp_buffer,  qual, future_bandwidth, reward_chunk_current, debug)
                
                list_rewards.append(reward_chunk_future[0])
                list_combos.append(reward_chunk_future[1])

            #if debug:
            #    for i, rew in enumerate(list_rewards):
            #        print("Combo {}, rew {}".format([i] + list_combos[i], rew))
            
            
            max_reward = max(list_rewards)
            max_index = list_rewards.index(max_reward)
            max_combo = [max_index] + list_combos[max_index]
            return max_reward, max_combo
            


    def abr(self, simstate, VIDEO_PROPERTIES, chunk_index):

        last_index = chunk_index - 1
        TOTAL_VIDEO_CHUNKS = len(VIDEO_PROPERTIES)
        future_chunk_length = MPC_FUTURE_CHUNK_COUNT
        
        if ( TOTAL_VIDEO_CHUNKS - last_index - 1 < future_chunk_length ):
                future_chunk_length = TOTAL_VIDEO_CHUNKS - last_index - 1

        available_quality_levels = []

        for x in range(chunk_index, chunk_index + future_chunk_length):
            A_DIM = VIDEO_PROPERTIES[x]["n_levels"]
            available_quality_levels.append([i for i in range(A_DIM)])
        
        he = simstate.history[-1]
        last_video_chunk_size = he['bytes']
        last_video_chunk_delay = he["delay"]
        last_bit_rate_level = he["level"]
        buffer_size = he['buffer_size']
        #self.logger.info("Using LAST bytes={}, delay={}, level={}, buffer_size={}".format(he['bytes'], he['delay'], he['level'], he['buffer_size']))
        
        debug = False
        if chunk_index == 16:
            debug = True
 
        future_bandwidth = self.retrieve_bandwidth_estimate(last_video_chunk_size, last_video_chunk_delay)
        max_reward, max_combo = self.recursive_reward(available_quality_levels, VIDEO_PROPERTIES, chunk_index, 0, buffer_size, last_bit_rate_level, future_bandwidth, 0, debug)
        if chunk_index == len(VIDEO_PROPERTIES) - 1:
            #self.logger.info("Last chunk reached: resetting bandwidth estimate state")

            self.past_bandwidth_ests = np.empty(PAST_SAMPLES)
            self.past_bandwidth_ests.fill(-1)
            self.past_errors = np.empty(PAST_SAMPLES)
            self.past_errors.fill(-1)
            self.past_bandwidths = np.empty(PAST_SAMPLES)
            self.past_bandwidths.fill(-1)

        #self.logger.info("Chose level = {}".format(max_combo[0]))
        return max_combo[0]
    
