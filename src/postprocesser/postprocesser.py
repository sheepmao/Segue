import numpy as np
import pandas as pd
import os, json
from src.consts.simulation_recap_consts import *
from src.consts.simulation_file_consts import *
from src.consts.postprocessing_consts import *
import glob, sys
import traceback

### Postprocesser ###
### General aggregation across multiple videos X ABR x Segue_Scheme


startup_delay = 10.0


class SegueScheme:
    def __init__(self, grouper_name, augmenter_name, nickname):
        
        self.grouper_name = grouper_name
        self.augmenter_name = augmenter_name
        self.nickname = nickname
    
    def __eq__(self, obj):
        return isinstance(obj, SegueScheme) and obj.grouper_name == self.grouper_name and obj.augmenter_name == self.augmenter_name


class Experiment:
    def __init__(self, csv_file, simulation_file, trace_file, cache_file=None):
        
        self.sim_file = simulation_file
        self.t_vmaf = None
        self.t_vmaf_switches = None
        self.total_rebuf = None
        self.total_rebuf_no_startup = None
        self.total_duration = None

        try:
            with open(cache_file, 'r') as fin:
                datas = json.load(fin)
            
            self.vmaf_unit_time = datas[CACHE_VMAF_DUMP]
            self.vmaf_switches_unit_time = datas[CACHE_SWITCHES_UNIT_TIME]
            self.reward = datas[CACHE_REWARD] 
            
            self.index_downloaded = datas[CACHE_QUALITY_INDEX_SIM]
            #self.resolution_downloaded = datas[CACHE_RESOLUTION_SIM]
            #self.bitrate_downloaded = datas[CACHE_BITRATE_SIM]
            
            self.rebuffering = datas[CACHE_REBUF_SIM]
            self.total_rebuf = sum(self.rebuffering)

            self.rebuffering_no_startup = datas[CACHE_REBUF_SIM_NO_STARTUP]
            self.total_rebuf_no_startup = sum(self.rebuffering_no_startup)
            
            
            #self.average_vmaf_downloaded = datas[CACHE_VMAF_SIM]

            self.trace_file = trace_file
            self.buffer_state_raw = (datas[CACHE_TIME_SIM], datas[CACHE_BUFFER_STATE_SIM])
            
            self.buffer_state_seconds = datas[CACHE_BUFFER_STATE_SECOND_SIM]
            self.vmaf_per_frame = datas[CACHE_VMAF_PER_FRAME]
            #self.trace = datas[CACHE_TRACES]
            self.cache_file = cache_file
        
        except:
            self.reward = None
            self.vmaf_unit_time = None
            self.vmaf_switches_unit_time = None

            try:
                raw_data = pd.read_csv(csv_file)
            except:
                print(csv_file)
                sys.exit(-1)
            assert os.path.exists(simulation_file)
        

            
            self.index_downloaded = raw_data[QUALITY_INDEX_SIM].tolist()
            #self.resolution_downloaded = raw_data[RESOLUTION_SIM].tolist()
            #self.bitrate_downloaded = raw_data[BITRATE_SIM].tolist()

            self.rebuffering = [ x for x in raw_data[REBUF_SIM] ]
            #self.average_vmaf_downloaded = raw_data[VMAF_SIM].tolist()

            self.total_rebuf = sum(self.rebuffering)


            self.trace_file = trace_file
            self.buffer_state_raw = (raw_data[TIME_SIM].tolist(), raw_data[BUFFER_STATE_SIM].tolist())
            
            self.rebuffering_no_startup = []
            trigger = -1
            
            for i, b in enumerate(self.buffer_state_raw[1]):
                if b >= startup_delay:
                    trigger = i + 1
                    break

            self.rebuffering_no_startup = self.rebuffering[trigger:]
            self.total_rebuf_no_startup = sum(self.rebuffering_no_startup)
            
            self.buffer_state_seconds = []
            
            time_iterator = 0
            buffer_state = 0
            raw_buffer_iterator = 0
            time_step = 1000.0
            
            while raw_buffer_iterator < len(raw_data[TIME_SIM]):
                time_iterator += time_step
                if time_iterator >= raw_data[TIME_SIM][raw_buffer_iterator]:
                    buffer_state = max(raw_data[BUFFER_STATE_SIM][raw_buffer_iterator]*1000 - (time_iterator - raw_data[TIME_SIM][raw_buffer_iterator]), 0)
                    raw_buffer_iterator += 1
                else:
                    buffer_state = max(0, buffer_state - time_step)
                self.buffer_state_seconds.append(buffer_state)

            while buffer_state > 0:
                buffer_state -= time_step
                self.buffer_state_seconds.append(max(buffer_state, 0))
                

            simulation_data = None
            with open(simulation_file, 'r') as fin:
                simulation_data = json.load(fin)

            self.vmaf_per_frame = []
            
            for i, down in enumerate(self.index_downloaded):
                self.vmaf_per_frame += simulation_data[str(i)][SIM_FILE_LEVELS][down][SIM_FILE_VMAF_PER_FRAME]
            
            #self.trace = []

           # with open(trace_file, 'r') as fin:
           #     lines = fin.readlines()
           #     for line in lines:
           #         line = line.split()
           #         self.trace.append((float(line[0]), float(line[1])))
           # 
            self.cache_file = cache_file
        
    

    def load_reward(self, reward_module):
        if self.reward:
            return self.reward
        self.vmaf_unit_time, self.vmaf_switches_unit_time, self.reward = reward_module.evaluate_reward_per_unit_time([self.vmaf_per_frame, self.rebuffering], return_list=True)
        self.vmaf_unit_time = self.vmaf_unit_time[:-1]
        self.vmaf_switches_unit_time = self.vmaf_switches_unit_time[:-1]

        self.t_vmaf = sum(self.vmaf_unit_time)/len(self.vmaf_unit_time)
        self.t_vmaf_switches = sum(self.vmaf_switches_unit_time)/len(self.vmaf_switches_unit_time)
 
        if self.cache_file:
            data = {}
            data[CACHE_VMAF_DUMP] = self.vmaf_unit_time
            data[CACHE_REWARD] = self.reward
            data[CACHE_SWITCHES_UNIT_TIME] = self.vmaf_switches_unit_time
            data[CACHE_QUALITY_INDEX_SIM] = self.index_downloaded
            #data[CACHE_RESOLUTION_SIM] = self.resolution_downloaded
            #data[CACHE_BITRATE_SIM] =  self.bitrate_downloaded 
            data[CACHE_REBUF_SIM] =  self.rebuffering 
            data[CACHE_REBUF_SIM_NO_STARTUP] = self.rebuffering_no_startup
            #data[CACHE_VMAF_SIM] =  self.average_vmaf_downloaded 
    
            data[CACHE_TIME_SIM] = self.buffer_state_raw[0]
            data[CACHE_BUFFER_STATE_SIM] = self.buffer_state_raw[1]
            
            data[CACHE_BUFFER_STATE_SECOND_SIM] =  self.buffer_state_seconds 
            data[CACHE_VMAF_PER_FRAME] = self.vmaf_per_frame 
            #data[CACHE_TRACES] = self.trace 
        

            with open(self.cache_file, 'w') as fout:
                json.dump(data, fout)
        return self.reward
    
    def get_reward(self):
        if self.reward:
            return self.reward
        else:
            return None
    
    
    def load_rebuffer_ratio(self):
        
        total_rebuffering = self.total_rebuffering(enable_first=False)
        if not self.total_duration:
            self.total_duration = sum(self.load_duration_sequence())

        return total_rebuffering/self.total_duration


    def load_total_segments_no(self):
        with open(self.sim_file, 'r') as fin:
            data = json.load(fin)
        return len(data)
    
    def load_duration_sequence(self):
        durations = []

        with open(self.sim_file, 'r') as fin:
            data = json.load(fin)
            for i in range(len(data)):
                durations.append(float(data[str(i)][SIM_FILE_DURATION]))
        return durations

    
    def load_bytes_sequence(self, preferred_index=-1):
        bytess = []

        with open(self.sim_file, 'r') as fin:
            data = json.load(fin)
            for i in range(len(data)):
                    bytess.append(float(data[str(i)][SIM_FILE_LEVELS][preferred_index][SIM_FILE_BYTES]))
        return bytess


    def load_vmaf_sequence(self, preferred_index=-1): ## don't run this with augmentation
        vmafs = {}

        with open(self.sim_file, 'r') as fin:
            data = json.load(fin)
            for i in range(len(data)):
                for j in range(len(data[str(i)][SIM_FILE_LEVELS])):
                    level = data[str(i)][SIM_FILE_LEVELS][j]
                    if not level[SIM_FILE_IS_AUGMENTED]:
                        if level[SIM_FILE_RESOLUTION] not in vmafs.keys():
                            vmafs[level[SIM_FILE_RESOLUTION]] = []
                        vmafs[level[SIM_FILE_RESOLUTION]] += level[SIM_FILE_VMAF_PER_FRAME]
        return vmafs 
    
    def load_bitrate_sequence(self, preferred_index=-1):
        bitrate = []

        with open(self.sim_file, 'r') as fin:
            data = json.load(fin)
            for i in range(len(data)):
                    bitrate.append(float(data[str(i)][SIM_FILE_LEVELS][preferred_index][SIM_FILE_BITRATE]))
        return bitrate


    
    def rebuf_probability(self):
        rebuf_prob = []
        
        for c in self.rebuffering_no_startup:
            if c > 0:
                rebuf_prob.append(1)
            else:
                rebuf_prob.append(0)
        
        startup_segments = len(self.rebuffering) - len(self.rebuffering_no_startup)
        rebuf_prob = [ 0 for x in range(startup_segments) ] + rebuf_prob
        return rebuf_prob

    def total_rebuffering(self, enable_first=True):
        if not enable_first:
            if self.total_rebuf_no_startup:
                return self.total_rebuf_no_startup
            return sum(self.rebuffering_no_startup)
        else:
            if self.total_rebuf:
                return self.total_rebuf

            return sum(self.rebuffering)

    def load_startup(self):
        return sum(self.rebuffering) - sum(self.rebuffering_no_startup)
    
    def total_vmaf(self):
        if self.t_vmaf:
            return self.t_vmaf

        if self.vmaf_unit_time:
            return sum(self.vmaf_unit_time)/len(self.vmaf_unit_time)
        else:
            return None

    def total_vmaf_switches(self):
        if self.t_vmaf_switches:
            return self.t_vmaf_switches

        if self.vmaf_switches_unit_time:
            return sum(self.vmaf_switches_unit_time)/len(self.vmaf_switches_unit_time)
        else:
            return None

    def metric(self, metric, enable_first=True):
        if metric == METRICS[0]:
            return self.total_rebuffering(enable_first=enable_first)
        elif metric == METRICS[1]:
            return self.total_vmaf()
        elif metric == METRICS[2]:
            return self.total_vmaf_switches()
        elif metric == METRICS[3]:
            return self.load_rebuffer_ratio()
        elif metric == METRICS[4]:
            return self.load_startup()
        else:
            sys.exit(-1)



class ExperimentSet:
    def __init__(self,  video_name, 
                        abr_module_name, 
                        segue_scheme,
                        simulation_file, logger, cache_directory=None):


        self.video_name = video_name
        self.abr_module_name = abr_module_name
        self.segue_scheme = segue_scheme
        self.simulation_file = simulation_file
        self.cache_directory = cache_directory
        self.logger = logger

        self.logger.debug("Creating experiment set")
        self.logger.debug("Video name ==> {}".format(self.video_name))
        self.logger.debug("ABR name ==> {}".format(self.abr_module_name))
        self.logger.debug("SEGUE scheme ==> {}".format(self.segue_scheme.nickname))
        self.logger.debug("SIM FILE ==> {}".format(self.simulation_file))

        # lazy load
        self.experiments = None
        self.rewards = None
    
    def to_string(self):
        string = ''
        string += 'video name {} === '.format(self.video_name)
        string += 'abr name {} === '.format(self.abr_module_name)
        string += 'segue scheme nickname {}'.format(self.segue_scheme.nickname)
        return string
    

    def load_segments_durations(self, normalization_experiment=None):
        assert self.experiments
        if normalization_experiment:
            norm = np.mean(normalization_experiment.load_segments_durations())
        else:
            norm = 1
        return [ x/norm for x in self.experiments[0].load_duration_sequence()]
    
    def load_segments_bytes(self,  normalization_experiment=None):
        assert self.experiments
        if normalization_experiment:
            norm = np.mean(normalization_experiment.load_segments_bytes())
        else:
            norm = 1
        return [ x/norm for x in  self.experiments[0].load_bytes_sequence()]

    def load_segments_bitrates(self, normalization_experiment=None):
        assert self.experiments
        
        if normalization_experiment:
            norm = np.mean(normalization_experiment.load_segments_bitrates())
        else:
            norm = 1

        return [ x/norm for x in self.experiments[0].load_bitrate_sequence()]

    def load_segments_no(self, normalization_experiment=None):
        assert self.experiments
        if normalization_experiment:
            norm = normalization_experiment.load_segments_no()
        else:
            norm = 1
        return self.experiments[0].load_total_segments_no()/ norm
    
    def load_vmaf_sequence(self):
        assert self.experiments
        return self.experiments[0].load_vmaf_sequence()

    def average_buffer_state_per_segment(self):
        
        max_len = -1
        for exp in self.experiments:
            if len(exp.buffer_state_raw[1]) > max_len:
                max_len = len(exp.buffer_state_raw[1])

        average_per_segment = [0.0 for x in range(max_len)]
        
        for sec in range(max_len):
            for exp in self.experiments:
                try:
                    average_per_segment[sec] += exp.buffer_state_raw[1][sec]
                except:
                    average_per_segment[sec] += 0.0 # out of clarity xD
        
        average_per_segment = [x/len(self.experiments) for x in average_per_segment]
        return average_per_segment

    
    def rebuffer_prob(self):
        rebuffer_prob = None

        for exp in self.experiments:
            if rebuffer_prob == None:
                rebuffer_prob = exp.rebuf_probability()
            else:
                rebuffer_prob = [ x + y for x, y in zip(rebuffer_prob, exp.rebuf_probability())]
        
        rebuffer_prob = [ x/len(self.experiments) for x in rebuffer_prob]
        return rebuffer_prob

    
    def average_buffer_state(self, sample_each=1.0):
        max_len = -1
        for exp in self.experiments:
            if len(exp.buffer_state_seconds) > max_len:
                max_len = len(exp.buffer_state_seconds)

        average_per_seconds = [0.0 for x in range(max_len)]
        
        for sec in range(max_len):
            for exp in self.experiments:
                try:
                    average_per_seconds[sec] += exp.buffer_state_seconds[sec]
                except:
                    average_per_seconds[sec] += 0.0 # out of clarity xD
        
        average_per_seconds = [x/len(self.experiments) for x in average_per_seconds]
        return average_per_seconds


    def load_experiments(self, experiments_directory, traces_directory):
        if self.experiments:
            return self.experiments
        
        self.experiments = []
        self.experiments_by_trace_file = {}

        for trace_file in glob.glob(os.path.join(traces_directory, '*')):
            csv = os.path.basename(trace_file)
            cache_file = None
            self.logger.debug("Loading experiment trace ==> {}".format(csv))
            if self.cache_directory:
                cache_file = os.path.join(self.cache_directory, csv)
                self.logger.debug("Cache file is {}".format(cache_file))

            exp = Experiment(os.path.join(experiments_directory, "{}.csv".format(csv)), self.simulation_file, trace_file, cache_file=cache_file)
            self.experiments.append(exp)      
            self.experiments_by_trace_file[os.path.basename(trace_file)] = exp 

        return self.experiments
    
    def load_rewards(self, reward_module=None, normalized_by=None):
        assert self.experiments
        if not reward_module:
            assert self.rewards 

        mean_normalization = 1.0
        if normalized_by:
            assert isinstance(normalized_by, ExperimentSet)
            mean_normalization = normalized_by.mean_reward(normalized_by=None)
            if mean_normalization < 0:
                self.logger.warning("Warning: Mean reward is negative. Computing non normalized")
                mean_normalization = 1
            ### SENSITIVE HERE: need to include border cases
        
        if self.rewards:
            return [x/mean_normalization for x in self.rewards]
        
        self.rewards = []
        
        for experiment in self.experiments:
            self.rewards.append(experiment.load_reward(reward_module))
        
        return [x/mean_normalization for x in self.rewards]

    def mean_reward(self, normalized_by=None):
        assert self.rewards
        if normalized_by:
            assert isinstance(normalized_by, ExperimentSet)
            mean_normalization = normalized_by.mean_reward(normalized_by=None)
            if mean_normalization < 0:
                self.logger.warning("Warning: Mean reward is negative. Computing non normalized")
                mean_normalization = 1

            ### SENSITIVE HERE: need to include border cases
            return np.mean(self.rewards)/mean_normalization
        else:
            return np.mean(self.rewards)
    
    def perc_reward(self, perc, normalized_by=None):
        assert self.rewards
        if normalized_by:
            assert isinstance(normalized_by, ExperimentSet)
            mean_normalization = normalized_by.mean_reward(normalized_by=None)
            if mean_normalization < 0:
                self.logger.warning("Warning: Mean reward is negative. Computing non normalized")
                mean_normalization = 1

            ### SENSITIVE HERE: need to include border cases
            return np.percentile(self.rewards, perc)/mean_normalization
        else:
            return np.percentile(self.rewards, perc)
    
    def mean_metric(self, metric, enable_first=True, normalized_by=None):
        metrics = []
        for experiment in self.experiments:
            metrics.append(experiment.metric(metric, enable_first=enable_first))
        
        mean_normalization = 1.0
        if normalized_by:
            assert isinstance(normalized_by, ExperimentSet)
            mean_normalization = normalized_by.mean_metric(metric, enable_first=enable_first)
            assert mean_normalization > 0
        return np.mean(metrics)/mean_normalization

    def compare_reward(self, reference_set, m=1):
        reward_diff = []
        assert isinstance(reference_set, ExperimentSet)        
        for trace, experiment in self.experiments_by_trace_file.items():
            current = experiment.get_reward()
            ref = reference_set.experiments_by_trace_file[trace].get_reward()
            reward_diff.append(current - ref)

        return reward_diff
    
    def compare_metric(self, metric, reference_set, enable_first=True):
        reward_diff = []
        assert isinstance(reference_set, ExperimentSet)        
        for trace, experiment in self.experiments_by_trace_file.items():
            current = experiment.metric(metric, enable_first=enable_first)
            ref = reference_set.experiments_by_trace_file[trace].metric(metric, enable_first=enable_first)
            reward_diff.append(current - ref)
            #if metric == METRICS[1] and current - ref > 4:
            #    print(trace)
            #    print(current - ref)
        return reward_diff
        
    
    def perc_metric(self, metric, perc, enable_first=True, normalized_by=None):
        metrics = []
        for experiment in self.experiments:
            metrics.append(experiment.metric(metric, enable_first=enable_first))
        
        mean_normalization = 1.0
        if normalized_by:
            assert isinstance(normalized_by, ExperimentSet)
            mean_normalization = normalized_by.mean_metric(metric, enable_first=enable_first)
            assert mean_normalization > 0

        return np.percentile(metrics, perc)/mean_normalization

    def metric(self, metric, enable_first=True, normalized_by=None):

        metrics = []
        for experiment in self.experiments:
            metrics.append(experiment.metric(metric, enable_first=enable_first))
        
        mean_normalization = 1.0
        if normalized_by:
            assert isinstance(normalized_by, ExperimentSet)
            mean_normalization = normalized_by.mean_metric(metric, enable_first=enable_first)
            assert mean_normalization > 0
        
        return [m/mean_normalization for m in metrics]



## the post processor returns sets of dataframes
## these dataframes can be used for plotting or for retrieving numbers


class PostProcesser:
    def __init__(self, tuples, traces_directory, logger):
        
        self.sets = {}
        self.logger = logger

        for tupl in tuples:

            video_name = tupl[0] ## name of the video 
            if video_name not in self.sets.keys():
                self.sets[video_name] = {}
            
            abr_name = tupl[1] ## abr of the experiments
            if abr_name not in self.sets[video_name].keys():
                self.sets[video_name][abr_name] = []
           

            gr_name = tupl[2] ## grouper technique
            aug_name = tupl[3] ## augmentation technique
            nickname = tupl[4] ## how do you call the scheme
            sim_file = tupl[5] ## simulation file with all the needed informations
            experiments_dir = tupl[6] ## directory of the experiments
            reward_module = tupl[7] ## reward module accounted
            cache_dir = tupl[8]            
            
            self.logger.info("Creating segue scheme with GROPUER {} and AUGMENTER {}. Nickname {}".format(gr_name, aug_name, nickname))
            segue_scheme = SegueScheme(gr_name, aug_name, nickname)
            experiment_set = ExperimentSet(video_name, abr_name, segue_scheme, sim_file, logger, cache_directory=cache_dir)
            experiment_set.load_experiments(experiments_dir, traces_directory)
            experiment_set.load_rewards(reward_module=reward_module)
            
            self.sets[video_name][abr_name].append(experiment_set)
    
    
    def find_normalization_set(self, mode, grouper_name, augmenter_name, abr_name):
        normalization_set = {}
        if mode == 'none':
            for video, abrs_experiments in self.sets.items():
                normalization_set[video] = {}
                for abr, experiments in abrs_experiments.items():
                    normalization_set[video][abr] = None
        elif mode == 'custom':
            assert grouper_name
            assert augmenter_name
            for video, abrs_experiments in self.sets.items():
                normalization_set[video] = {}
                for abr, experiments in abrs_experiments.items():
                    scheme = SegueScheme(grouper_name, augmenter_name, '')
                    a_n = abr
                    if abr_name:
                        a_n = abr_name
                    normalization_set[video][abr] = self.get_set(video, a_n, scheme)
        elif mode == 'best':
            best_experiments = self.get_best_experiments()
            for video, abrs_experiments in self.sets.items():
                normalization_set[video] = {}
                for abr, experiments in abrs_experiments.items():
                    normalization_set[video][abr] = best_experiments[video]     
        else:
            sys.exit(-1)
        return normalization_set
    
    def get_best_experiments(self):
        self.best = {}
        for video, abrs_experiments in self.sets.items():
            self.best[video] = (None, None, None)
            for abr, experiments in abrs_experiments.items():
                for exp in experiments:
                    mean_reward = exp.mean_reward()
                    if self.best[video] == (None, None, None):
                        self.best[video] = (exp, mean_reward, abr)
                    else:
                        if self.best[video][1] < mean_reward:
                            self.best[video] = (exp, mean_reward, abr)
        
        return_dict = {}
        for video, b in self.best.items():
            return_dict[video] = b[0]

        return return_dict


    def get_set(self, video, abr, scheme):
        if scheme == None:
            return None
        
        for exp in self.sets[video][abr]:
            if scheme == exp.segue_scheme:
                return exp
        
        print("Scheme {} and {} with abr {}".format(scheme.grouper_name, scheme.augmenter_name, abr))
        print("Not Found")
        sys.exit(-1)

    
    def get_segments_stat(self, n_set):
        datas = {}
        for video, abrs_experiments in self.sets.items():
            d  = []
            for abr, experiments in abrs_experiments.items():
                normalization_experiment = n_set[video][abr]
                for exp in experiments:
                    data_point = {}
                    data_point[SCHEME_GROUPER_CSV] = exp.segue_scheme.grouper_name
                    data_point[SCHEME_AUGMENTER_CSV] = exp.segue_scheme.augmenter_name
                    data_point[SCHEME_LABEL] = exp.segue_scheme.nickname
                    data_point[SEGMENTS_DURATION_SEQUENCE_CSV] = exp.load_segments_durations(normalization_experiment=normalization_experiment)

                    data_point[SEGMENTS_BYTES_SEQUENCE_CSV] = exp.load_segments_bytes(normalization_experiment=normalization_experiment)
                    data_point[SEGMENTS_NO_CSV] = exp.load_segments_no(normalization_experiment=normalization_experiment)
                    data_point[SEGMENTS_BITRATE_SEQUENCE_CSV] = exp.load_segments_bitrates(normalization_experiment=normalization_experiment)
                    d.append(data_point)
            datas[video] = pd.DataFrame(d)
        return datas

    def get_reward_video_abr(self, n_set):
        
        datas = {}
        for video, abrs_experiments in self.sets.items():
            for abr, experiments in abrs_experiments.items():
                normalization_experiment = n_set[video][abr]
                d = []
                for exp in experiments:
                    
                    data_point = {}
                    data_point[VIDEO_NAME_CSV] = video
                    data_point[ABR_NAME_CSV] = abr
                    data_point[SCHEME_GROUPER_CSV] = exp.segue_scheme.grouper_name
                    data_point[SCHEME_AUGMENTER_CSV] = exp.segue_scheme.augmenter_name
                    data_point[SCHEME_LABEL] = exp.segue_scheme.nickname
                    
                    data_point[REWARD_MEAN_CSV] = exp.mean_reward(normalized_by=normalization_experiment)
                    data_point[REWARD_1_PERC_CSV] = exp.perc_reward(1, normalized_by=normalization_experiment)
                    data_point[REWARD_25_PERC_CSV] = exp.perc_reward(25, normalized_by=normalization_experiment)
                    data_point[REWARD_MEDIAN_CSV] = exp.perc_reward(50, normalized_by=normalization_experiment)
                    data_point[REWARD_75_PERC_CSV] = exp.perc_reward(75, normalized_by=normalization_experiment)
                    data_point[REWARD_99_PERC_CSV] = exp.perc_reward(99, normalized_by=normalization_experiment)

                    d.append(data_point)

                datas[(video, abr)] = pd.DataFrame(d) 
        return datas
    

    def get_rewards_list(self, n_set):
        
        datas = {}
        for video, abrs_experiments in self.sets.items():
            for abr, experiments in abrs_experiments.items():
                normalization_experiment = n_set[video][abr]
                d = []  
                for exp in experiments:
                    data_point = {}
                    
                    data_point[VIDEO_NAME_CSV] = video
                    data_point[ABR_NAME_CSV] = abr
                    data_point[SCHEME_GROUPER_CSV] = exp.segue_scheme.grouper_name
                    data_point[SCHEME_AUGMENTER_CSV] = exp.segue_scheme.augmenter_name
                    data_point[SCHEME_LABEL] = exp.segue_scheme.nickname
                    data_point[REWARDS_LIST] = exp.load_rewards(normalized_by=normalization_experiment) 
                    d.append(data_point)
                datas[(video, abr)] = pd.DataFrame(d) 
        return datas
        

    def get_metrics_list(self, n_set):
        
        datas = {}
        for video, abrs_experiments in self.sets.items():
            for abr, experiments in abrs_experiments.items():
                normalization_experiment = n_set[video][abr]
                d = []
                for exp in experiments:
                    
                    data_point = {}
                    data_point[VIDEO_NAME_CSV] = video
                    data_point[ABR_NAME_CSV] = abr
                    data_point[SCHEME_GROUPER_CSV] = exp.segue_scheme.grouper_name
                    data_point[SCHEME_AUGMENTER_CSV] = exp.segue_scheme.augmenter_name
                    data_point[SCHEME_LABEL] = exp.segue_scheme.nickname
                    
                    
                    data_point[REBUF_RATIO_LIST_CSV] = exp.metric(METRICS[3], normalized_by=normalization_experiment)
                    data_point[REBUF_LIST_CSV] = exp.metric(METRICS[0], normalized_by=normalization_experiment)
                    data_point[VMAF_LIST_CSV] = exp.metric(METRICS[1],normalized_by=normalization_experiment)
                    data_point[VMAF_SWITCHES_LIST_CSV] = exp.metric(METRICS[2],normalized_by=normalization_experiment)
                    data_point[REBUF_NO_STARTUP_LIST_CSV] = exp.metric(METRICS[0], enable_first=False,normalized_by=normalization_experiment)
                    d.append(data_point)
                datas[(video, abr)] = pd.DataFrame(d) 
        return datas
    

    def reward_comparison(self, r_set):
        
        datas = {}
        for video, abrs_experiments in self.sets.items():
            for abr, experiments in abrs_experiments.items():
                
                d = []
                reference_set = r_set[video][abr]
                
                for exp in experiments: 

                    data_point = {}
                    data_point[VIDEO_NAME_CSV] = video
                    data_point[ABR_NAME_CSV] = abr
                    data_point[SCHEME_GROUPER_CSV] = exp.segue_scheme.grouper_name
                    data_point[SCHEME_AUGMENTER_CSV] = exp.segue_scheme.augmenter_name
                    data_point[SCHEME_LABEL] = exp.segue_scheme.nickname
                    
                    mean_ref = reference_set.mean_reward()
                    data_point[REWARD_DIFF] = [ x/mean_ref for x in exp.compare_reward(reference_set, m=mean_ref)]

                    d.append(data_point)
                datas[(video, abr)] = pd.DataFrame(d) 
        return datas


    def metric_comparison(self, r_set):
        
        
        datas = {}
        for video, abrs_experiments in self.sets.items():
            for abr, experiments in abrs_experiments.items():
                d = []
                reference_set = r_set[video][abr]
                for exp in experiments: 

                    data_point = {}
                    data_point[VIDEO_NAME_CSV] = video
                    data_point[ABR_NAME_CSV] = abr
                    data_point[SCHEME_GROUPER_CSV] = exp.segue_scheme.grouper_name
                    data_point[SCHEME_AUGMENTER_CSV] = exp.segue_scheme.augmenter_name
                    data_point[SCHEME_LABEL] = exp.segue_scheme.nickname
                    
                    data_point[VMAF_DIFF] = [ x/reference_set.mean_metric(METRICS[1]) for x in exp.compare_metric(METRICS[1], reference_set)] 
                    data_point[REBUF_DIFF] =  [ x for x in exp.compare_metric(METRICS[0], reference_set) ]
                    data_point[SWITCHES_DIFF] = [ x/reference_set.mean_metric(METRICS[2]) for x in  exp.compare_metric(METRICS[2], reference_set) ]
                    data_point[REBUF_NO_STARTUP_DIFF] = [ x for x in  exp.compare_metric(METRICS[0], reference_set, enable_first=False) ]
                    data_point[REBUF_RATIO_DIFF] =  [ x for x in exp.compare_metric(METRICS[3], reference_set) ]
                    
                    d.append(data_point)
                datas[(video, abr)] = pd.DataFrame(d) 
        return datas

    
    
    def nm(self, exp, normalized, metric, mean=False, perc=-1, enable_first=True, norm=False):
        n = None
        if norm:
            n = normalized

        if mean:
            return (exp.mean_metric(metric, normalized_by=n, enable_first=enable_first) - 
                    normalized.mean_metric(metric, normalized_by=n, enable_first=enable_first))
        else:
            return (exp.perc_metric(metric, perc, normalized_by=n, enable_first=enable_first) - 
                    normalized.perc_metric(metric, perc, normalized_by=n, enable_first=enable_first))

    def nq(self, exp, reference, normalized, mean=False, perc=-1, enable_first=True, norm=True):
        n = None
        #if norm:
        #    n = normalized

        if mean:
            return (exp.mean_reward(normalized_by=n) - 
                    reference.mean_reward(normalized_by=n))
        else:
            return (exp.perc_reward(perc, normalized_by=n) - 
                    reference.perc_reward(perc, normalized_by=n))


    def get_distributions(self):
        
        
        datas = {}

        for video, abrs_experiments in self.sets.items():
            for abr, experiments in abrs_experiments.items():
                d = []
                for exp in experiments: 
                     
                    data_point = {}
                    data_point[VIDEO_NAME_CSV] = video
                    data_point[ABR_NAME_CSV] = abr
                    data_point[SCHEME_GROUPER_CSV] = exp.segue_scheme.grouper_name
                    data_point[SCHEME_AUGMENTER_CSV] = exp.segue_scheme.augmenter_name
                    data_point[SCHEME_LABEL] = exp.segue_scheme.nickname
                    
                    self.logger.info("Analyzing {} with {} and {}".format(video, abr, exp.segue_scheme.nickname))

                    dur = sum(exp.load_segments_durations())
                    
                    # array, one element per trace in the trace set, not normalized (intrinsecally normalized by the definition of rebuffer ratio)
                    data_point[REBUFFER_RATIO_DISTRIBUTION] = exp.metric(METRICS[3])
                    # array, one element per trace in the trace set, not normalized. It is already normalized by the unit time
                    data_point[VMAF_DISTRIBUTION] = exp.metric(METRICS[1])
                    data_point[STARTUP_DISTRIBUTION] = exp.metric(METRICS[4])
                    data_point[VMAF_SWITCHES_DISTRIBUTION] = exp.metric(METRICS[2])
                    data_point[QOE_DISTRIBUTION] = [ x/dur for x in exp.load_rewards() ]

 
                    d.append(data_point)
                datas[(video, abr)] = pd.DataFrame(d) 
        return datas


   
    def get_metrics_video_abr_diff_with_norm(self, n_set, n_vmaf=True, normalize_qoe=None):
        
        
        datas = {}

        for video, abrs_experiments in self.sets.items():
            for abr, experiments in abrs_experiments.items():
                d = []
                normalization_experiment = n_set[video][abr]
                
                if normalize_qoe:
                    n_qoe_experiment = normalize_qoe[video][abr]
                else:
                    n_qoe_experiment = normalization_experiment

                for exp in experiments: 
                     
                    data_point = {}
                    data_point[VIDEO_NAME_CSV] = video
                    data_point[ABR_NAME_CSV] = abr
                    data_point[SCHEME_GROUPER_CSV] = exp.segue_scheme.grouper_name
                    data_point[SCHEME_AUGMENTER_CSV] = exp.segue_scheme.augmenter_name
                    data_point[SCHEME_LABEL] = exp.segue_scheme.nickname
                    
                    self.logger.info("Analyzing {} with {} and {}".format(video, abr, exp.segue_scheme.nickname))

                    data_point[REBUF_MEAN_CSV] = self.nm(exp, normalization_experiment,METRICS[0], mean=True)
                    data_point[REBUF_1_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[0],perc=1)
                    data_point[REBUF_25_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[0],perc=25)
                    data_point[REBUF_MEDIAN_CSV] = self.nm(exp, normalization_experiment,METRICS[0],perc=50)
                    data_point[REBUF_75_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[0],perc=75)
                    data_point[REBUF_99_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[0],perc=99)

                    
                    data_point[VMAF_MEAN_CSV] = self.nm(exp, normalization_experiment,METRICS[1],mean=True, norm=n_vmaf)
                    data_point[VMAF_1_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[1],perc=5,norm=n_vmaf) ##
                    data_point[VMAF_25_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[1],perc=25,norm=n_vmaf)
                    data_point[VMAF_MEDIAN_CSV] = self.nm(exp, normalization_experiment,METRICS[1],perc=50,norm=n_vmaf)
                    data_point[VMAF_75_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[1],perc=75,norm=n_vmaf)
                    data_point[VMAF_99_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[1],perc=99,norm=n_vmaf)
                    
                    data_point[VMAF_SWITCHES_MEAN_CSV] = self.nm(exp, normalization_experiment,METRICS[2],mean=True,norm=n_vmaf)
                    data_point[VMAF_SWITCHES_1_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[2],perc=1,norm=n_vmaf)
                    data_point[VMAF_SWITCHES_25_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[2],perc=25,norm=n_vmaf)
                    data_point[VMAF_SWITCHES_MEDIAN_CSV] = self.nm(exp, normalization_experiment,METRICS[2],perc=50,norm=n_vmaf)
                    data_point[VMAF_SWITCHES_75_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[2],perc=75,norm=n_vmaf)
                    data_point[VMAF_SWITCHES_99_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[2],perc=95,norm=n_vmaf) ###

                    data_point[REBUF_NO_STARTUP_MEAN_CSV] = self.nm(exp, normalization_experiment,METRICS[0], mean=True, enable_first=False)
                    data_point[REBUF_NO_STARTUP_1_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[0],perc=1,  enable_first=False)
                    data_point[REBUF_NO_STARTUP_25_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[0],perc=25, enable_first=False)
                    data_point[REBUF_NO_STARTUP_MEDIAN_CSV] = self.nm(exp, normalization_experiment,METRICS[0],perc=50, enable_first=False)
                    data_point[REBUF_NO_STARTUP_75_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[0],perc=75, enable_first=False)
                    data_point[REBUF_NO_STARTUP_99_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[0],perc=99, enable_first=False)
                   
                    data_point[REBUF_RATIO_MEAN_CSV] = self.nm(exp, normalization_experiment,METRICS[3],mean=True)
                    data_point[REBUF_RATIO_1_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[3],perc=1)
                    data_point[REBUF_RATIO_25_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[3],perc=25)
                    data_point[REBUF_RATIO_MEDIAN_CSV] = self.nm(exp, normalization_experiment,METRICS[3],perc=50)
                    data_point[REBUF_RATIO_75_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[3],perc=75)
                    data_point[REBUF_RATIO_99_PERC_CSV] = self.nm(exp, normalization_experiment,METRICS[3],perc=95) ###
                    
                    dur = sum(exp.load_segments_durations())
                    nqoe = dur * 25
                    data_point[QOE_MEAN_CSV] = self.nq(exp, normalization_experiment, n_qoe_experiment, mean=True)/nqoe
                    data_point[QOE_1_PERC_CSV] = self.nq(exp, normalization_experiment, n_qoe_experiment, perc=5)/nqoe ###
                    data_point[QOE_25_PERC_CSV] = self.nq(exp, normalization_experiment, n_qoe_experiment, perc=25)/nqoe
                    data_point[QOE_MEDIAN_CSV] = self.nq(exp, normalization_experiment, n_qoe_experiment, perc=50)/nqoe
                    data_point[QOE_75_PERC_CSV] = self.nq(exp, normalization_experiment, n_qoe_experiment, perc=75)/nqoe
                    data_point[QOE_99_PERC_CSV] = self.nq(exp, normalization_experiment, n_qoe_experiment, perc=99)/nqoe
                    
                    
                    # array, one element per trace in the trace set, not normalized (intrinsecally normalized by the definition of rebuffer ratio)
                    data_point[REBUFFER_RATIO_DISTRIBUTION] = exp.metric(METRICS[3])

                    # array, one element per trace in the trace set, we want the difference between the constant length anf the current
                    data_point[REBUFFER_RATIO_DIFF_DISTRIBUTION] = exp.compare_metric(METRICS[3], normalization_experiment)
                    
                    # array, one element per trace in the trace set, not normalized. It is already normalized by the unit time
                    data_point[VMAF_DISTRIBUTION] = exp.metric(METRICS[1])
                   
                    # array, one element per trace in the trace set, we want the difference between the constant length anf the current
                    data_point[VMAF_DIFF_DISTRIBUTION] = exp.compare_metric(METRICS[1], normalization_experiment)

                    data_point[VMAF_SWITCHES_DISTRIBUTION] = exp.metric(METRICS[2])
                    data_point[VMAF_SWITCHES_DIFF_DISTRIBUTION] = exp.compare_metric(METRICS[2], normalization_experiment)
                    

                    data_point[QOE_DISTRIBUTION] = [ x/dur for x in exp.load_rewards() ]
                    data_point[QOE_DIFF_DISTRIBUTION] = [ x/dur for x in exp.compare_reward(normalization_experiment) ]

 
                    d.append(data_point)
                datas[(video, abr)] = pd.DataFrame(d) 
        return datas

    def get_metrics_video_abr(self, n_set):

        datas = {}
        for video, abrs_experiments in self.sets.items():
            for abr, experiments in abrs_experiments.items():
                d = []
                normalization_experiment = n_set[video][abr]
                for exp in experiments: 
                    
                    data_point = {}
                    data_point[VIDEO_NAME_CSV] = video
                    data_point[ABR_NAME_CSV] = abr
                    data_point[SCHEME_GROUPER_CSV] = exp.segue_scheme.grouper_name
                    data_point[SCHEME_AUGMENTER_CSV] = exp.segue_scheme.augmenter_name
                    data_point[SCHEME_LABEL] = exp.segue_scheme.nickname
                    

                    data_point[REBUF_MEAN_CSV] = exp.mean_metric(METRICS[0], normalized_by=normalization_experiment)
                    data_point[REBUF_1_PERC_CSV] = exp.perc_metric(METRICS[0], 1, normalized_by=normalization_experiment)
                    data_point[REBUF_25_PERC_CSV] = exp.perc_metric(METRICS[0], 25,normalized_by=normalization_experiment)
                    data_point[REBUF_MEDIAN_CSV] = exp.perc_metric(METRICS[0], 50,normalized_by=normalization_experiment)
                    data_point[REBUF_75_PERC_CSV] = exp.perc_metric(METRICS[0], 75,normalized_by=normalization_experiment)
                    data_point[REBUF_99_PERC_CSV] = exp.perc_metric(METRICS[0], 99,normalized_by=normalization_experiment)

                    
                    data_point[VMAF_MEAN_CSV] = exp.mean_metric(METRICS[1],normalized_by=normalization_experiment)
                    data_point[VMAF_1_PERC_CSV] = exp.perc_metric(METRICS[1], 1,normalized_by=normalization_experiment)
                    data_point[VMAF_25_PERC_CSV] = exp.perc_metric(METRICS[1], 25,normalized_by=normalization_experiment)
                    data_point[VMAF_MEDIAN_CSV] = exp.perc_metric(METRICS[1], 50,normalized_by=normalization_experiment)
                    data_point[VMAF_75_PERC_CSV] = exp.perc_metric(METRICS[1], 75,normalized_by=normalization_experiment)
                    data_point[VMAF_99_PERC_CSV] = exp.perc_metric(METRICS[1], 99,normalized_by=normalization_experiment)
                    
                    data_point[VMAF_SWITCHES_MEAN_CSV] = exp.mean_metric(METRICS[2],normalized_by=normalization_experiment)
                    data_point[VMAF_SWITCHES_1_PERC_CSV] = exp.perc_metric(METRICS[2], 1,normalized_by=normalization_experiment)
                    data_point[VMAF_SWITCHES_25_PERC_CSV] = exp.perc_metric(METRICS[2], 25,normalized_by=normalization_experiment)
                    data_point[VMAF_SWITCHES_MEDIAN_CSV] = exp.perc_metric(METRICS[2], 50,normalized_by=normalization_experiment)
                    data_point[VMAF_SWITCHES_75_PERC_CSV] = exp.perc_metric(METRICS[2], 75,normalized_by=normalization_experiment)
                    data_point[VMAF_SWITCHES_99_PERC_CSV] = exp.perc_metric(METRICS[2], 99,normalized_by=normalization_experiment)

                    data_point[REBUF_NO_STARTUP_MEAN_CSV] = exp.mean_metric(METRICS[0], enable_first=False,normalized_by=normalization_experiment)
                    data_point[REBUF_NO_STARTUP_1_PERC_CSV] = exp.perc_metric(METRICS[0], 1,  enable_first=False,normalized_by=normalization_experiment)
                    data_point[REBUF_NO_STARTUP_25_PERC_CSV] = exp.perc_metric(METRICS[0], 25, enable_first=False,normalized_by=normalization_experiment )
                    data_point[REBUF_NO_STARTUP_MEDIAN_CSV] = exp.perc_metric(METRICS[0], 50, enable_first=False,normalized_by=normalization_experiment )
                    data_point[REBUF_NO_STARTUP_75_PERC_CSV] = exp.perc_metric(METRICS[0], 75, enable_first=False,normalized_by=normalization_experiment )
                    data_point[REBUF_NO_STARTUP_99_PERC_CSV] = exp.perc_metric(METRICS[0], 99, enable_first=False,normalized_by=normalization_experiment )
                   
                    data_point[REBUF_RATIO_MEAN_CSV] = exp.mean_metric(METRICS[3], normalized_by=normalization_experiment)
                    data_point[REBUF_RATIO_1_PERC_CSV] = exp.perc_metric(METRICS[3], 1, normalized_by=normalization_experiment)
                    data_point[REBUF_RATIO_25_PERC_CSV] = exp.perc_metric(METRICS[3], 25, normalized_by=normalization_experiment )
                    data_point[REBUF_RATIO_MEDIAN_CSV] = exp.perc_metric(METRICS[3], 50, normalized_by=normalization_experiment )
                    data_point[REBUF_RATIO_75_PERC_CSV] = exp.perc_metric(METRICS[3], 75, normalized_by=normalization_experiment )
                    data_point[REBUF_RATIO_99_PERC_CSV] = exp.perc_metric(METRICS[3], 99, normalized_by=normalization_experiment )
                    

                    d.append(data_point)
                datas[(video, abr)] = pd.DataFrame(d) 
        return datas
