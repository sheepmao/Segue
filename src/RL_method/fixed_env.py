

# This code has been readapted from the one made available in https://github.com/hongzimao/pensieve



import numpy as np
import logging, ntpath
from src.utils.logging.logging_segue import create_logger
MILLISECONDS_IN_SECOND = 1000.0
B_IN_MB = 1000000.0
BITS_IN_BYTE = 8.0
RANDOM_SEED = 42
#VIDEO_CHUNCK_LEN = 4000.0  # millisec, every time add this amount to buffer  Pensieve original use fixed chunk length
BUFFER_THRESH = 60.0 * MILLISECONDS_IN_SECOND  # millisec, max buffer limit
DRAIN_BUFFER_SLEEP_TIME = 500.0  # millisec
PACKET_PAYLOAD_PORTION = 0.95
LINK_RTT = 80  # millisec
PACKET_SIZE = 1500  # bytes
BUFFER_STARTUP = 10.0


# Data structure per chunk:
# chunk_progressive - chunk_duration (time) - number of layers available - list of availability:
# per available, ordered by bitrate [ chunk size byte, chunk bitrate (kbit/s), vmaf score, resolution ]



class Environment:
    def __init__(self, trace, random_seed=RANDOM_SEED):
        self.random_seed = random_seed
        np.random.seed(self.random_seed)
        self.logger = logging.getLogger('Controller.StreamEnvironment') 
        self.logger.setLevel(logging.ERROR) # DEBUG, INFO, WARNING, ERROR, CRITICAL
        self.buffer_size = 0
        self.mahimahi_ptr = 1
        self.cooked_time, self.cooked_bw = trace[0], trace[1]
        self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr - 1]
        self.startup = True

    def debug_print(self):
        dd = dict(self.__dict__) 
        del dd['cooked_time']
        del dd['cooked_bw']
        return "E{} => {}".format(id(self), dd)

    def copy(self):
        c = Environment((self.cooked_time, self.cooked_bw), random_seed=self.random_seed)
        c.logger = self.logger
        c.buffer_size = self.buffer_size
        c.mahimahi_ptr = self.mahimahi_ptr
        c.last_mahimahi_time = self.last_mahimahi_time
        c.startup = self.startup
        return c

    def fetch_chunk(self, chunk_size, chunk_duration):
        chunk_duration *= MILLISECONDS_IN_SECOND
        self.logger.info(" Fetch chunk size={}  and  duration={}".
                format(chunk_size, chunk_duration))

        # use the delivery opportunity in mahimahi
        delay = 0.0  # in ms
        video_chunk_counter_sent = 0  # in bytes

        while True:  # download video chunk over mahimahi
            throughput = self.cooked_bw[self.mahimahi_ptr] \
                         * B_IN_MB / BITS_IN_BYTE
            duration = self.cooked_time[self.mahimahi_ptr] \
                       - self.last_mahimahi_time

            packet_payload = throughput * duration * PACKET_PAYLOAD_PORTION

            if video_chunk_counter_sent + packet_payload > chunk_size:

                fractional_time = (chunk_size - video_chunk_counter_sent) / \
                                  throughput / PACKET_PAYLOAD_PORTION
                delay += fractional_time
                self.last_mahimahi_time += fractional_time
                break

            video_chunk_counter_sent += packet_payload
            delay += duration
            self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr]
            self.mahimahi_ptr += 1

            if self.mahimahi_ptr >= len(self.cooked_bw):
                # loop back in the beginning
                # note: trace file starts with time 0
                self.mahimahi_ptr = 1
                self.last_mahimahi_time = 0

        delay *= MILLISECONDS_IN_SECOND
        delay += LINK_RTT
        
        self.logger.info("Download took {} ms".format(delay))
        
        if not self.startup:
            # rebuffer time
            rebuf = np.maximum(delay - self.buffer_size, 0.0)
            # update the buffer
            self.buffer_size = np.maximum(self.buffer_size - delay, 0.0)
        # add in the new chunk
            self.buffer_size += chunk_duration
        else:
            rebuf = delay
            self.buffer_size += chunk_duration
            if self.buffer_size >= BUFFER_STARTUP*MILLISECONDS_IN_SECOND:
                self.startup = False

        self.logger.info("Rebuffering: {}, Current buffer size: {}".format(rebuf, self.buffer_size))

        # sleep if buffer gets too large
        sleep_time = 0
        if self.buffer_size > BUFFER_THRESH:
            # exceed the buffer limit
            # we need to skip some network bandwidth here
            # but do not add up the delay
            drain_buffer_time = self.buffer_size - BUFFER_THRESH
            sleep_time = np.ceil(drain_buffer_time / DRAIN_BUFFER_SLEEP_TIME) * \
                         DRAIN_BUFFER_SLEEP_TIME
            self.buffer_size -= sleep_time

            while True:
                duration = self.cooked_time[self.mahimahi_ptr] \
                           - self.last_mahimahi_time
                if duration > sleep_time / MILLISECONDS_IN_SECOND:
                    self.last_mahimahi_time += sleep_time / MILLISECONDS_IN_SECOND
                    break
                sleep_time -= duration * MILLISECONDS_IN_SECOND
                self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr]
                self.mahimahi_ptr += 1

                if self.mahimahi_ptr >= len(self.cooked_bw):
                    # loop back in the beginning
                    # note: trace file starts with time 0
                    self.mahimahi_ptr = 1
                    self.last_mahimahi_time = 0

        # the "last buffer size" return to the controller
        # Note: in old version of dash the lowest buffer is 0.
        # In the new version the buffer always have at least
        # one chunk of video
        return_buffer_size = self.buffer_size
        
        self.logger.info("Sleeping time of {}, new buffer size is {}".format(sleep_time, self.buffer_size))
        return {'delay' : delay, 
                'sleep_time' : sleep_time, 
                'buffer_size' : return_buffer_size / MILLISECONDS_IN_SECOND, 
                'rebuf' : rebuf / MILLISECONDS_IN_SECOND }
