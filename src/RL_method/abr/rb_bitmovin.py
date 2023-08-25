import logging

B_IN_KB = 1000.0
MS_IN_S = 1000.0
BITS_IN_B = 8.0

REFERENCE_SEGMENT_LENGTH = 4.0
DEPTH = 5
T_STARTUP = 10
PREFERRED_STARTUP_RATE = 1



class Abr():
    def __init__(self, qoe_module, **kwargs):
        self.logger = logging.getLogger("ABR")
        self.step_counter = 0

    def copy(self):
        # stateless
        return self

    def bandwidth_estimator(self, ss):
        buffer_size = ss.history[-1]['buffer_size']
        
        segments_in = 0
        while buffer_size > 0 and (segments_in + 1) <= len(ss.history): ## If we only have positive buffer this becomes problematic
            buffer_size -= ss.history[-(segments_in + 1)]['duration']
            segments_in += 1
        
        assert segments_in > 0,"We should have at least one segment here"

        weighted_sum = 0.0
        DEPTH_ESTIMATE = min(len(ss.history), DEPTH)
        
        samples = 0

        for j in range(DEPTH_ESTIMATE):
            last_chunk_bytes = ss.history[-(j+1)]["bytes"] # bytes
            last_chunk_delay = ss.history[-(j+1)]["delay"] # ms
            last_chunk_bw = last_chunk_bytes/last_chunk_delay # KBps
            
            weight = max(0, 1 - j/segments_in) #It doesn't make sense otherwise
            
            if weight > 0:
                samples += 1

            weighted_sum += last_chunk_bw*weight 
        
        assert samples > 0

        weighted_sum /= samples

        assert weighted_sum >= 0 
        return weighted_sum # KBps


    def suggest_rate(self, simstate, VIDEO_PROPERTIES, chunk_index):
        
        VIDEO_LEVELS = VIDEO_PROPERTIES[chunk_index]["levels"]
        assert len(simstate.history) > 0,"We should have streamed something by now we're at %d " % chunk_index
        estimated_bandwidth = self.bandwidth_estimator(simstate) #KBps
        
        R_MIN = float("inf")
        index_R_MIN = -1

        R_MAX = 0
        index_R_MAX = -1

        for i, level in enumerate(VIDEO_LEVELS):
            r_ith = level["bitrate"]/BITS_IN_B
            if R_MAX < r_ith and r_ith < estimated_bandwidth:
                R_MAX = r_ith
                index_R_MAX = i
            if R_MIN > r_ith:
                R_MIN = r_ith
                index_R_MIN = i
        
        if R_MAX > 0:
            return R_MAX, index_R_MAX
        else:
            return R_MIN, index_R_MIN
            


    def abr(self, simstate, VIDEO_PROPERTIES, chunk_index):
        
        suggested_rate, suggested_rate_index = \
                self.suggest_rate(simstate, VIDEO_PROPERTIES, chunk_index)
        time_elapsed_since_playback_start = \
                simstate.history[-1]["time"]  - simstate.history[0]["time"] 
        time_elapsed_since_playback_start /= MS_IN_S
        VIDEO_LEVELS = VIDEO_PROPERTIES[chunk_index]["levels"]
        if time_elapsed_since_playback_start < T_STARTUP:
            preferred_rate_startup = -1
            try:
                preferred_rate_startup = VIDEO_LEVELS[PREFERRED_STARTUP_RATE]["bitrate"]/BITS_IN_B
            except:
                preferred_rate_startup = VIDEO_LEVELS[PREFERRED_STARTUP_RATE-1]["bitrate"]/BITS_IN_B
            for i, level in reversed(list(enumerate(VIDEO_LEVELS))):
                level_rate = level["bitrate"]/BITS_IN_B
                if i == suggested_rate_index:
                    return suggested_rate_index 
                if level_rate <= preferred_rate_startup:
                    return i
            return len(VIDEO_LEVELS) - 1
        else:
            return suggested_rate_index

    
