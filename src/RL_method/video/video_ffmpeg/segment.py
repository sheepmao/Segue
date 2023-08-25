from src.utils.video_ffmpeg.video import Video

class Segment:
    def __init__(self, video, seqno, frame_start, frame_end, time_start, time_end):
       
        self._video = video
        self._seqno = seqno
        self._frame_start = int(frame_start)
        self._frame_end = int(frame_end)
        self._time_start = time_start
        self._time_end = time_end

        assert self._seqno >= 0
        assert self._frame_start >= 0 and self._frame_start < self._frame_end
        assert self._time_start >= 0 and self._time_start < self._time_end
        assert self._frame_end - self._frame_start == self._video.load_total_frames()

        self._vmaf_data = None
        self._ffprobe_data = None
        
        self._ffprobe_duration = None
        self._ffprobe_size = None

    def seqno(self):
        return self._seqno

    def video(self):
        return self._video

    def assign_vmaf(self, vmaf_arr):
        assert len(vmaf_arr) == self._video.load_total_frames(), "Inconsistent frame range"
        self._vmaf_data = vmaf_arr
    
    def vmaf(self):
        assert self._vmaf_data, "Vmaf not yet assigned"
        return self._vmaf_data
   
    def assign_ffprobe(self, ffprobe_arr):
        assert len(ffprobe_arr) == self._video.load_total_frames(), "Inconsistent frame range"
        self._ffprobe_data = ffprobe_arr
    
    def ffprobe(self):
        assert self._ffprobe_data, "FFprobe not yet assigned"
        return self._ffprobe_data
    
    def frame_range(self):
        return self._frame_start, self._frame_end

    def load_ffprobe_duration(self):
        if self._ffprobe_duration:
            return self._ffprobe_duration
        elif self._ffprobe_data:
            return sum([x[0] for x in self._ffprobe_data])
        else:
            sys.exit(-1)

    def load_ffprobe_size(self):
        if self._ffprobe_size:
            return self._ffprobe_size
        elif self._ffprobe_data:
            return sum([x[1] for x in self._ffprobe_data])
        else:
            sys.exit(-1)
