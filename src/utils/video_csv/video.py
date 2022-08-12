import math
import os, subprocess, json, glob
import sys
import numpy as np
import tempfile 
from shutil import copyfile
from src.consts.video_dataframe_preproc_consts import *
import pandas as pd
from src.utils.logging.logging_segue import create_logger
import logging
B_IN_BYTE = 8
M_IN_K = 1000

HACK_CTR = 0
import time

NANOSEC_IN_SEC = 1000000000.0

def pmkdir(kdir):
    if not os.path.exists(kdir):
        os.makedirs(kdir)


class Video:
    
    def __init__(self, video_path, logdir, verbose=False, concat_file=None):
#        global HACK_CTR
#        HACK_CTR += 1
#        if HACK_CTR == 1000:
#            print("1000 videos created, blockin")
#            while True:
#                time.sleep(1)

        self.logs_dir = logdir
        self.verbose = verbose
        pmkdir(logdir)
        video_id = video_path.replace('/', '-')
        log_file = os.path.join(logdir, 'videos.log'.format(video_id))
        self.logger = logging.getLogger("video")
        #create_logger('Video {}'.format(video_id), log_file, verbose=verbose)

        if not os.path.exists(video_path):
            self.logger.info("Video {} does not exist.".format(video_path))
            if concat_file:
                self.logger.info("Concatenation specified: creating video")
                #TODO: CONCAT different fqa files

                #concat_cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_file, '-c', 'copy', '-y', video_path]
                #concat_cmd_formatted = ' '.join(concat_cmd).strip()
                #self.logger.debug("Executing {}".format(concat_cmd_formatted))
                #proc = subprocess.Popen(concat_cmd_formatted, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                #outs, errs = proc.communicate()
                #assert os.path.exists(video_path)

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
        self._resolution_id = None
        self._bitrate = None
        self._keyframes_index_list = None
        self._keyframes_timestamp_list = None
    
    def video_path(self):
        return self._video_path

    
    def load_resolution(self):

        if self._resolution:
            self.logger.debug("Already computed resolution ID: {}".format(self._resolution))
            return self._resolution
        
        self._resolution = os.path.basename(os.path.dirname(self._video_path))
        return self._resolution


    def load_total_frames(self):
        
        if self._total_frames:
            self.logger.debug("Already computed total frames: {}".format(self._total_frames))
            return self._total_frames

        self.logger.debug("For frames count, loading the dataframe")
        with open(self._video_path, 'r') as fin:
            video_dataframe = pd.read_csv(fin, engine='python').sort_values(by=[FRAME_NUM], ignore_index=True)
        self._total_frames = video_dataframe.shape[0]
        self.logger.debug("Video {}: Computed a total of {} frames".format(self._video_path, self._total_frames))
        
        return self._total_frames

    
    def load_fps(self):
        
        if self._fps:
            self.logger.debug("Already computed FPS: {}".format(self._fps))
            return self._fps
        
        with open(self._video_path, 'r') as fin:
            video_dataframe = pd.read_csv(fin, engine='python').sort_values(by=[FRAME_NUM], ignore_index=True)
        frame_DURATION = video_dataframe[PTS][1]
        frame_duration_sec = frame_DURATION/NANOSEC_IN_SEC
        self._fps = 1.0/frame_duration_sec
        return self._fps

    
    def load_duration(self):
        if self._duration:
            self.logger.debug("Already computed duration: {}".format(self._duration))
            return self._duration
        
        with open(self._video_path, 'r') as fin:
            video_dataframe = pd.read_csv(fin, engine='python').sort_values(by=[FRAME_NUM], ignore_index=True)
        
        self._duration = sum(video_dataframe[FRAME_DUR])/NANOSEC_IN_SEC
        return self._duration

    
    def load_bytes(self):
        if self._bytes:
            self.logger.debug("Already computed bytes: {}".format(self._bytes))
            return self._bytes
    
        with open(self._video_path, 'r') as fin:
            video_dataframe = pd.read_csv(fin, engine='python').sort_values(by=[FRAME_NUM], ignore_index=True)
        self._bytes = sum(video_dataframe[FRAME_SIZE]) / 8.0
        return self._bytes

    
    def load_bitrate(self):
        if self._bitrate:
            self.logger.debug("Already computed bitrate: {}".format(self._bitrate))
            return self._bitrate
        
        self._bitrate = self.load_bytes()*B_IN_BYTE/self.load_duration()/M_IN_K
        return self._bitrate

    def get_video_stats(self):
        return self.load_duration(), self.load_bitrate(), self.load_bytes()
    
    
    def check_other_video(self, other_video_path, force):

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



    def rescale_h264_constant_quality(  self, 
                                        video_out_path, 
                                        crf, 
                                        gop, 
                                        forced_key_frames=None, 
                                        force=False):
        
        self.logger.info("Copying max res viedo into folder")
        copyfile(self._video_path, video_out_path)
        return Video(video_out_path, self.logs_dir)
    # Not all I-frames are keyframes. -skip_frame nokey will skip non-KF I-frames.
    # Care to filter by "pict type"


    def load_common_keyframe_indexes(self):
        path = os.path.dirname(os.path.dirname(self._video_path))
        bname = os.path.basename(self._video_path)
        available = os.listdir(path)
        
        this_keyframes = self.load_keyframes_indexes_single()

        for av in available:
            if 'asset' in av:
                vp = Video(os.path.join(path, av, bname), self.logs_dir)
                self.logger.info("Analysing {}".format(vp._video_path))
                vp_keys = vp.load_keyframes_indexes_single()
                this_keyframes = list(set(this_keyframes) & set(vp_keys))
                this_keyframes.sort()

        return this_keyframes

    def load_keyframes_indexes(self):
        return self.load_common_keyframe_indexes()
    
    def load_keyframes_timestamps(self):
        all_timestamps = self.load_keyframes_timestamps_single(all_frames=True)
        self.logger.info("Readed all timestamps")
        good_keyframes = self.load_common_keyframe_indexes()
        self.logger.info("Readed all common keyframes")
        return [ all_timestamps[y] for y in good_keyframes]

    def load_keyframes_timestamps_single(self, all_frames=False):
        
        with open(self._video_path, 'r') as fin:
            video_dataframe = pd.read_csv(fin, engine='python').sort_values(by=[FRAME_NUM], ignore_index=True)
        if all_frames:
            self.logger.debug("Retrieving timestamps of all frames")
            all_timestamps = [ x/NANOSEC_IN_SEC for x in list(video_dataframe[PTS]) ]
            return all_timestamps
        else:
            if self._keyframes_timestamp_list:
                self.logger.debug("Already computed keyframe timestamp: {}".format(self._keyframes_timestamp_list))
                return self._keyframes_timestamp_list

            PTSs = video_dataframe.loc[video_dataframe[TYPE] == 'I'][PTS]
            self._keyframes_timestamp_list = [ x/NANOSEC_IN_SEC for x in list(PTSs) ]
            return self._keyframes_timestamp_list




    def load_keyframes_indexes_single(self):
        

        if self._keyframes_index_list:
            self.logger.debug("Already computed keyframe indexes: {}".format(self._keyframes_index_list))
            return self._keyframes_index_list

        self.logger.debug("Retrieving the keyframes timestamps")

        keyframes_timestamps = self.load_keyframes_timestamps_single()
        all_frames_timestamps = self.load_keyframes_timestamps_single(all_frames=True)
        
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

        self._keyframes_index_list = self.load_keyframes_indexes()
        self._keyframes_timestamp_list = self.load_keyframes_timestamps()
        pmkdir(os.path.dirname(cache_file))
        self.logger.debug("Dumping into {}".format(cache_file))
        with open(cache_file, 'w') as fout:
            data = {}
            data['timestamps'] = self._keyframes_timestamp_list
            data['indexes'] = self._keyframes_index_list
            json.dump(data, fout)
    
    def read_key_cache(self, cache_file):
        with open(cache_file, 'r') as fin:
            data = json.load(fin)
            self._keyframes_timestamp_list = data['timestamps']
            self._keyframes_index_list = data['indexes']
            

    def load_keyframes(self, cache=False, cache_file=None):
        
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
        

        
        path = os.path.dirname(os.path.dirname(self._video_path))
        bname = os.path.basename(self._video_path)
        available = os.listdir(path)
        assert resolution in available
        dirin = os.path.join(path, resolution, bname)
        self.logger.info("Copying {} to {}".format(dirin, file_out))
        pmkdir(os.path.dirname(file_out))
        copyfile(os.path.join(path, resolution, bname), file_out)
        return Video(file_out, self.logs_dir) 


    def rescale_at_res_method_switching(self, ladder, fileout, method, codec): 
        
        self.logger("Illegal operation for video dataframe")
        pass 


    
    def rescale_h264_crf( self, crf, res, fileout, g=-1, forced_key_frames=None, force=False):
        
        self.logger("Illegal operation for video dataframe")
        pass 


 
    def rescale_h264_two_pass(  self, ladders, fileout, gop=-1,
                                forced_key_frames=None, 
                                force=False):
        
        ## This is usually called during augmentation
        IAB_PATH = 'videos/{}/IAB/*/chunk-0.fqa'
        video_name = self._video_path.split('/')[1]
        target_bitrate = ladders.target_br
        with open(self._video_path, 'r') as fin:
            video_dataframe = pd.read_csv(fin, engine='python').sort_values(by=[FRAME_NUM], ignore_index=True)
        
        temps_name = []
        closest = None
        closest_dist = float(math.inf)

        frame_start = list(video_dataframe[FRAME_NUM])[0]
        frame_end = list(video_dataframe[FRAME_NUM])[-1]

        from glob import glob
        for candidate in glob(IAB_PATH.format(video_name)):
            with open(candidate, 'r') as fin:
                video_candidate = pd.read_csv(fin, engine='python').sort_values(by=[FRAME_NUM], ignore_index=True)
            segment_candidate = video_candidate.loc[(video_candidate[FRAME_NUM] >= frame_start) & (video_candidate[FRAME_NUM] <= frame_end)]

            temp_name = next(tempfile._get_candidate_names())
            temps_name.append(temp_name)
            segment_candidate.to_csv(temp_name)
            segment_t = Video(temp_name, self.logs_dir)
            temp_dist = abs(segment_t.load_bitrate() - target_bitrate)
            if temp_dist < closest_dist:
                closest = temp_name
                closest_dist = temp_dist
        pmkdir(os.path.dirname(fileout))
        copyfile(closest, fileout)
        for t in temps_name:
            os.remove(t)
        return Video(fileout, self.logs_dir)
        

    
        self.logger("Illegal operation for video dataframe")
        pass 


