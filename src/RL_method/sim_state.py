import logging
from itertools import product
import src.simulator.fixed_env as env
from multiprocessing import Pool
import multiprocessing
import traceback, importlib, glob
import src.simulator.load_trace as load_trace
import numpy as np
import sys
from src.utils.logging.logging_segue import create_logger
RESULTS_DUMP = ["TIME", "SEGMENT_PROGRESSIVE", "DURATION", "BYTES", "QUALITY_INDEX", "RESOLUTION", "BITRATE", "VMAF", "REBUF", "BUFFER_STATE", "DELAY", "REWARD"]
DEFAULT_QUALITY = 1
NORMALIZATION_FACTOR = 4.0

cpu_count = multiprocessing.cpu_count()

def createSimStateSet(abr_module_str, qoe_module_str, qoe_module_class, qoe_module_args, traces_folder, fps):
    logger = logging.getLogger("ABRController.SimState")
    #logger.setLevel(logging.DEBUG)

    try:
        logger.info("Loading ABR module {}".format(abr_module_str))
        abr_module = importlib.machinery.SourceFileLoader('abr', abr_module_str).load_module()
        
        logger.info("Loading QOE module {}".format(qoe_module_str))
        qoe_module_str = qoe_module_str.replace('/', '.').replace('.py', '')
        QoEModule = getattr(importlib.import_module(qoe_module_str), qoe_module_class)
        qoe_module = QoEModule(logger, fps, qoe_module_args)
    except:
        logger.error("Error while loading dynamic modules. Exiting...")
        logger.error(traceback.format_exc())
        sys.exit(-1)
    traces = [load_trace.load_trace(tf) for tf in glob.glob(traces_folder +"/*")]


    return SimStateSet(abr_module, qoe_module, traces), qoe_module, abr_module

def mp_step_helper(ss, args):
    VIDEO_PROPERTIES, fr, to = args
    while not ss.is_done():
        ss.step(VIDEO_PROPERTIES)
    
    r = 0
    if fr != -1 and to != -1:
        r = ss.evaluate_reward(VIDEO_PROPERTIES, fr, to)
    return ss, r

def mp_step_n_helper(ss, arg):
    VIDEO_PROPERTIES, n, fr, to = arg

    for x in range(n):
        if not ss.is_done():
            ss.step(VIDEO_PROPERTIES)
    r = 0
    if fr != -1 and to != -1:
        r = ss.evaluate_reward(VIDEO_PROPERTIES, fr, to)
    return ss, r

class SimStateSet():
    def __init__(self, abr_module, qoe_module, traces):
        self.abr_module = abr_module
        self.qoe_module = qoe_module
        self.traces = traces

        self.ss_set = []
        for i, trace in enumerate(traces):
            abr = abr_module.Abr(qoe_module)
            self.ss_set.append(
                SimState(abr, qoe_module, env.Environment(trace), i))

    def copy(self):
        cop = SimStateSet(self.abr_module, self.qoe_module, [])
        cop.ss_set = [x.copy() for x in self.ss_set]
        return cop

    def step(self, VIDEO_PROPERTIES):
        for ss in self.ss_set:
            ss.step(VIDEO_PROPERTIES) 

    def step_till_end(self, VIDEO_PROPERTIES, fr, to, use_pool = True):
        tasks = product(self.ss_set, [(VIDEO_PROPERTIES, fr, to)])
        if use_pool:
            with Pool(cpu_count) as pool: ## That shouldn't be fixed
                ret = pool.starmap(mp_step_helper, tasks)
                self.ss_set = [ x[0] for x in ret ]
                rewards = [x[1] for x in ret]
        else:
            ret = [mp_step_helper(a, (b,c,d)) for (a, (b, c, d)) in tasks]
            self.ss_set = [ x[0] for x in ret ]
            rewards = [x[1] for x in ret]
        return self.qoe_module.aggregate_rewards(rewards)

    def step_n(self, VIDEO_PROPERTIES, n, fr, to, use_pool = True):
        """
        Step n times for each SimState in the set
        VIDEO_PROPERTIES: the segment list which obtained from MultileveVideo class function get_simuation_data() 
        which will call multilevel_segment class function get_simuation_data() like following:
        {"0":{"chunk_progressive":0,"n_levels":2,"levels":[
            {resolution:"640x360, "bitrate":529, "vmaf":94, "bytes":330668,"duration":2.0,"is_augment":False,"vmaf_per_frame":[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] }
            ,resolution:"854x380, "bitrate":529, "vmaf":94, "bytes":330668,"duration":2.0,"is_augment":False, "vmaf_per_frame":[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] } 
                                                          ]
             },
         "1":{"chunk_progressive":1,"n_levels":2,"levels":[
            {resolution:"640x360, "bitrate":529, "vmaf":94, "bytes":330668,"duration":2.0,"is_augment":False,"vmaf_per_frame":[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] }
            ,resolution:"854x380, "bitrate":529, "vmaf":94, "bytes":330668,"duration":2.0,"is_augment":False, "vmaf_per_frame":[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] }
                                                            ]
             },....
        }
        """
        if use_pool :
            tasks = product(self.ss_set, [(VIDEO_PROPERTIES, n, fr, to)])
            with Pool(cpu_count) as pool: ## That shouldn't be fixed
                ret = pool.starmap(mp_step_n_helper, tasks)
                self.ss_set = [ x[0] for x in ret ]
                rewards = [x[1] for x in ret]
        
        else:
            tasks = product(self.ss_set, [(VIDEO_PROPERTIES, n, fr, to)])
            ret = [mp_step_n_helper(a,(b,n, fr, to)) for (a, (b, fr, to)) in tasks]
            self.ss_set = [ x[0] for x in ret ]
            rewards = [x[1] for x in ret]
        return self.qoe_module.aggregate_rewards(rewards)

    def reward(self):
        return np.mean([ss.history[-1]['reward'] for ss in self.ss_set])

    def is_done(self):
        return self.ss_set[0].is_done()

    def get_chunk_index(self):
        return self.ss_set[0].chunk_index

    def debug_print(self):
        res = ""
        for x in self.ss_set:
            res += x.debug_print()
        return res

class SimState():
    """ Essentially a network environment + abr + qoe, keeps track of the history
    of steps """
    '''Video properties is a list of dictionaries, which is created by function load_video_properties in src/simulator/abr_controller.py 
    each dictionary is a segment which contains the following keys:
    duration: duration of the segment in seconds
    '''
    def __init__(self, abr, qoe, net, trace_idx):
        self.logger = logging.getLogger("ABRController.SimState")
        self.net = net
        self.qoe = qoe
        self.abr = abr
        self.chunk_index = 0
        self.trace_idx = trace_idx

        self.history = []
        self.video_done = False
    def is_done(self):
        return self.video_done

    def copy(self):
        cop = SimState(self.abr.copy(), self.qoe.copy(), self.net.copy(), self.trace_idx)
        cop.chunk_index = self.chunk_index
        cop.video_done = self.video_done
        cop.history = list(self.history)
        return cop
    
    
    def evaluate_reward(self, VIDEO_PROPERTIES, fr, to):
        assert to <= self.chunk_index + 1
        hist = self.history[fr:to]
        downloaded_sequence = [x['level'] for x in hist]
        rebuffering_time = [x['rebuf'] for x in hist]
        downloaded_vmaf_sequence = []

        for i, x in enumerate(downloaded_sequence):
            downloaded_vmaf_sequence += VIDEO_PROPERTIES[fr + i]["levels"][x]["vmaf_per_frame"]
        return self.qoe.evaluate_reward_per_unit_time([downloaded_vmaf_sequence, rebuffering_time])

    def step(self, VIDEO_PROPERTIES):
        """        VIDEO_PROPERTIES = {"0":{"chunk_progressive":0,"n_levels":2,"levels":[
            {resolution:"640x360, "bitrate":529, "vmaf":94, "bytes":330668,"duration":2.0,"is_augment":False,"vmaf_per_frame":[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] }
            ,resolution:"854x380, "bitrate":529, "vmaf":94, "bytes":330668,"duration":2.0,"is_augment":False, "vmaf_per_frame":[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] } 
                                                          ]
             },
         "1":{"chunk_progressive":1,"n_levels":2,"levels":[
            {resolution:"640x360, "bitrate":529, "vmaf":94, "bytes":330668,"duration":2.0,"is_augment":False,"vmaf_per_frame":[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] }
            ,resolution:"854x380, "bitrate":529, "vmaf":94, "bytes":330668,"duration":2.0,"is_augment":False, "vmaf_per_frame":[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] }
                                                            ]
             },....
        }"""
        # Check we don't exhaust video
        if self.chunk_index >= len(VIDEO_PROPERTIES):
            self.video_done = True
            return

        # ABR, determine the level
        if self.chunk_index == 0:
            level = DEFAULT_QUALITY
        else:
            level = self.abr.abr(self, VIDEO_PROPERTIES, self.chunk_index) 

    
        def level_obj(idx):
            if idx is None: return None
            return VIDEO_PROPERTIES[self.chunk_index]["levels"][idx]

        lo = level_obj(level)
        prev_lo = None
        if self.history != []:
            prev_lo = VIDEO_PROPERTIES[self.chunk_index-1]["levels"][self.history[-1]['level']]

        # Fetch chunk
        duration = VIDEO_PROPERTIES[self.chunk_index]['duration']
        size = VIDEO_PROPERTIES[self.chunk_index]['levels'][level]['bytes']
        #self.logger.debug("step: Fetch segment {} at level {} => {} s, {} bytes"
        #       .format(self.chunk_index, level, duration, size))
        data = self.net.fetch_chunk(size, duration)


        #if self.chunk_index > 0 and data['rebuf'] > 0 and duration > 10:
        #    print("=== NETENV({}): rebuf={} at {}".format(self.trace_idx, data['rebuf'], self.chunk_index))


        # Add some random data
        data['level'] = level


        data['time'] = data['delay'] + data['sleep_time']
        if self.history != []:
            data['time'] += self.history[-1]['time']

        data['duration'] = duration
        data['bytes'] = size
        data['resolution'] = lo['resolution']
        data['bitrate'] = lo['bitrate']
        data["vmaf"] = lo["vmaf"]*(duration/NORMALIZATION_FACTOR)
        
        # QOE 
        data['reward'] = self.qoe.evaluate_reward_per_segment([
            lo,
            prev_lo,
            VIDEO_PROPERTIES[self.chunk_index], data['rebuf']] )

        #self.logger.debug("step: delay={}  sleep={}".format(data['delay'], data['sleep_time']))

       
        self.history.append(data)
        
        # Determine next chunk level
        self.chunk_index += 1

    def log_dict(self, idx):
        res = {key.upper(): val for key,val in self.history[idx].items()}
        res['SEGMENT_PROGRESSIVE'] = idx
        res['QUALITY_INDEX'] = res['LEVEL']
        res['BUFFER_STATE'] = res['BUFFER_SIZE']
        res2 = {k:res[k] for k in RESULTS_DUMP}
        return res2

    def debug_print(self):
        dd = dict(self.__dict__)
        s = "SS{} => {}, ".format(id(self), dd)
        s += self.net.debug_print()
        s += self.abr.debug_print()
        return s
        irint(self.chunk_index)
