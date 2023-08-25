import sys,logging
import math
CUSHION_SEGMENTS = 5

class Abr():
    def __init__(self, qoe_module):
        self.logger = logging.getLogger("ABRController.ABR")
        #self.hardcoded_bitrates = (5500, 8500) 
        self.hardcoded_bitrates = (400, 8000) 

    def copy(self):
        # stateless
        return self

    def debug_print(self):
        return "A{} => {}".format(id(self), self.__dict__)

    def abr(self, simstate, VIDEO_PROPERTIES, chunk_index):
        AVERAGE_BR_LB = 0
        AVERAGE_BR_UB = 0
        
        total_dur = 0

        AVERAGE_BR_LB = self.hardcoded_bitrates[0]
        AVERAGE_BR_UB = self.hardcoded_bitrates[1]
        
        BITRATE_EXPANSION_FACTOR_RESEVOIR_LB = VIDEO_PROPERTIES[chunk_index]['levels'][0]['bitrate']/AVERAGE_BR_LB
        BITRATE_EXPANSION_FACTOR_RESEVOIR_UB = VIDEO_PROPERTIES[chunk_index]['levels'][-1]['bitrate']/AVERAGE_BR_UB
        
        RESEVOIR_EXPANSION_FACTOR_RATE = BITRATE_EXPANSION_FACTOR_RESEVOIR_LB 
        
        LAST_SEGMENT_DURATION = VIDEO_PROPERTIES[chunk_index - 1]['duration']
        CURRENT_SEGMENT_DURATION = VIDEO_PROPERTIES[chunk_index]['duration']
        

        RESEVOIR_TEMP = min(140, max(8, 8*RESEVOIR_EXPANSION_FACTOR_RATE))
        CUSHION_TEMP = CUSHION_SEGMENTS * 4.0
        
        LEVELS_NO = VIDEO_PROPERTIES[chunk_index]["n_levels"] # number of levels(sum of each resolutions * it's level->if not use agmantation -> 1) in the chunk
        LEVELS = VIDEO_PROPERTIES[chunk_index]["levels"] # list of dictionaries, each dictionary is a level with its properties 
        #ex:   [{"resolution": "640x360", "bytes": 330668, "bitrate": 529.0688,etc},{resolution: "960x540", bytes: 660668, bitrate: 829.0688,etc},..]
        DATA = []
        
        last_resolution = -1

        INDEXES = [] # list of resolution level indexes ex:(0-4)
        RESOLUTION_LIST = [] # list of resolutions in the chunk

        # create a list of indexes for each resolution and level in the current chunk 
        for i, level in enumerate(LEVELS):
            if level['resolution'] != last_resolution:
                if INDEXES:
                    DATA.append(INDEXES)
                INDEXES = [i]
                last_resolution = level['resolution']
                RESOLUTION_LIST.append(last_resolution)
            else:
                INDEXES.append(i)
       
       # DATA is a list of lists, each list contains the indexes of the levels of a resolution
        DATA.append(INDEXES)
        A_DIM = len(DATA)
        

        self.logger.info("Video chunk {} has {} resolutions".format(chunk_index, A_DIM))
        for i, indexes in enumerate(DATA):
            self.logger.info("Resolution {} has {} levels".format(i, len(indexes)))
        
     
        self.logger.info('Resevoir is {} while Cushion is {}'.format(RESEVOIR_TEMP, CUSHION_TEMP))
        
        buffer_size = simstate.history[-1]['buffer_size']
        last_level = simstate.history[-1]['level']
        self.logger.info('buffer_size = {}   last_level = {}'.format(buffer_size, last_level))
        last_resolution = VIDEO_PROPERTIES[chunk_index - 1]['levels'][last_level]['resolution']
        
        if last_resolution not in RESOLUTION_LIST:
            RESOLUTION_LIST.append(last_resolution)
            RESOLUTION_LIST = sorted(RESOLUTION_LIST, key= lambda x: int(x.split('x')[0]))
        last_resolution_index = RESOLUTION_LIST.index(last_resolution)

        if last_resolution == RESOLUTION_LIST[-1]:
            R_MAX = A_DIM - 1
        else:
            R_MAX = last_resolution_index + 1
        
        if last_resolution == RESOLUTION_LIST[0]:
            R_MIN = 0
        else:
            R_MIN = last_resolution_index - 1



        if buffer_size < RESEVOIR_TEMP:
                bit_rate = 0
        elif buffer_size >= RESEVOIR_TEMP + CUSHION_TEMP:
                bit_rate = LEVELS_NO - 1
        else:
                f_buf_now = (A_DIM - 1) * (buffer_size - RESEVOIR_TEMP) / float(CUSHION_TEMP)
                #resolution_index = int(resolution)
                
                pull_up = False
                pull_down = False

                if f_buf_now >= R_MAX:
                    resolution_index = int( math.floor(f_buf_now) )
                    pull_up = True
                elif f_buf_now <= R_MIN:
                    resolution_index = int( math.ceil(f_buf_now) ) 
                    pull_down = True
                else:
                    resolution_index = last_resolution_index


                if len(DATA[resolution_index]) == 1:
                    bit_rate = DATA[resolution_index][0]
                else:
                    
                    level_available = len(DATA[resolution_index])
                    
                    if pull_up:
                        level_index = level_available - 1
                    elif pull_down:
                        level_index = 0
                    else:
                        delta = f_buf_now - R_MIN
                        if resolution_index > 0 and resolution_index < (A_DIM - 1):
                            delta /= 2.0                  # outermost buckets are already in range [0,1[
                        level_index = int(delta * level_available)
                        assert level_index < level_available
                    bit_rate = DATA[resolution_index][level_index]

        
        self.logger.info("Chunk {} selected at quality {}".format(chunk_index, int(bit_rate)))
        return int(bit_rate)
