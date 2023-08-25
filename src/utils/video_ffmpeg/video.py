import os, subprocess, json, glob
import sys
import numpy as np
import tempfile 
from shutil import copyfile


from src.utils.logging.logging_segue import create_logger
from src.utils.read_ladders.ladders import Ladders
from src.consts.rescaling_method_consts import *
# ADD
from tempfile import TemporaryDirectory
import shutil
B_IN_BYTE = 8
M_IN_K = 1000

def pmkdir(kdir):
    if not os.path.exists(kdir):
        os.makedirs(kdir)


class Video:
    """
    A wrapper around ffmpeg to retrieve and manipulate video information.
    
    This class provides functionalities to:
    - Retrieve video details (like fps, duration, resolution etc.)
    - Rescale videos at different resolutions.
    - Segment videos based on keyframes.
    """

    ''' Attributes: fps, duration, total_frames, bytes, resolution, 
        bitrate, keyframes_index_list, keyframes_timestamp_list'''

    '''Utility function include: load_fps, load_duration, load_total_frames, load_bytes, 
                                 load_resolution, load_bitrate, load_keyframes_indexes, 
                                 load_keyframes_timestamps, load_keyframes, dump_key_cache, read_key_cache
                                 rescale_h264_constant_quality, rescale_at_resolution,
                                 check_other_video, video_path, get_video_stats,
                                 rescale_at_res_method_switching,  rescale_h264_two_pass, rescale_vp9_two_pass,
                                '''
    
    def __init__(self, video_path, logdir, verbose=False, concat_file=None):
        """
        Initializes the Video object.
        
        :param video_path: Path to the video file.
        :param logdir: Directory for storing logs.
        :param verbose: Flag indicating verbosity level.
        :param concat_file: File used for concatenating videos (if needed).
        """

        self.logs_dir = logdir
        self.verbose = verbose
        pmkdir(logdir)
        video_id = video_path.replace('/', '-')
        log_file = os.path.join(logdir, 'video_{}.log'.format(video_id))
        self.logger = create_logger('Video {}'.format(video_id), log_file, verbose=verbose)

        if not os.path.exists(video_path):
            self.logger.info("Video {} does not exist.".format(video_path))
            if concat_file:
                self.logger.info("Concatenation specified: creating video")
                concat_cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_file, '-c', 'copy', '-y', video_path]
                concat_cmd_formatted = ' '.join(concat_cmd).strip()
                self.logger.debug("Executing {}".format(concat_cmd_formatted))
                proc = subprocess.Popen(concat_cmd_formatted, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                outs, errs = proc.communicate()
                assert os.path.exists(video_path)

            else:
                self.logger.error("Video does not exist and concatenation not specified")
                sys.exit(-1)

        else:
            self.logger.debug("Video {} exists".format(video_path))
            self.logger.debug("Video object has been created correctly")
        
        self._video_path = video_path

        ## lazy: information are loaded only if the proper function is called

        ## general info
        self._fps = None
        self._duration = None
        self._total_frames = None
        self._bytes = None
        self._resolution = None
        self._bitrate = None
        self._keyframes_index_list = None
        self._keyframes_timestamp_list = None
    
    def video_path(self):
        """
        Returns the video path associated with the Video object.
        """
        return self._video_path

    def load_resolution(self):
        """
        Loads and returns the resolution of the video.
        """
        if self._resolution:
            self.logger.debug("Already computed resolution: {}".format(self._resolution))
            return self._resolution
        
        result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0",
                                 self._video_path],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
        
        self._resolution = result.stdout.decode("utf-8").rstrip()
        return self._resolution

    def load_total_frames(self):
        """
        Calculates and returns the total number of frames in the video.
        """
        if self._total_frames:
            self.logger.debug("Already computed total frames: {}".format(self._total_frames))
            return self._total_frames

        self.logger.debug("For frames count, fetching container")
        result = subprocess.run(["ffprobe",  "-v", "error",
                                "-select_streams", "v:0", "-show_entries", 
                                "stream=nb_frames", "-of", "default=nokey=1:noprint_wrappers=1", self._video_path],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        try:
            result = float(result.stdout)
        except:
            self.logger.debug("Fetching container failed. Computing invoking ffprobe")
            result = subprocess.run(["ffprobe",  "-v", "error",
                                    "-count_frames", "-select_streams", "v:0", "-show_entries", 
                                    "stream=nb_read_frames", "-of", "default=nokey=1:noprint_wrappers=1", self._video_path],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            result = float(result.stdout)
        
        self.logger.debug("Video {}: Computed a total of {} frames".format(self._video_path, result))
        
        self._total_frames = result
        return result

    
    def load_fps(self):
        """
        Loads and returns the frames-per-second (FPS) of the video.
        """
        
        if self._fps:
            self.logger.debug("Already computed FPS: {}".format(self._fps))
            return self._fps
        
        result = subprocess.run(["ffprobe",  "-v", "error",
                                "-select_streams", "v", "-of", 
                                "default=noprint_wrappers=1:nokey=1", 
                                "-show_entries", "stream=r_frame_rate", self._video_path],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        
        result = result.stdout.decode('utf-8')
        result = float(result.split('/')[0])/float(result.split('/')[1])
        result = "{:.2f}".format(result)
        self._fps = float(result)
        self.logger.debug("Video {} is {} fps".format(self._video_path, self._fps))
        return self._fps

    
    def load_duration(self):
        """
        Loads and returns the duration (in seconds) of the video.
        """
        if self._duration:
            self.logger.debug("Already computed duration: {}".format(self._duration))
            return self._duration
        
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                 "format=duration", "-of",
                                 "default=noprint_wrappers=1:nokey=1", self._video_path],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
        
        self._duration = float(result.stdout)
        return self._duration

    
    def load_bytes(self):
        """
        Loads and returns the size (in bytes) of the video.
        """
        if self._bytes:
            self.logger.debug("Already computed bytes: {}".format(self._bytes))
            return self._bytes
    
        self._bytes = os.path.getsize(self._video_path)
        return self._bytes

    
    def load_bitrate(self):
        """
        Calculates and returns the bitrate of the video.
        """
        if self._bitrate:
            self.logger.debug("Already computed bitrate: {}".format(self._bitrate))
            return self._bitrate
        
        self._bitrate = self.load_bytes()*B_IN_BYTE/self.load_duration()/M_IN_K
        return self._bitrate

    def get_video_stats(self):
        """
        Retrieves and returns a tuple of video stats: duration, bitrate, and size in bytes.
        """
        return self.load_duration(), self.load_bitrate(), self.load_bytes()
    
    
    def check_other_video(self, other_video_path, force):
        """
        Checks the existence and validity of another video. If force is True, overwrites the existing video.
        
        :param other_video_path: Path to the other video.
        :param force: Flag indicating if overwriting is allowed.
        """
        if os.path.exists(other_video_path) and not force:
            self.logger.debug("Video exists and force option deselected")
            other_video = Video(other_video_path, self.logs_dir, self.verbose)
            try:
                if (other_video.load_total_frames() != self.load_total_frames()):
                    self.logger.info("Video {} exists but corrupted. ".format(other_video_path))
                    self.logger.info("Total frames: {}, Expected {}. Recomputing...".format(    other_video.load_total_frames(),
                                                                                                self.load_total_frames()))
                    os.remove(other_video_path)
                    return None
            except:
                self.logger.info("Video is not well formed. Removing")    
                os.remove(other_video_path)
                return None

            else:
                self.logger.info("Video is well formed. Skipping computation")
                return other_video

        if force and os.path.exists(other_video_path):
            self.logger.debug("Video {} exists and force option selected. Removing video..".format(other_video_path))
            os.remove(other_video_path)
            return None
        
        return None

   

    # Not all I-frames are keyframes. -skip_frame nokey will skip non-KF I-frames.
    # Care to filter by "pict type"

    def load_keyframes_timestamps(self, all_frames=False):
        """
        Fetches timestamps of keyframes in the video. If all_frames is set, it fetches timestamps of all frames.

        :param all_frames: bool, optional (default is False)
            If set to True, fetches timestamps of all frames, else only keyframes.
        
        :return: list
            List of timestamps.
        """

        skip_no_key = "-skip_frame nokey" 
        if all_frames:
            self.logger.debug("Retrieving timestamps of all frames")
            skip_no_key = ""
        else:
            if self._keyframes_timestamp_list:
                self.logger.debug("Already computed keyframe timestamp: {}".format(self._keyframes_timestamp_list))
                return self._keyframes_timestamp_list

        cmd = "ffprobe -loglevel error -select_streams v:0 {} -show_frames -show_entries frame=pkt_pts_time -of csv {} | cut -d ',' -f 2".format(skip_no_key,self._video_path)
        
        ### VP9 doesn't work for just keyframes
        if not all_frames and 'webm' in os.path.basename(self._video_path).split('.')[1]:
            self.logger.debug("VP9 detected: overwriting cmd for just keyfames filtering")
            cmd = "ffprobe -loglevel error -select_streams v:0 -show_entries packet=pts_time,flags -of csv=print_section=0 " + self._video_path +" | awk -F',' '/K/ {print $1}'"
        

        self.logger.debug("Executing command: {}".format(cmd))
        
        proc = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outs, errs = proc.communicate()
        outs = outs.decode("utf-8").split()
        try:
            timestamps = [ float(t) for t in outs ]
        except:
            self.logger.error("Couldn't parse FPS list")
            sys.exit(-1)
        
        if not all_frames:
            self._keyframes_timestamp_list = timestamps
        return timestamps



    def load_keyframes_indexes(self):
        """
        Fetches and returns indexes of keyframes in the video.

        :return: list
            List of keyframe indexes.
        """

        if self._keyframes_index_list:
            self.logger.debug("Already computed keyframe indexes: {}".format(self._keyframes_index_list))
            return self._keyframes_index_list

        self.logger.debug("Retrieving the keyframes timestamps")

        keyframes_timestamps = self.load_keyframes_timestamps()
        all_frames_timestamps = self.load_keyframes_timestamps(all_frames=True)
        
        try:
            indexes = []
            for k in keyframes_timestamps:
                indexes.append(all_frames_timestamps.index(k))
        except Exception as e:
            self.logger.error("Something went wrong while computing the key frames indexes")
            self.logger.exception("message")
            sys.exit(-1)

        self.logger.debug("Keyframe indexes: {}".format(indexes))
        
        self._keyframes_index_list = [int(x) for x in indexes]
        return indexes
   

    def dump_key_cache(self, cache_file):
        """
        Saves keyframe data to a cache file for quicker access in the future.

        :param cache_file: str
            Path to the cache file where keyframe data will be saved.
        """
        self._keyframes_index_list = self.load_keyframes_indexes()
        self._keyframes_timestamp_list = self.load_keyframes_timestamps()
        self.logger.debug("Dumping into {}".format(cache_file))
        with open(cache_file, 'w') as fout:
            data = {}
            data['timestamps'] = self._keyframes_timestamp_list
            data['indexes'] = self._keyframes_index_list
            json.dump(data, fout)
    
    def read_key_cache(self, cache_file):
        """
        Reads keyframe data from a provided cache file.

        :param cache_file: str
            Path to the cache file from which keyframe data will be read.
        
        :return: list
            List of keyframe data.
        """
        with open(cache_file, 'r') as fin:
            data = json.load(fin)
            self._keyframes_timestamp_list = data['timestamps']
            self._keyframes_index_list = data['indexes']
            

    def load_keyframes(self, cache=False, cache_file=None):
        """
        Loads keyframes from the video. If cache is enabled, tries to read from cache first.

        :param cache: bool, optional (default is False)
            If set to True, reads keyframes from cache if available.
        :param cache_file: str, optional
            Path to the cache file. Required if cache is set to True.
        
        :return: list
            List of keyframes.
        """    
        if self._keyframes_index_list and self._keyframes_timestamp_list and not cache:
            self.logger.debug("Keyframes lists already computed")
            self.logger.debug("Keyframes indexes: {}".format(self._keyframes_index_list))
            self.logger.debug("Keyframes timestamps: {}".format(self._keyframes_timestamp_list))
            return self._keyframes_index_list, self._keyframes_timestamp_list

        if cache:
            self.logger.debug("Cache option selected")
            assert cache_file is not None
            if os.path.exists(cache_file):
                self.logger.debug("cache file {} exist. Reading data from it".format(cache_file))
                try:
                    self.read_key_cache(cache_file)
                except:
                    self.logger.debug("Couldn't read the cache file. Retrieving keyframes and dumping")
                    self.dump_key_cache(cache_file)
            else:
                self.logger.debug("Cache file {} does not exists".format(cache_file))
                self.dump_key_cache(cache_file)
            
            self.cache = cache_file
        else:
            self.logger.debug("Cache option deselected. Returning data")
            self._keyframes_index_list = self.load_keyframes_indexes()
            self._keyframes_timestamp_list = self.load_keyframes_timestamps()
        
        return self._keyframes_index_list, self._keyframes_timestamp_list


    def rescale_at_resolution(  self,
                                file_out,
                                resolution, 
                                codec,
                                ladders_df,
                                method,
                                cache=False,
                                cache_file=None):
        """
        Rescales the video to a given resolution using a specified codec and method.

        :param file_out: str
            Path where the rescaled video will be saved.
        :param resolution: tuple
            Desired resolution for the output video (width, height).
        :param codec: str
            Video codec to be used for encoding.
        :param ladders_df: DataFrame
            DataFrame containing bitrate ladders for different resolutions.
        :param method: str
            Rescaling method to be used.
        :param cache: bool, optional (default is False)
            If set to True, uses cache for keyframes.
        :param cache_file: str, optional
            Path to the cache file. Required if cache is set to True.
        """
        ...
        ## if cache is on:
            ## cache file exists: cache_file is copied to cache out
            ## cache file doesn't exist: file out is computed, then copied to cache
        ## if cache is off:
            ## if file out exists, skip
            ## if file out doesn't exist, compute
        
        if cache:
            self.logger.debug("Caches have been enabled")
            assert cache_file is not None, "Cache selected, cache file must be not None"
            if os.path.exists(cache_file):
                self.logger.debug("Cache file {} already exists".format(cache_file))
                if not os.path.exists(file_out):
                    self.logger.debug("File out {} doesn't exist. Copying {} -> {}".format(file_out, cache_file, file_out))
                    pmkdir(os.path.dirname(file_out))  
                    copyfile(cache_file, file_out)
                else:
                    self.logger.debug("File out {} already exist. Not overwriting it".format(file_out))
                return Video(file_out, self.logs_dir, self.verbose)
            else:
                self.logger.debug("Cache file doesn't exist")
                if os.path.exists(file_out):
                    self.logger.debug("Cache doesn't exist, but file out does. Copying it into caches")
                    copyfile(file_out, cache_file)
                    return Video(file_out, self.logs_dir, self.verbose)
        else:
            self.logger.debug("Cache deselected")
            if os.path.exists(file_out):
                self.logger.debug("File out {} already exists".format(file_out))
                return Video(file_out, self.logs_dir, self.verbose)
            else:
                self.logger.debug("File out {} does not yet exist. Computing".format(file_out))
        
        assert os.path.exists(ladders_df), "Bitrate ladder file doesn't exists"
        
        import pandas as pd
        ladders_df_csv = pd.read_csv(ladders_df)
        
        self.logger.info("Preparing to rescale video {} at resolution {}".format(self._video_path, resolution))
        self.logger.info("Bitrate ladders stored in {}".format(ladders_df))
        
        self.logger.debug("Creating ladder object")
        assert codec == 'h264' or codec == 'vp9', 'Unsupported codec'
        ladder = Ladders(ladders_df_csv, codec, resolution, self.load_fps(), self.logger)
        self.logger.debug("Ladder object created succesfully")

        if not os.path.exists(os.path.dirname(file_out)):
            self.logger.debug("Creating {}".format(os.path.dirname(file_out)))
            os.makedirs(os.path.dirname(file_out))
        
        print("Rescaling video from resolution {} to {}".format(self.load_resolution(), resolution))
        video = self.rescale_at_res_method_switching(ladder, file_out, method, codec)

        if cache:
            if not os.path.exists(os.path.dirname(cache_file)):
                self.logger.debug("Creating folder for cache")
                os.makedirs(os.path.dirname(cache_file))
            self.logger.debug("Copying file to cache")
            copyfile(file_out, cache_file)

        return video


    def rescale_at_res_method_switching(self, ladder, fileout, method, codec): 
        ''' Mthod_ID is the key of the method in the json file and defined in src/consts/rescaling_method_consts.py'''
        """
        Selects the appropriate rescaling method based on the provided method string.

        :param ladder: dict
            Dictionary containing the resolution and bitrate information.
        :param fileout: str
            Path where the rescaled video will be saved.
        :param method: str
            Rescaling method to be used.
        :param codec: str
            Video codec to be used for encoding.
        """
        method_id = method[K_RESCALING_METHOD_KEYFRAMES_APPROACH]
        self.logger.debug("selected rescaling method is {}".format(method))

        if method_id == K_RESCALING_METHOD_KEYFRAMES_GOP:
            assert K_RESCALING_METHOD_GOP_SECONDS  in method.keys()
            gop_seconds = int(method[K_RESCALING_METHOD_GOP_SECONDS])
            gop = int(self.load_fps()*gop_seconds)
            self.logger.debug("Gop method selected with gop time of {}. Rescaling with a gop of {}".format(gop_seconds, gop))
            
            if codec == 'h264':
                self.logger.debug("Codec is h264")
                video = self.rescale_h264_two_pass( ladder, 
                                                    fileout,
                                                    gop=gop)
            elif codec == 'vp9':
                self.logger.debug("Codec is vp9")
                video = self.rescale_vp9_two_pass(  ladder, 
                                                    fileout,
                                                    gop=gop)
            else:
                self.logger.error("Codec {} unknown.".format(codec))
                sys.exit(-1)
 

        elif method_id == K_RESCALING_METHOD_KEYFRAMES_CONSTANT:
            assert K_RESCALING_METHOD_SEGMENT_SECONDS in method.keys()

            segment_seconds = float(method[K_RESCALING_METHOD_SEGMENT_SECONDS])
            constant_keys_interval = int(segment_seconds*self.load_fps())
            self.logger.debug("Constant segment length is {}. Constant frame interval of {}".format(segment_seconds, constant_keys_interval))
            
            if codec == "h264":
                self.logger.debug("Codec is h264")
                
                forced_key_frames_indexes = []
                forced_key_frames_timestamps = []

                forced_key = 0
                time_iterator = 0

                while time_iterator < self.load_duration():
                    forced_key = int(max(0, time_iterator * self.load_fps()))
                    forced_key_frames_indexes.append(forced_key)
                    forced_key_frames_timestamps.append(time_iterator)
                    time_iterator += segment_seconds

                self.logger.debug("Forcing key_frames: {}".format(forced_key_frames_indexes))
                
                video = self.rescale_h264_two_pass( ladder, 
                                                    fileout,
                                                    forced_key_frames=forced_key_frames_indexes)
            elif codec=="vp9":
                self.logger.debug("Codec is vp9")
                video = self.rescale_vp9_two_pass(  ladder, 
                                                    fileout,
                                                    constant_keys_interval=constant_keys_interval)
            else:
                self.logger.error("Codec {} unknown.".format(codec))
                sys.exit(-1)
                
        elif method_id == K_RESCALING_METHOD_KEYFRAMES_FORCE_KEYS:
            assert K_RESCALING_METHOD_FORCED_INDEXES_LIST in method.keys()
            assert codec == 'h264', "Only h264 allowed with forced keys method"

            key_frames_list = method[K_RESCALING_METHOD_FORCED_INDEXES_LIST]

            self.logger.debug("Forced keys methodology selected")
            self.logger.debug("Forcing key_frames: {}".format(key_frames_list))
            
            video = self.rescale_h264_two_pass( ladder, 
                                                fileout,
                                                forced_key_frames=key_frames_list)

        else:
            self.logger.error("Method {} unknown. Accepted: GOP-CONSTANT-FORCE_KEYS".format(method_id))
            sys.exit(-1)
        return video


    def rescale_vp9_two_pass(self, ladders, fileout, gop=-1,  constant_keys_interval=-1, force=False): 
        """
        Rescales the video using the VP9 codec with two-pass encoding.

        :param ladders: list
            List of dictionaries containing resolution and bitrate information for different levels.
        :param fileout: str
            Path where the rescaled video will be saved.
        :param gop: int, optional (default is -1)
            Group of Pictures size.
        :param constant_keys_interval: int, optional (default is -1)
            Interval for forced keyframes.
        :param force: bool, optional (default is False)
            If set to True, will forcibly overwrite the output video if it already exists.
        """
        video = self.check_other_video(fileout, force)
        if video is not None:
            return video

        if gop > 0:
            assert constant_keys_interval == -1, "If gop is selected, constant keys must be deselected"
            keyframes_specs = "-g {}".format(gop)
        elif constant_keys_interval > 0:
            assert gop == -1, "If constant keys interval is selected, gop must be deselected"
            keyframes_specs = "-keyint_min {} -g {}".format(gop, gop)
        else:
            self.logger.error("No key specification. Aborting")
            sys.exit(-1)

        temp_name = next(tempfile._get_candidate_names())
        
        first_pass, second_pass = ladders.format_cmd_vp9_two_pass(self.logger)
        first_pass = first_pass.format(self._video_path, keyframes_specs, temp_name, fileout)
        second_pass = second_pass.format(self._video_path, keyframes_specs, temp_name, fileout)
        two_pass = first_pass + ' && ' + second_pass 
        
        self.logger.debug("Executing {}".format(two_pass))
        proc = subprocess.Popen(two_pass, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outs, errs = proc.communicate()
        
        if os.path.exists(temp_name+ '-0.log'):
            os.remove(temp_name+ '-0.log')
        
        video = Video(fileout, self.logs_dir, self.verbose)
        if (video.load_total_frames() != self.load_total_frames()):
            self.logger.error("Video {} exists but wasn't encoded correctly. ".format(fileout))
            self.logger.error("Total frames: {}, Expected {}. Removing and terminating".format( video.load_total_frames(),
                                                                                                self.load_total_frames()))
            os.remove(fileout)
            sys.exit(-1)
        else:
            return video
            

 
    def rescale_h264_two_pass(  self, ladders, fileout, gop=-1,
                                forced_key_frames=None, 
                                force=False):
        """
        Rescales the video using the h264 codec with two-pass encoding.

        :param ladders: list
            List of dictionaries containing resolution and bitrate information for different levels.
        :param fileout: str
            Path where the rescaled video will be saved.
        :param gop: int, optional (default is -1)
            Group of Pictures size.
        :param forced_key_frames: list, optional
            List of frames to be forced as keyframes.
        :param force: bool, optional (default is False)
            If set to True, will forcibly overwrite the output video if it already exists.
        """
        video = self.check_other_video(fileout, force)
        if video is not None:
            return video

        if gop > 0:
            assert forced_key_frames == None, "If gop is selected, forced keys must be deselected"
            keyframes_specs = "-g {}".format(gop)
        elif forced_key_frames is not None:
            assert gop == -1, "If forced key frames is selected, gop must be deselected"
            key_string = ['eq(n,{})'.format(k) for k in forced_key_frames]
            key_string = '+'.join(key_string).strip()
            keyframes_specs =  '-force_key_frames "expr:{}"'.format(key_string)
        else:
            keyframes_specs = ''

        temp_name = next(tempfile._get_candidate_names())
        

        first_pass, second_pass = ladders.format_cmd_h264_two_pass(self.logger, self.load_duration())
       
        first_pass = first_pass.format(self._video_path, keyframes_specs, temp_name)
        second_pass = second_pass.format(self._video_path, keyframes_specs, temp_name, fileout)
        
        pmkdir(os.path.dirname(fileout))

        two_pass = first_pass + ' && ' + second_pass
        self.logger.debug("Executing {}".format(two_pass))
        proc = subprocess.Popen(two_pass, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outs, errs = proc.communicate()
        
        if os.path.exists(temp_name+ '-0.log'):
            os.remove(temp_name+ '-0.log')
        if os.path.exists(temp_name+ '-0.log.mbtree'):
            os.remove(temp_name+ '-0.log.mbtree')

        video = Video(fileout, self.logs_dir, self.verbose)
        if (video.load_total_frames() != self.load_total_frames()):
            self.logger.error("Video {} exists but wasn't encoded correctly. ".format(fileout))
            self.logger.error("Total frames: {}, Expected {}. Removing and terminating".format( video.load_total_frames(), self.load_total_frames()))
            os.remove(fileout)
            sys.exit(-1)
        else:
            forced_key_frames = None
            return video
            

    def rescale_h264_constant_quality(  self, 
                                        video_out_path, 
                                        crf,
                                        gop, 
                                        forced_key_frames=None, 
                                        force=False):
        """
        Rescales the video using h264 codec with constant quality.
        
        :param video_out_path: Output path for the rescaled video.
        :param crf: Constant Rate Factor for the video encoding.
        :param gop: Group of pictures size.
        :param forced_key_frames: List of frames to be forced as keyframes.
        :param force: Flag to force the re-encoding even if output exists.
        """
        '''Rescale a video at a given resolution, using ffmpeg and h264 codec'''
        '''If force_key_frames is not None, the video is rescaled using the keyframes 
        specified which will serve as boundaries for the segments'''


        self.logger.debug("Selected rescale method h264 in constant quality")
        
        video = self.check_other_video(video_out_path, force)
        if video is not None:
            return video

        gop_string = ""
        if gop > 0:
            self.logger.debug("Rescaling with a gop of {}".format(gop))
            gop_string = "-g {}".format(gop)
        
        forced_key_frames_string = ""

        if forced_key_frames is not None:
            if isinstance(forced_key_frames, list):
                self.logger.debug("List of keyframes specified")
                k_string = ['eq(n,{})'.format(k) for k in forced_key_frames]
                k_string = '+'.join(k_string).strip()
                forced_key_frames_string = '-force_key_frames "expr:{}"'.format(k_string)

        cmd = "ffmpeg -i {} -c:v libx264 -crf {} {} {} -y {}".format(   self._video_path, 
                                                                        crf, 
                                                                        forced_key_frames_string,
                                                                        gop_string, 
                                                                        video_out_path)

        self.logger.info("Executing {}".format(cmd))
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outs, errs = proc.communicate()
        assert os.path.exists(video_out_path), "Video {} does not exist".format(video_out_path)
        self.logger.info("Rescaling from {} to {} completed succesfully!".format(self._video_path, video_out_path))
        video = Video(video_out_path, self.logs_dir, self.verbose)
        
        if (video.load_total_frames() != self.load_total_frames()):
            self.logger.error("Video {} exists but wasn't encoded correctly. ".format(video_out_path))
            self.logger.error("Total frames: {}, Expected {}. Removing and terminating".format( video.load_total_frames(),
                                                                                                self.load_total_frames()))
            os.remove(video_out_path)
            sys.exit(-1)
        else:
            return video
    def rescale_h264_constant_quality_list(self,
                                    video_out_path,
                                    crf_values,
                                    gop,
                                    forced_key_frames=None,
                                    force=False):
        """
        Rescales the video using h264 codec with constant quality CRF list to encode each segment.
        
        :param video_out_path: Output path for the rescaled video.
        :param crf: Constant Rate Factor for the video encoding.
        :param gop: Group of pictures size.
        :param forced_key_frames: List of frames to be forced as keyframes.
        :param force: Flag to force the re-encoding even if output exists.
        """

        self.logger.debug("Selected rescale method h264 in constant quality")

        video = self.check_other_video(video_out_path, force)
        if video is not None:
            return video

        gop_string = ""
        if gop > 0:
            self.logger.debug("Rescaling with a gop of {}".format(gop))
            gop_string = "-g {}".format(gop)

        # Create a temporary directory to store each segment
        with TemporaryDirectory() as temp_dir:
            last_keyframe = 0
            segments = []
            for i, keyframe in enumerate(forced_key_frames[1:-1]): # Exclude first and last keyframe
                segment_path = f"{temp_dir}/segment_{i}.mp4"
                segments.append(segment_path)
                crf = crf_values[i]
                cmd = "ffmpeg -i {} -ss {} -to {} -c:v libx264 -crf {} {} -y {}".format(
                    self._video_path,   
                    last_keyframe,
                    keyframe,
                    crf,
                    gop_string,
                    segment_path)
                print("Executing {}".format(cmd))
                self.logger.info("Executing {}".format(cmd))
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                outs, errs = proc.communicate()
                assert os.path.exists(segment_path), f"Segment {segment_path} does not exist"

                last_keyframe = keyframe

            # Concatenate all segments
            concat_file = f"{temp_dir}/concat_list.txt"
            with open(concat_file, "w") as f:
                for segment in segments:
                    f.write(f"file '{segment}'\n")

            concat_cmd = "ffmpeg -f concat -safe 0 -i {} -c copy -y {}".format(concat_file, video_out_path)
            proc = subprocess.Popen(concat_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            outs, errs = proc.communicate()

        assert os.path.exists(video_out_path)
        self.logger.info("Rescaling from {} to {} completed successfully!".format(self._video_path, video_out_path))
        video = Video(video_out_path, self.logs_dir, self.verbose)

        if video.load_total_frames() != self.load_total_frames():
            self.logger.error("Video {} exists but wasn't encoded correctly. ".format(video_out_path))
            self.logger.error("Total frames: {}, Expected {}. Removing and terminating".format(
                video.load_total_frames(),
                self.load_total_frames()))
            os.remove(video_out_path)
            sys.exit(-1)
        else:
            return video

    def rescale_h264_crf( self, crf, res, fileout, g=-1, forced_key_frames=None, force=False):
        """
        Rescales the video using the h264 codec with Constant Rate Factor (CRF).

        :param crf: int
            Constant Rate Factor value for quality control.
        :param res: tuple
            Desired resolution for the output video (width, height).
        :param fileout: str
            Path where the rescaled video will be saved.
        :param g: int, optional (default is -1)
            Group of Pictures size.
        :param forced_key_frames: list, optional
            List of frames to be forced as keyframes.
        :param force: bool, optional (default is False)
            If set to True, will forcibly overwrite the output video if it already exists.
        """      
        video = self.check_other_video(fileout, force)
        
        if video is not None:
            return video
        

        if g > 0:
            assert forced_key_frames == None, "If gop is selected, forced keys must be deselected"
            keyframes_specs = "-g {}".format(g)
        elif forced_key_frames is not None:
            assert g == -1, "If forced key frames is selected, gop must be deselected"
            key_string = ['eq(n,{})'.format(k) for k in forced_key_frames]
            key_string = '+'.join(key_string).strip()
            keyframes_specs =  '-force_key_frames "expr:{}"'.format(key_string)
        else:
            self.logger.error("No key specification. Aborting")
            sys.exit(-1)

        
        crf_command = "ffmpeg -i {} -vf scale={} -crf {} {} {}".format( self._video_path,
                                                                        res, crf, keyframes_specs, 
                                                                        fileout)
        
        self.logger.info("Executing {}".format(crf_command))
        proc = subprocess.Popen(crf_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outs, errs = proc.communicate()
        
        video = Video(fileout, self.logs_dir, self.verbose)
        if (video.load_total_frames() != self.load_total_frames()):
            self.logger.error("Video {} exists but wasn't encoded correctly. ".format(fileout))
            self.logger.error("Total frames: {}, Expected {}. Removing and terminating".format( video.load_total_frames(), self.load_total_frames()))
            os.remove(fileout)
            sys.exit(-1)
        else:
            forced_key_frames = None
            return video
        