import pandas as pd
import os, shutil, sys
import os, subprocess, json, glob
from src.utils.video_csv.video import Video
from src.utils.video_csv.segment import Segment
from src.consts.vmaf_consts import *
from shutil import copyfile
from src.consts.video_dataframe_preproc_consts import *
import logging
NANOSEC_IN_SEC = 1000000000.0


def empty(folder, logger):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.error('Failed to delete %s. Reason: %s' % (file_path, e))


def pmkdir(kdir):
    if not os.path.exists(kdir):
        os.makedirs(kdir)

 

class FullVideo:
    
    def __init__(self, video):
        
            self._video = video
            self.logger = video.logger
            self._segments_list = []

            self._segments_dir = None
            self._segments_keys_boundaries = None
            self._segments_keys_timestamps = None
            
            self._vmaf_data = None
            self._psnr = None
            self._ffprobe_data = None

            self.logger.debug("Full video created succesfully")
        
    def video(self):
        return self._video

    def read_ffprobe_file(self, file_in):
        with open(file_in, 'r') as fin:
            file_in = pd.read_csv(file_in, engine='python').sort_values(by=[FRAME_NUM], ignore_index=True)
        self._ffprobe_data = []
        all_sizes = [ x/8.0 for x in list(file_in[FRAME_SIZE]) ]
        pts = list(file_in[PTS])
        all_durations_minus_last = [ (y - x)/NANOSEC_IN_SEC for x,y in zip(pts, pts[1:])]
        last = pts[1]/NANOSEC_IN_SEC
        all_durations = all_durations_minus_last + [last]
        
        assert len(all_durations) == len(all_sizes)
        self._ffprobe_data = [(x, int(y)) for x,y in zip(all_durations, all_sizes)]
        
        return True



    def load_ffprobe(   self, 
                        store_file, 
                        cache=False,
                        cache_file=None):
        
 
        
        done = self.read_ffprobe_file(self._video._video_path)
        assert len(self._ffprobe_data) == self._video.load_total_frames()
        return self._ffprobe_data

    def keyframe_split( self, 
                        assembled_chunks_dir, 
                        template, 
                        key_frame_indexes=None, 
                        force=False):


        if os.path.exists(assembled_chunks_dir):
            chunks_no = len(os.listdir(assembled_chunks_dir))
            if key_frame_indexes:
                chunks_no_target = len(key_frame_indexes) + 1
            else:
                keyframe_list = self._video.get_keyframes_indexes()[1:] # exclude first
                chunks_no_target = len(keyframe_list)

            if chunks_no == chunks_no_target and force == False:
                self.logger.debug("Force option deselected, correct number of chunks")
                return
            else:
                self.logger.debug("Force is {}".format(force))
                self.logger.debug("Chunks no is {}, expected is {}".format(chunks_no, chunks_no_target))
                self.logger.debug("Emptying the folder {}".format(assembled_chunks_dir))
                empty(assembled_chunks_dir, self.logger)
        
        chunks_no_target = -1

        if key_frame_indexes == None:
            
            keyframe_list = self._video.get_keyframes_indexes()[1:] # exclude first
            chunks_no_target = len(keyframe_list)
            keyframe_list  = [int(x) for x in keyframe_list]
        else:
            key_frame_indexes  = [int(x) for x in key_frame_indexes]
            chunks_no_target = len(key_frame_indexes) + 1
        
        with open(self._video._video_path, 'r') as vp:
            video_dataframe = pd.read_csv(vp, engine='python').sort_values(by=[FRAME_NUM], ignore_index=True)

        start = 0
        for i, keyf in enumerate(key_frame_indexes):
            df = video_dataframe.iloc[start:keyf, ]
            df.to_csv(os.path.join(assembled_chunks_dir, template.format(i)))
            start = keyf

        df = video_dataframe.iloc[keyf:, ]
        df.to_csv(os.path.join(assembled_chunks_dir, template.format(i+1)))
        chunks_no = len(os.listdir(assembled_chunks_dir))
        assert chunks_no == chunks_no_target, "Expected: {}, current {}".format(chunks_no_target, chunks_no) 
        key_frame_indexes = None
    
    def load_segments(self):
        if self._segments_list:
            self.logger.debug("Returning already computed list of segments")
            return self._segments_list
        else:
            self.logger.error("ERROR: segments list has not already been computed")
            return None

    def segment_h264(   self,
                        forced_keyframes_indexes, 
                        forced_keyframes_timestamps,
                        assembled_chunks_dir,
                        force=False): ## ZERO INCLUDED
        
        if self._segments_list and not force:
            self.logger.error("Already performed segmentation. To load segments, execute \"load_segments\" method")
            return

        assert len(forced_keyframes_indexes) == len(forced_keyframes_timestamps)
        assert forced_keyframes_indexes[0] == 0
        assert forced_keyframes_timestamps[0] == 0.0


        forced_keyframes_indexes = [int(x) for x in forced_keyframes_indexes]

        self.logger.info("Segmenting video {}".format(self._video.video_path()))    
        self.logger.debug("Final video chunks will be stored in {}".format(assembled_chunks_dir))
        self.logger.debug("Forced key frames indexes accounted are {}".format(forced_keyframes_indexes))
        self.logger.debug("Forced key frames timestamps accounted are {}".format(forced_keyframes_timestamps))
        
        pmkdir(assembled_chunks_dir)
        self.keyframe_split( assembled_chunks_dir,
                            '{}.fqa', 
                            key_frame_indexes=forced_keyframes_indexes[1:], force=force)
        

        start_frame = 0
        start_time = 0.0

        end_frames_all = self._video.load_total_frames()
        end_time_all = self._video.load_duration()

        tuples = list(zip(forced_keyframes_indexes[1:] + [end_frames_all] , forced_keyframes_timestamps[1:] + [end_time_all]))
        total_frames = 0

        for i, (end_frame, end_time) in enumerate(tuples):
            segment_path = os.path.join(assembled_chunks_dir, "{}.fqa".format(i))
            video_segment = Video(segment_path, self._video.logs_dir, self._video.verbose)
            segment_frames = video_segment.load_total_frames()
            
            total_frames += segment_frames
            if (segment_frames != end_frame - start_frame):
                self.logger.error("Inconsistent number of frames: actual {} != expected {}".format(segment_frames, end_frame - start_frame))
                self.logger.error("Emptying segments folder")
                empty(assembled_chunks_dir, self.logger)
                sys.exit(-1)

            segment = Segment(video_segment, i, start_frame, end_frame, start_time, end_time)
            self._segments_list.append(segment)
            start_frame = end_frame
            start_time = end_time
        
        self._segments_dir = assembled_chunks_dir
        self._segments_keys_boundaries = forced_keyframes_indexes
        self._segments_keys_timestamps = forced_keyframes_timestamps
        return total_frames

    
    def vmaf(self):
        if self._vmaf_data:
            return self._vmaf_data
        else:
            logger.error("Vmaf data not yet computed")
            sys.exit(-1)
    
    def read_vmaf_file(self, file_in, model):
        with open(file_in, 'r') as fin:
            file_in = pd.read_csv(fin, engine='python').sort_values(by=[FRAME_NUM], ignore_index=True)
        assert model == VMAF or model == VMAF2
        self._vmaf_data = list(file_in[model])
        assert len(self._vmaf_data) == self._video.load_total_frames()
        return True

    
    def read_psnr(self, file_in):
        with open(file_in) as fin:
            file_in = pd.read_csv(fin, engine='python').sort_values(by=[FRAME_NUM], ignore_index=True)
        self._psnr = list(file_in[PSNR])
        return True
    
    def load_psnr(self,
            reference_video,
            store_file,
            cache=False,
            cache_file=None):
        

        done = self.read_psnr(self._video._video_path)
        assert len(self._psnr) == self._video.load_total_frames()
        return self._psnr

    

    def load_vmaf( self, 
                   reference_video, 
                   store_file, 
                   vmaf_model_name,
                   cache=False,
                   cache_file=None):
        
        done = self.read_vmaf_file(self._video._video_path, vmaf_model_name)
        assert len(self._vmaf_data) == self._video.load_total_frames()
        return self._vmaf_data

       

    def assign_vmaf_to_segments(self, vmaf_store_dir):

        if not self._segments_list:
           self.logger.error("Cannot assign VMAF to segments: not segmented yet")
           sys.exit(-1)
        elif not self._vmaf_data:
            self.logger.error("Cannot assign VMAF to segments: VMAF not yet computet")
            sys.exit(-1)
        
        pmkdir(vmaf_store_dir)

        for s in self._segments_list:
            self.logger.debug("Handling segment {}".format(s.seqno()))
            fout = os.path.join(vmaf_store_dir, "{}.vpf".format(s.seqno()))
            assigned = False
            if os.path.exists(fout):
                try:
                    with open(fout, 'r') as fin:
                        data = json.load(fin)
                        vmaf_list = data['vmaf_per_frame']
                    s.assign_vmaf(vmaf_list)
                    assigned = True
                except:
                    self.logger.debug("Failed to parse vpf file. Recomputing")
                    os.remove(fout)
            if not assigned:
                frame_start, frame_end = s.frame_range()
                self.logger.debug("Slicing VMAF data: start {} ==> end {}".format(frame_start, frame_end))
                vmaf_list  = self._vmaf_data[frame_start:frame_end]
                s.assign_vmaf(vmaf_list)
                with open(fout, 'w') as ffout:
                    data = {}
                    data['vmaf_per_frame'] = vmaf_list
                    json.dump(data, ffout)
     
    def assign_ffprobe_to_segments(self, ffprobe_store_dir):

        if not self._segments_list:
           self.logger.error("Cannot assign FFPROBE to segments: not segmented yet")
           sys.exit(-1)
        elif not self._ffprobe_data:
            self.logger.error("Cannot assign FFPROBE to segments: FFPROBE not yet computet")
            sys.exit(-1)
        
        pmkdir(ffprobe_store_dir)

        for s in self._segments_list:
            self.logger.debug("Handling segment {}".format(s.seqno()))
            fout = os.path.join(ffprobe_store_dir, "{}.ffprobe".format(s.seqno()))
            assigned = False
            if os.path.exists(fout):
                try:
                    with open(fout, 'r') as fin:
                        data = json.load(fin)
                        ffprobe_list = data['ffprobe_dur_size']
                    s.assign_ffprobe(ffprobe_list)
                    assigned = True
                except:
                    self.logger.debug("Failed to parse ffprobe file. Recomputing")
                    os.remove(fout)
            if not assigned:
                frame_start, frame_end = s.frame_range()
                self.logger.debug("Slicing FFPROBE data: start {} ==> end {}".format(frame_start, frame_end))
                ffprobe_list  = self._ffprobe_data[frame_start:frame_end]
                s.assign_ffprobe(ffprobe_list)
                with open(fout, 'w') as ffout:
                    data = {}
                    data['ffprobe_dur_size'] = ffprobe_list
                    json.dump(data, ffout)
    
