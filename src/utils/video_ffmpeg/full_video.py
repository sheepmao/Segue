import os, shutil, sys
import os, subprocess, json, glob
from src.utils.video_ffmpeg.video import Video
from src.utils.video_ffmpeg.segment import Segment
from src.consts.vmaf_consts import *
from shutil import copyfile


FFPROBE_CONST = [ 'ffprobe', '-v', 'quiet', '-show_packets', '-select_streams', 'v', '-print_format', 'json=c=1']

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
        if os.path.exists(file_in):
            try:
                with open(file_in, 'r') as fin:
                    data = json.load(fin)

                self._ffprobe_data = [(float(vv["duration_time"]), int(vv["size"])) for vv in data['packets']]
                
                if len(self._ffprobe_data) != self._video.load_total_frames():
                    self.logger.debug("Local cache ffprobe number of frames mismatched. Recomputing")
                    os.remove(file_in)
                    return False
                
                else:
                   return True

            except:
                self.logger.info("Malformed VMAF FFprobe file. Recomputing")
                os.remove(file_in)
                return False
        return False



    def load_ffprobe(   self, 
                        store_file, 
                        cache=False,
                        cache_file=None):
        
        if cache:
            self.logger.debug("Caches have been enabled")
            assert cache_file is not None, "Cache selected, cache file must be not None"
            done = self.read_ffprobe_file(cache_file)
            if done:
                if os.path.exists(store_file):
                    self.logger.debug("File out {} exist. Removing it".format(store_file))
                    os.remove(store_file)
                self.logger.debug("Copying cache {} to {}".format(cache_file, store_file))
                pmkdir(os.path.dirname(store_file))  
                copyfile(cache_file, store_file)
                return self._ffprobe_data
                
            else:
                done = self.read_ffprobe_file(store_file)
                if done:
                    self.logger.debug("File out {} exists. Copying it into cache".format(store_file))
                    pmkdir(os.path.dirname(cache_file))  
                    copyfile(store_file, cache_file)
                    return self._ffprobe_data
 
        if self._ffprobe_data:
            if len(self._ffprobe_data) == self._video.load_total_frames():
                self.logger.debug("FFprobe data already loaded. Frames count coincide")
                return self._ffprobe_data
            else:
                self.logger.debug("FFprobe data already loaded, but frame counts corrupted. Re-loading")
        
        done = self.read_ffprobe_file(store_file)
        if done:
            self.logger.debug("FFprobe data not yet loaded but already computed. Returning it")
            if cache:
                pmkdir(os.path.dirname(cache_file))  
                copyfile(store_file, cache_file)    
            return self._ffprobe_data
        
        ffprobe_cmd = FFPROBE_CONST + [ self._video.video_path() ] 
        self.logger.debug('Executing FFPROBE with cmd {}'.format(' '.join(ffprobe_cmd)))
        result = subprocess.run(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        result = json.loads(result.stdout.decode('utf-8'))
        
        with open(store_file, 'w') as fout:
            json.dump(result, fout)

        done = self.read_ffprobe_file(store_file)
        
        if not done:
            self.logger.error("FFprobe file couldn't compute correctly. Exiting")
            sys.exit(-1)
        
        if cache:
            pmkdir(os.path.dirname(cache_file))  
            copyfile(store_file, cache_file)    
        
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

            keyframe_list  = [str(x) for x in keyframe_list]
            keyframe_list = ','.join(keyframe_list)
        else:
            key_frame_indexes  = [str(x) for x in key_frame_indexes]
            chunks_no_target = len(key_frame_indexes) + 1
            
            keyframe_list = ','.join(key_frame_indexes)
            key_frame_indexes = None
            key_frame_split_cmd = 'ffmpeg -i {} -acodec copy -f segment  -segment_frames "{}" -vcodec copy -reset_timestamps 1 -map 0 -y {}/{}'.format( self._video.video_path(), 
                                                                                                                                                keyframe_list, 
                                                                                                                                                assembled_chunks_dir, 
                                                                                                                                                template)
        self.logger.debug("Executing {}".format(key_frame_split_cmd))
        proc = subprocess.Popen(key_frame_split_cmd,shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outs, errs = proc.communicate()
        chunks_no = len(os.listdir(assembled_chunks_dir))
        assert chunks_no == chunks_no_target, "Expected: {}, current {}".format(chunks_no_target, chunks_no) 

    
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
                            '%d.mp4', 
                            key_frame_indexes=forced_keyframes_indexes[1:], force=force)
        

        start_frame = 0
        start_time = 0.0

        end_frames_all = self._video.load_total_frames()
        end_time_all = self._video.load_duration()

        tuples = list(zip(forced_keyframes_indexes[1:] + [end_frames_all] , forced_keyframes_timestamps[1:] + [end_time_all]))
        total_frames = 0

        for i, (end_frame, end_time) in enumerate(tuples):
            segment_path = os.path.join(assembled_chunks_dir, "{}.mp4".format(i))
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
    
    def read_vmaf_file(self, file_in):
        if os.path.exists(file_in):
            try:
                with open(file_in, 'r') as fin:
                    data = json.load(fin)

                self._vmaf_data = [float(vv['metrics']['vmaf']) for vv in data['frames']]
                
                if len(self._vmaf_data) != self._video.load_total_frames():
                    self.logger.debug("Local cache vmaf number of frames mismatched. Recomputing")
                    os.remove(file_in)
                    return False
                
                else:
                   return True

            except:
                self.logger.info("Malformed VMAF file. Recomputing")
                os.remove(file_in)
                return False
        return False

    
    def read_psnr(self, file_in):
        try:
            with open(file_in, 'r') as fin:
                self._psnr = float(fin.readlines()[0])
                return True
        except:
            return False
    
    def load_psnr(self,
            reference_video,
            store_file,
            cache=False,
            cache_file=None):
        

        if cache:
            self.logger.debug("Caches have been enabled")
            assert cache_file is not None, "Cache selected, cache file must be not None"
            done = self.read_psnr(cache_file)
            if done:
                if os.path.exists(store_file):
                    self.logger.debug("File out {} exist. Removing it".format(store_file))
                    os.remove(store_file)
                self.logger.debug("Copying cache {} to {}".format(cache_file, store_file))
                pmkdir(os.path.dirname(store_file))  
                copyfile(cache_file, store_file)
                return self._psnr
                
            else:
                done = self._psnr(store_file)
                if done:
                    self.logger.debug("File out {} exists. Copying it into cache".format(store_file))
                    pmkdir(os.path.dirname(cache_file))  
                    copyfile(store_file, cache_file)
                    return self._psnr
 
        if self._psnr:
            return self._psnr

        done = self.read_psnr(store_file)
        if done:
            if cache:
                pmkdir(os.path.dirname(cache_file))  
                copyfile(store_file, cache_file)    
            return self._psnr

         
        pmkdir(os.path.dirname(store_file))
        target_resolution = reference_video.video().load_resolution().split('x')
        cmd = 'ffmpeg -i {} -i {} -lavfi "[0]scale={}:{}[a];[a][1]psnr" -f null /dev/null'.format(self.video().video_path(), reference_video.video().video_path(), target_resolution[0], target_resolution[1])
        self.logger.info("Exectuting PSNR command {}".format(cmd))
        proc = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outs, errs = proc.communicate()
        
        psnr = float(outs.decode("utf-8").split("average:")[1].split("min")[0])
        with open(store_file, 'w') as fout:
            fout.write(str(psnr))

        assert os.path.exists(store_file), "vmaf didn't compute correctly. Command: {}".format(cmd)
       
        done = self.read_psnr(store_file)
        if not done:
            self.logger.error("PSNR couldn't compute correctly. Exiting")
            sys.exit(-1)
        
        if cache:
            pmkdir(os.path.dirname(cache_file))  
            copyfile(store_file, cache_file)    
        return self._psnr

    

    def load_vmaf( self, 
                   reference_video, 
                   store_file, 
                   vmaf_model_name,
                   cache=False,
                   cache_file=None):
        
        if cache:
            self.logger.debug("Caches have been enabled")
            assert cache_file is not None, "Cache selected, cache file must be not None"
            done = self.read_vmaf_file(cache_file)
            if done:
                if os.path.exists(store_file):
                    self.logger.debug("File out {} exist. Removing it".format(store_file))
                    os.remove(store_file)
                self.logger.debug("Copying cache {} to {}".format(cache_file, store_file))
                pmkdir(os.path.dirname(store_file))  
                copyfile(cache_file, store_file)
                return self._vmaf_data
                
            else:
                done = self.read_vmaf_file(store_file)
                if done:
                    self.logger.debug("File out {} exists. Copying it into cache".format(store_file))
                    pmkdir(os.path.dirname(cache_file))  
                    copyfile(store_file, cache_file)
                    return self._vmaf_data
 
        if self._vmaf_data:
            if len(self._vmaf_data) == self._video.load_total_frames():
                self.logger.debug("VMAF data already loaded. Frames count coincide")
                return self._vmaf_data
            else:
                self.logger.debug("VMAF data already loaded, but frame counts corrupted. Re-loading")
        
        done = self.read_vmaf_file(store_file)
        if done:
            self.logger.debug("Vmaf data not yet loaded but already computed. Returning it")
            if cache:
                pmkdir(os.path.dirname(cache_file))  
                copyfile(store_file, cache_file)    
            return self._vmaf_data

        if vmaf_model_name == VMAF_4K:
            self.logger.debug("Vmaf 4k model selected")
        elif vmaf_model_name == VMAF_HDTV:
            self.logger.debug("Vmaf hdtv model selected")
        elif vmaf_model_name == VMAF_MOBILE:
            self.logger.debug("Vmaf mobile model selected")
        else:
            self.logger.error("Vmaf model = {} unknown".format(vmaf_model_name))
      

        if not os.path.exists(VMAF_SCRIPT_PATH):
           self.logger.error("vmaf script = {}  doesn't exist. Check if the path is correct".format(VMAF_SCRIPT_PATH))
           sys.exit(-1)


       ## configuration of the correct model

        vmaf_mobile = ""
        if vmaf_model_name == VMAF_4K:
           resolution_width = VMAF_4K_WIDTH
           resolution_height = VMAF_4K_HEIGHT
           vmaf_model_path = VMAF_4K_MODEL
        else:
           resolution_width = VMAF_HDTV_WIDTH
           resolution_height = VMAF_HDTV_HEIGHT
           vmaf_model_path = VMAF_HDTV_MODEL
           if vmaf_model_name == VMAF_MOBILE:
               vmaf_mobile = VMAF_MOBILE_OPT       

        cmd = VMAF_CMD.format(  VMAF_SCRIPT_PATH,
                               reference_video._video.video_path(), 
                               self._video.video_path(), 
                               resolution_width, 
                               resolution_height, 
                               vmaf_model_path, 
                               store_file, vmaf_mobile)
       
        pmkdir(os.path.dirname(store_file))
        print("store_file dir created sucessfully:",os.path.dirname(store_file))
        print(store_file,"is exist:",os.path.exists(store_file))
        self.logger.info("Exectuting vmaf command {}".format(cmd))
        proc = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outs, errs = proc.communicate()
        assert os.path.exists(store_file), "vmaf didn't compute correctly. Command: {}".format(cmd)
       
        done = self.read_vmaf_file(store_file)
        if not done:
            self.logger.error("Vmaf couldn't compute correctly. Exiting")
            sys.exit(-1)
        
        if cache:
            pmkdir(os.path.dirname(cache_file))  
            copyfile(store_file, cache_file)    
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
            fout = os.path.join(vmaf_store_dir, "{}.json".format(s.seqno()))
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
            fout = os.path.join(ffprobe_store_dir, "{}.json".format(s.seqno()))
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
    
