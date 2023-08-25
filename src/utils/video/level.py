import sys
import copy
import math
import inspect
import numpy as np
from src.consts.simulation_file_consts import *
from src.consts.grouper_configs_consts import BYTES_OPT
from src.consts.manifest_representation_consts import *

M_IN_K = 1000.0
B_IN_BYTE = 8

def get_caller_name():
    """Returns the name of the caller function."""
    return inspect.stack()[2][3]

class Level:
    """
    Represents a level(resolution) in a video stream. 
    A level consists of multiple fragments (segments) of the video.
    This class provides methods to merge levels and compute various attributes of the level.
    """

    def __init__(self, fragments, OPT=BYTES_OPT[1], logger=None, is_augmented=False):
        """
        Initializes the Level object.
        
        :param fragments: List of video fragments that make up this level.
        :param OPT: Optimization option. Default is BYTES_OPT[1].
        :param logger: Logger object for logging messages. Default is None.
        :param is_augmented: Indicates if the level is augmented. Default is False.
        """
        # Ensure there are fragments present
        assert len(fragments) > 0
        
        # Set the fragments, optimization option, and other attributes
        self._fragments = tuple(fragments)
        assert OPT in BYTES_OPT 
        self.bytes_opt = OPT
        
        # Initialize attributes for lazy loading
        self._duration = None
        self._bitrate = None
        self._bytes = None
        self._total_frames = None
        self._vmaf = None
        self._resolution = None 
        self._sim_data = None
        self._csv_std_data = None
        self._csv_aug_data = None
        self._is_augmented = is_augmented
        self.logger = logger

    def __eq__(self, other):
        """Determines if two Level objects are equal based on their properties."""
        def ret_neq(val1, val2):
            return val1 == val2
        
        # Check if bytes, resolution, and augmentation status are the same for both levels
        return all([
            ret_neq(self.load_bytes(-1), other.load_bytes(-1)),
            ret_neq(self.load_resolution(-1), other.load_resolution(-1)),
            ret_neq(self._is_augmented, other._is_augmented)
        ])

    def debug_print_aug(self):
        """Generates a debug string with augmented details of the Level."""
        debug_p = '****\n'
        debug_p += 'resolution ==> {}\n'.format(self._resolution)
        debug_p += 'bytes ==> {}\n'.format(self._bytes)
        debug_p += 'vmaf ==> {}\n'.format(self._vmaf)
        debug_p += 'bitrate ==> {}\n'.format(self._bitrate)
        return debug_p

    def log_msg(self, msg, info=False):
        """Logs a message prefixed with the name of the caller function."""
        msg = "{} -> {}".format(get_caller_name(), msg)
        if self.logger:
            self.logger.info(msg) if info else self.logger.debug(msg)

    def copy(self):
        """Creates a deep copy of the Level object."""
        level = Level(self._fragments, OPT=self.bytes_opt, logger=self.logger)
        level._duration = self._duration
        level._bitrate = self._bitrate
        level._bytes = self._bytes
        level._total_frames = self._total_frames
        level._vmaf = self._vmaf
        level._resolution = self._resolution
        level._sim_data = self._sim_data
        level._is_augmented = self._is_augmented
        return level

    def debug_print(self, idx):
        """Generates a debug string with details of the Level for a specific index."""
        msg = ''
        msg += "{} --> dur {}\n".format(idx, self.load_duration(idx))
        msg += "{} --> bytes {}\n".format(idx, self.load_bytes(idx)) 
        msg += "{} --> bitrate {}\n".format(idx, self.load_bitrate(idx)) 
        msg += "{} --> composed by {} fragments\n".format(idx, len(self._fragments)) 
        return msg

    # The following methods load various properties of the level.
    # They use lazy loading: if the property was previously computed, it returns the cached value.
    # Otherwise, it computes the property from the underlying fragments and caches the result.

    def load_resolution(self, idx):
        """Loads and returns the resolution of the level."""
        if self._resolution:
            self.log_msg("idx:{}, Resolution already computed: {}".format(idx, self._resolution))
            return self._resolution
        
        for fr in self._fragments:
            if self._resolution:
                if fr.video().load_resolution() != self._resolution:
                    self.log_msg("Inconsisted resolution among assembled fragments {} != {}".format(self._resolution, fr.video().load_resolution()), info=True)
                    sys.exit(-1)
            else:
                self._resolution = fr.video().load_resolution()

        self.log_msg("idx: {}, Resolution computed: {}".format(idx, self._resolution))
        return self._resolution

    def load_duration(self, idx):
        """Loads and returns the total duration of the level."""
        if self._duration:
            self.log_msg("idx:{}, Duration already computed: {}".format(idx, self._duration))
            return self._duration
        
        self._duration = sum(fr.video().load_duration() for fr in self._fragments)
        self.log_msg("idx: {}, Duration computed: {}".format(idx, self._duration))
        return self._duration

    def load_bytes(self, idx):
        """Loads and returns the total bytes of the level."""
        if self._bytes:
            self.log_msg("idx:{}, Bytes already computed: {}".format(idx, self._bytes))
            return self._bytes

        self._bytes = 0
        for fr in self._fragments:
            if self.bytes_opt == BYTES_OPT[0]:
                try:
                    self._bytes += fr.load_ffprobe_size()
                except:
                    self.log_msg("Cannot load from ffprobe")
                    sys.exit(-1)
            else:
                self._bytes += fr.video().load_bytes()
        
        self.log_msg("idx:{}, Bytes computed: {}".format(idx, self._bytes))
        return float(self._bytes)

    def load_vmaf(self, idx):
        """Loads and returns the VMAF (Video Multi-method Assessment Fusion) score list of the level."""
        if self._vmaf:
            self.log_msg("idx:{}, vmaf list already computed: mean {}".format(idx, np.mean(self._vmaf)))
            return self._vmaf
        #create a list of vmaf scores for each frame and then compute the mean
        self._vmaf = []
        for fr in self._fragments:
            self._vmaf += fr.vmaf()
        
        self.log_msg("idx:{}, Average VMAF is: {}".format(idx, np.mean(self._vmaf)))
        return self._vmaf
 
 



    def load_bitrate(self, idx):
        """Loads and returns the bitrate of the level."""
        if self._bitrate:
            self.log_msg("idx:{}, Bitrate already computed: {}".format(idx, self._bitrate))
            return self._bitrate


        self._bitrate = (self.load_bytes(idx) * B_IN_BYTE)/self.load_duration(idx)/M_IN_K #kbits
        self.log_msg("idx:{}, Bitrate computed: {}".format(idx, self._bitrate))
        return self._bitrate

    def load_total_frames(self, idx):
        """Loads and returns the total number of frames in the level."""
        if self._total_frames:
            self.log_msg("idx:{}, Total frames already computed: {}".format(idx, self._total_frames))
            return self._total_frames
       
        self._total_frames = sum(fr.video().load_total_frames() for fr in self._fragments)
        
        self.log_msg("idx:{}, Total frames computed: {}".format(idx, self._total_frames))
        return self._total_frames

    def merge(self, other, idx):
        """Merges this Level with another Level and returns the merged Level."""
        assert isinstance(other, Level), "Not correct instance"
        new_fr = self._fragments + other._fragments
        self.log_msg("Assembled idx:{}, composed by {} + {} fragments".format(idx, len(self._fragments), len(other._fragments)))
        return Level(new_fr, OPT=self.bytes_opt, logger=self.logger)

    def get_simulation_data(self, idx):
        """Returns simulation data for this Level."""
        if self._sim_data:
            return self._sim_data

        l = {
            SIM_FILE_RESOLUTION: self.load_resolution(idx),
            SIM_FILE_BYTES: self.load_bytes(idx),
            SIM_FILE_BITRATE: self.load_bitrate(idx),
            SIM_FILE_VMAF: np.mean(self.load_vmaf(idx)),
            SIM_FILE_VMAF_PER_FRAME: self.load_vmaf(idx),
            SIM_FILE_IS_AUGMENTED: self._is_augmented
        }
        self._sim_data = l
        return l

    def get_level_csv_data_std(self, idx):
        """Returns standard CSV data for this Level."""
        if self._csv_std_data:
            return self._csv_std_data
        
        self._csv_std_data = {
            BITRATE_CSV_STD.format(self.load_resolution(idx)): self.load_bitrate(idx),
            VMAF_CSV_STD.format(self.load_resolution(idx)): np.mean(self.load_vmaf(idx)),
            BYTES_CSV_STD.format(self.load_resolution(idx)): self.load_bytes(idx)
        }
        return self._csv_std_data

    def get_level_csv_data_aug(self, idx):
        """Returns augmented CSV data for this Level."""
        if self._csv_aug_data:
            self._csv_aug_data[INDEX_CSV] = idx
            return self._csv_aug_data
        
        self._csv_aug_data = {
            INDEX_CSV: idx,
            DURATION_CSV: self.load_duration(idx),
            RESOLUTION_CSV: self.load_resolution(idx),
            BITRATE_CSV_AUG: self.load_bitrate(idx),
            VMAF_CSV_AUG: np.mean(self.load_vmaf(idx)),
            BYTES_CSV_AUG: self.load_bytes(idx)
        }
        return self._csv_aug_data
