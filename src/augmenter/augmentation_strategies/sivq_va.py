from src.augmenter.augmentation_strategies.augmenter import Augmenter
from src.consts.augmenter_consts import *
from src.utils.video.level import Level
import numpy as np

class SivqVA(Augmenter):

    def __init__(   self, raw_video,
                    rescaled_videos, ss,
                    original_segments_dir,
                    augmented_dir_out,
                    augmentation_module_args,
                    splitting_module_args,
                    log_dir, figs_dir,
                    verbose=False):
    
        super().__init__(   raw_video,
                            rescaled_videos, ss,
                            original_segments_dir,
                            augmented_dir_out,
                            augmentation_module_args,
                            splitting_module_args,
                            log_dir, figs_dir,
                            verbose=False)

    def augment(self, multiresolution_video):

        self.logger.info("Initializing augmentation")
        self.logger.info("First, launching encoding process")
        resolution_list  = []
        
        augmented_videos = self.ae.make_augmented_segments()
        augmented_videos_map = {}
        for video in augmented_videos:
            augmented_videos_map[video.video().load_resolution()] = video


        baseline_video_map = {}
        for video in self.rescaled_videos:
            baseline_video_map[video.video().load_resolution()] = video
            resolution_list.append(video.video().load_resolution())

        resolution_list = sorted(resolution_list, key=lambda x: int(x.split('x')[0]))
        chunks_no = len(self.rescaled_videos[0].load_segments())
        
        add_all_map = {}

        
        for video in self.rescaled_videos:
            for i, segment in enumerate(video.load_segments()):
                level = augmented_videos_map[video.video().load_resolution()].load_segments()[i]
                level = Level([level])
                    
                if i not in add_all_map.keys():
                    add_all_map[i] = []

                add_all_map[i].append(level)
    
        multires_video = multiresolution_video.add_levels(add_all_map)
        
        remove_map = {}

        self.logger.info("Chunks no is {}".format(chunks_no))

        vmaf_treshold = float(self.augmentation_module_args[K_AUGMENTER_VMAF_TH])
        
        self.logger.info("Threshold for beta V is {} vmaf points".format(vmaf_treshold))

        for i, segment in enumerate(multires_video.segments()):
            to_keep = []
            for j, l in enumerate(segment.levels):
                tmp = j
                segment_vmaf = np.mean(l.load_vmaf(j))
                segment_size = l.load_bytes(j)
                
                vmaf_th = segment_vmaf - vmaf_treshold
                for k, lk in enumerate(segment.levels):
                    k_segment_vmaf = np.mean(lk.load_vmaf(k))
                    k_segment_size = lk.load_bytes(k)
                    if k_segment_vmaf > vmaf_th:
                        if k_segment_size < segment_size:
                            tmp = k
                            segment_vmaf = np.mean(lk.load_vmaf(k))
                            segment_size = lk.load_bytes(k)
                
                if tmp != j:
                    self.logger.info("Representation {} can be substituted by representation {}".format(j,tmp))
                else:
                    self.logger.info("Representation {} can't be substituted".format(tmp))
                if tmp not in to_keep:
                    to_keep.append(tmp)
            
            if i == 0 and len(to_keep) == 1:
                to_keep.append(to_keep[0] + 1)

            for j, l in enumerate(segment.levels):
                if j not in to_keep:
                    if i not in remove_map.keys():
                        remove_map[i] = []
                    remove_map[i].append(l)
                    
            
        multires_video = multires_video.remove_levels(remove_map)
        return multires_video







