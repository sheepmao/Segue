from src.consts.ladders_configs_consts import *
import sys

class Ladders():
    def __init__(self, bitrate_ladders, codec, resolution, fps, logger):
        self.resolution = resolution
        self.codec = codec

        if codec == "h264":
            self.init_bitmovin(bitrate_ladders, resolution, fps, logger)
        elif codec == "vp9":
            self.init_google(bitrate_ladders, resolution, fps, logger)
        else:
            logger.error("Error: unsupported codec")
            sys.exit(-1)


    def init_bitmovin(self, df, resolution, fps, logger):
        logger.debug("Bitmovin initialization method selected")
        row = df[(df[K_LADDER_RESOLUTION] == resolution) & (df[K_LADDER_FPS] == int(round(fps)))].iloc[0]
        try:
            self.target_br = float(row[K_LADDER_TARGET_BR])
            self.min_br = float(row[K_LADDER_MIN_BR])
            self.max_br = float(row[K_LADDER_MAX_BR])

            assert self.min_br > 0
            assert self.max_br >= self.target_br
            assert self.target_br >= self.min_br

        except:
            logger.error("Failed to parse ladders")
            sys.exit(-1)
        
        logger.debug("For resolution {} found max {}, target {} and min {}".format(    resolution, 
                                                                                            self.max_br, 
                                                                                            self.target_br,
                                                                                            self.min_br))
    def init_google(self, df, resolution, fps, logger):
        logger.debug("Google initialization method selected") 
        row = df[(df[K_LADDER_RESOLUTION] == resolution) & (df[K_LADDER_FPS] == int(round(fps)))].iloc[0]
        try:
            self.target_br = float(row[K_LADDER_TARGET_BR])
            self.min_br = float(row[K_LADDER_MIN_BR])
            self.max_br = float(row[K_LADDER_MAX_BR])
            
            assert self.min_br > 0
            assert self.max_br > self.target_br
            assert self.target_br > self.min_br

            self.crf = int(row[K_LADDER_CRF])
            
            assert self.crf > 0

            self.threads_pass_1 = int(row[K_THREADS_PASS_1])
            self.tiles_pass_1 = int(row[K_TILES_PASS_1])
            self.speed_pass_1 = int(row[K_SPEED_PASS_1])
            

            self.threads_pass_2 = int(row[K_THREAD_PASS_2])
            self.tiles_pass_2 = int(row[K_TILES_PASS_2])
            self.speed_pass_2 = int(row[K_SPEED_PASS_2])

            assert self.threads_pass_1 > 0
            assert self.threads_pass_2 > 0

            assert self.tiles_pass_1 >= 0
            assert self.tiles_pass_2 >= 0

            assert self.speed_pass_1 >= 0
            assert self.speed_pass_2 >= 0

        except:
            logger.error("Failed to parse ladders")
            sys.exit(-1)
        
        logger.debug("For resolution {} found max {}, target {} and min {}".format(    resolution, 
                                                                                            self.max_br, 
                                                                                            self.target_br, 
                                                                                            self.min_br))
    def format_cmd_vp9_two_pass(self, logger):
         
         assert self.codec == "vp9", "Cannot call format cmd for vp9 with other codecs"
         logger.debug("Formatting strings for vp9 encoding")

         VOID = "{}"
         
         first_pass =  "ffmpeg -i {} -vf scale={} -b:v {}k \
                       -minrate {}k -maxrate {}k -tile-columns {} -crf {} -threads {} \
                        -quality good  {} -c:v libvpx-vp9 \
                        -pass 1 -speed {} -passlogfile {} -y {}".format( VOID, self.resolution,
                                                                         self.target_br, self.min_br, self.max_br,
                                                                         self.tiles_pass_1, self.crf, self.threads_pass_1, 
                                                                         VOID, self.speed_pass_1, VOID, VOID)
     


         second_pass =   "ffmpeg -i {} -vf scale={} -b:v {}k \
                         -minrate {}k -maxrate {}k -tile-columns {} -crf {} -threads {} \
                         -quality good  {} -c:v libvpx-vp9 \
                         -pass 2 -speed {} -passlogfile {} -y {}".format(    VOID, self.resolution,
                                                                             self.target_br, self.min_br, self.max_br,
                                                                             self.tiles_pass_2, self.crf, self.threads_pass_2,
                                                                             VOID, self.speed_pass_2, VOID, VOID)

         
         logger.debug("Strings formatted")
         logger.debug("Pass 1 : {}".format(first_pass))
         logger.debug("Pass 2 : {}".format(second_pass))
         
         return first_pass, second_pass


         
    def format_cmd_h264_two_pass(self, logger, video_duration):
         assert self.codec == "h264", "cannot call format cmd for h264 with other codecs"
         logger.debug("Computing cmd string for h264 encoding")
         VOID = "{}"

         if self.max_br > self.target_br:
            bufsize = 1.5*self.max_br
         else:
            bufsize = self.target_br * video_duration

         x_pass =    "ffmpeg -i {} -vf scale={} -c:v libx264 \
                     -b:v {}k -maxrate {}k -minrate {}k -bufsize {}k {}".format( VOID, self.resolution, 
                                                                                 self.target_br, self.max_br,
                                                                                 self.min_br, bufsize, VOID)

         
         first_pass = x_pass + ' -pass 1 -f mp4 -passlogfile {} -y /dev/null'
         second_pass = x_pass + ' -pass 2 -passlogfile {} -y {}'

         return first_pass, second_pass
