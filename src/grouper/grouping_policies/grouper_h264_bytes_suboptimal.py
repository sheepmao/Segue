from src.utils.video.multilevel_video_factory import MultilevelVideoFactory
import pandas as pd
import tempfile, os, sys
from src.consts.keys_consts import *

from src.consts.grouper_configs_consts import *
from src.consts.video_configs_consts import *

from src.grouper.grouping_policies.grouper_policy import GrouperPolicy
from src.grouper.grouping_policies.grouper_optimizer.grouper_bytes_optimizer import GrouperBytesOptimizer
from src.utils.video_factory import Video, FullVideo, EXTENSION

M_IN_K = 1000.0
B_IN_BYTES = 8

class BytesOptimizedGrouperPolicy(GrouperPolicy):
    def __init__(   self, 
                    grouper_data,
                    video_data,
                    video_obj,
                    rescaled_dir_template,
                    verbose,
                    logs_dir,
                    figs_dir):
        
        super().__init__(   grouper_data,
                            video_data,
                            video_obj,
                            rescaled_dir_template,
                            verbose,
                            logs_dir,
                            figs_dir)
        
        try:

            self.logger.info("Bytes optimizer grouper created")
            
            self.bitrate_ladders_file = grouper_data[K_PARAMETERS_GROUPER][K_BITRATE_LADDERS_GROUPER]
            self.logger.info("Bitrate ladders retrieved at {}".format(self.bitrate_ladders_file))
            
            
            self.gop_seconds = float(grouper_data[K_PARAMETERS_GROUPER][K_GOP_SECONDS_GROUPER])
            self.logger.info("Desired gop : {}".format(self.gop_seconds))
            
            
            self.target_bytes_length_seconds = float(grouper_data[K_PARAMETERS_GROUPER][K_TARGET_SEGMENT_BYTES_LENGTH_SECONDS_GROUPER])
            self.logger.info("Desired target bytes legnth : as {} seconds".format(self.target_bytes_length_seconds))
            
            try:
                self.bytes_option = gp[K_BYTES_MODE_GROUPER]
                self.logger.debug("Bytes optioon selected = {}".format(BYTES_OPT[0]))
            except:
                self.logger.debug("Bytes mode option not found.")
                self.logger.debug("Default byte mode = {}".format(BYTES_OPT[1]))
                self.bytes_option = BYTES_OPT[1]
            
            self.opt_lookahead = int(grouper_data[K_PARAMETERS_GROUPER][K_OPTIMIZATION_LOOKAHEAD_GROUPER])
            self.logger.info("Lookahead is : {}".format(self.opt_lookahead)) 
        except:
            self.logger.error("Something went wrong in parsing the parameters")
            self.logger.exception("message")
            sys.exit(-1)


    def load_expected_keyframes(self):

        if not self.segments_keys_indexes or not self.segments_keys_timestamps:
            self.logger.debug("Keyframes not yet loaded --> run make groups before")
            sys.exit(-1)

    def make_groups(self):
        

        self.logger.info("Starting grouping routine. Method: bytes optimizer. Desired length-like bytes -> {}".format(self.target_bytes_length_seconds))
        

        if not K_OPTIMIZATION_FRAGMENTS_DIR_TEMPLATE_GROUPER in self.grouper_data[K_PARAMETERS_GROUPER].keys():
            self.logger.error("Fragments dir must be specified")
            sys.exit(-1)

        resolutions = self.video_data[K_RESOLUTIONS].split()
        template_res = resolutions[0]
        self.logger.debug("Handling template resolution {}".format(template_res))
        
        self.logger.info("Creating GOP rescaling method")
        method = self.create_gop_rescaling_method()
        self.logger.debug("GOP rescaling method --> {}".format(method))
        
        file_out = os.path.join(self.rescaled_dir_template.format(template_res), 'unfragmented.{}'.format(EXTENSION))
        self.logger.debug("Rescaled output  stored at {}".format(file_out))
        
        cache_file = self.get_cache_file(template_res)
        if cache_file:
            self.logger.debug("Cache file selected: {}".format(cache_file))

        self.logger.info("Starting rescaling of template resolution")
        video_template_resolution = self.video_obj.rescale_at_resolution(file_out, template_res, 'h264', self.bitrate_ladders_file,
                                                                        method, cache=self.cache, cache_file=cache_file)
         
        self.logger.info("Rescaling of template resolution computed succesfully")
        
        fragments_dir = self.grouper_data[K_PARAMETERS_GROUPER][K_OPTIMIZATION_FRAGMENTS_DIR_TEMPLATE_GROUPER].format(self.video_data[K_NAME_VIDEO], template_res)
        self.logger.debug("Fragments will be stored in {}".format(fragments_dir))
        
        cache_keys = None
        if self.cache:
            cache_keys = cache_file.replace('.{}'.format(EXTENSION), '.keys')
            self.logger.debug("Cache file for keys: {}".format(cache_keys))

        self.logger.debug("Loading rescaled video keyframes")
        keyframe_indexes, keyframe_timestamps = video_template_resolution.load_keyframes(cache=self.cache, cache_file=cache_keys)
        self.logger.debug("Keyframes indexes: {}".format(keyframe_indexes))
        self.logger.debug("Keyframes timestamps: {}".format(keyframe_timestamps))

        self.logger.debug("Computing target bytes length")
        video_bitrate = video_template_resolution.load_bitrate()
        self.logger.debug("Video bitrate is {} kbits".format(video_bitrate))
        target_bytes_per_segment = int(self.target_bytes_length_seconds * video_bitrate * M_IN_K / B_IN_BYTES)
        self.logger.info("Target bytes per segment is {}".format(target_bytes_per_segment))

        self.logger.debug("Creating a full video from video template")
        video_template_resolution = FullVideo(video_template_resolution)
        
        self.logger.info("Fragmenting template video")
        video_template_resolution.segment_h264(keyframe_indexes, keyframe_timestamps, fragments_dir)
        self.logger.info("Fragmentation computed correctly")
        
        if self.bytes_option == BYTES_OPT[0]:
            ffprobe_file_out = os.path.join(self.rescaled_dir_template.format(template_res), 'unfragmented.ffprobe')
            self.logger.debug("Storing FFprobe in {}".format(ffprobe_file_out))
                
            cache_file = self.get_cache_file(template_res)
            if cache_file:
                f1 = Path(cache_file)
                f2 = f1.with_suffix('')
                cache_file = f2.with_suffix('.ffprobe')
                self.logger.debug("Storing ffprobe cache file in {}".format(cache_file))
                
            video_template_resolution.load_ffprobe(ffprobe_file_out, cache=self.cache, cache_file=cache_file)
            self.logger.info("FFPROBE of resolution {} computed succesfully".format(res))
            video_template_resolution.assign_ffprobe_to_segments(os.path.join(fragments_dir, 'ffprobe'))
            self.logger.info("FFPROBE assigned correctly to segment for resolution {}".format(template_resolution))

       
        self.logger.debug("Creating fragments objects for optimization")
        factory = MultilevelVideoFactory(self.logger, OPT=self.bytes_option, enable_logging=self.verbose)
        fragments = factory.multilevel_video_from_full_videos( [ video_template_resolution] )
        self.logger.debug("Fragments objects created correctly")

        
        log_file_optimizer = os.path.join(self.logs_dir, 'bytes_optimizer.logs')
        self.logger.debug("Logging optimization output to {}".format(log_file_optimizer))
        
        
        self.logger.info("Creating bytes optimizer")
        grouper_bytes_optimizer = GrouperBytesOptimizer(  self.opt_lookahead, fragments, 'Grouper Bytes Optimizer', 
                                                        log_file_optimizer, target_bytes_per_segment, verbose=self.verbose)
        self.logger.info("Bytes optimizer object created succesfully")

        
        self.logger.info("Starting bytes optimization")
        grouper_bytes_optimizer.compute_suboptimal()
        self.logger.info("Bytes optimization computed succesfully")


        self.logger.debug("Retrieving keyframes boundaries and creating rescaling method")
        self.segments_keys_indexes, self.segments_keys_timestamps = grouper_bytes_optimizer.return_suboptimal()
        method = self.create_forced_keys_rescaling_method()
        self.logger.debug("Rescaling method for other resolutions created succesfully")

        for res in resolutions[1:]:
            self.logger.debug("Handling resolution {}".format(res))
            file_out = os.path.join(self.rescaled_dir_template.format(res), 'unfragmented.{}'.format(EXTENSION))
            self.logger.debug("File stored at {}".format(file_out))
            video_res = self.video_obj.rescale_at_resolution(   file_out, res, 'h264', self.bitrate_ladders_file,
                                                                method)
            
            self.logger.debug("Video at resolution {} re-encoded succesfully".format(res))
            file_keys_out = os.path.join(self.rescaled_dir_template.format(res), 'unfragmented.keys')
            self.logger.debug("Checking if all needed keyframes are presents")
            self.check(video_res, file_keys_out)
            self.logger.debug("Keyframes check completed succesfully")
             
        scene_df = self.format_dataframe_segments()
        return scene_df

