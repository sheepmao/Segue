import sys,os
from src.utils.video_ffmpeg.video import Video as FFmpegVideo
from src.utils.video_ffmpeg.full_video import FullVideo as FFmpegFullVideo
from src.utils.video_ffmpeg.segment import Segment as FFMpegSegment

from src.utils.video_csv.video import Video as CsvVideo
from src.utils.video_csv.full_video import FullVideo as CsvFullVideo
from src.utils.video_csv.segment import Segment as CsvSegment

if os.environ.get("SEGUE_VIDEO","") == "CSV":
    Video = CsvVideo
    FullVideo = CsvFullVideo
    Segment = CsvSegment
    EXTENSION = 'fqa'
else:
    Video = FFmpegVideo
    FullVideo = FFmpegFullVideo
    Segment = CsvSegment
    EXTENSION = 'mp4'
