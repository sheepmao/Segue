
# Data structure per chunk:
# chunk_progressive - chunk_duration (time) - number of layers available - list of availability:
# per available, ordered by bitrate [ chunk size byte, chunk bitrate (kbit/s), vmaf score, resolution ]
import os, ntpath, copy, glob, pickle
import numpy as np
import src.simulator.fixed_env as env
import src.simulator.load_trace as load_trace
from src.simulator.sim_state import SimState, SimStateSet, createSimStateSet, RESULTS_DUMP
import argparse, time
import logging
import json
import itertools
import importlib.machinery
import pandas as pd
import sys
import traceback
from pathlib import Path
from src.consts.reward_consts import *
from src.consts.simulation_file_consts import *
from src.utils.logging.logging_segue import create_logger
RANDOM_SEED = 42



def ss_test(ss, VIDEO_PROPERTIES):
    """ play a bit around with the copy function """
    cop = ss.copy()
    VP2 = copy.deepcopy(VIDEO_PROPERTIES)
    for x in VP2:
        x['duration'] -= 1
    cop.step(VP2)


def load_video_properties(VIDEO_PROPERTIES_FILE):
    with open(VIDEO_PROPERTIES_FILE, "r") as fin:
        data = json.load(fin)
    ss = {}
    for idx in range(len(data.keys())):
        ss[idx] = data[str(idx)]
    return ss

def main(LOG_DIR, RESULT_DIR, VIDEO_FILE, TRACE_FILE, ABR_MODULE, QOE_CONFIGS):
    

    def enable_log(logname):
        logger = logging.getLogger(logname)
        logger.setLevel(logging.INFO)
        LOG_FILE = os.path.join(LOG_DIR, '{}.log'.format(ntpath.basename(TRACE_FILE)))
        # create file handler which logs even debug messages
        fh = logging.FileHandler(LOG_FILE)
        fh.setLevel(logging.INFO)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)
    
    enable_log("ABRController")
    enable_log("SimState")
    enable_log("ABR")
    log_file = os.path.join(LOG_DIR, '{}.log'.format(ntpath.basename(TRACE_FILE).replace('.txt', '')))
    #logger = create_logger('ABRController', log_file, verbose=True)
    logger = logging.getLogger("ABRController")
    logger.info("Starting ABR Controller")
    logger.info("Log file is stored in {}".format(log_file))
    #logger = logging.getLogger("ABR Controller")
    

    VIDEO_PROPERTIES = load_video_properties(VIDEO_FILE)
    logger.info("Video properties loaded")
    
    fps = round(len(VIDEO_PROPERTIES[0][SIM_FILE_LEVELS][0][SIM_FILE_VMAF_PER_FRAME])/VIDEO_PROPERTIES[0][SIM_FILE_DURATION])
    with open(QOE_CONFIGS, 'r') as fin:
        qoe_data = json.load(fin)

    qoe_module = qoe_data[REWARD_MODULE]
    assert os.path.exists(qoe_module)
    qoe_class_name = qoe_data[REWARD_CLASS]

    logger.info("Qoe module = {}, Class name = {}".format(qoe_module, qoe_class_name))

    try:
        qoe_parameters = qoe_data[REWARD_PARAMETERS]
        logger.info("Reward parameters are {}".format(qoe_parameters))
    except:
        print("no param")
        qoe_parameters = {}

    
    np.random.seed(RANDOM_SEED)
    logger.info("Initializing...")

    try:
        logger.info("Loading ABR module {}".format(ABR_MODULE))
        abr_module = importlib.machinery.SourceFileLoader('abr', ABR_MODULE).load_module()
        logger.info("Loading QOE module {}".format(qoe_module))
        qoe_module_str = qoe_module.replace('/', '.').replace('.py', '')
        QoEModule = getattr(importlib.import_module(qoe_module_str), qoe_class_name)
        qoe_module = QoEModule(logger, fps, qoe_parameters)
    
    except:
        logger.error("Error while loading dynamic modules. Exiting...")
        logger.error(traceback.format_exc())
        sys.exit(-1)
    

    #ss_set = SimStateSet(abr_module, qoe_module,
    #        [load_trace.load_trace(x) for x in glob.glob("TRACES/TRACES_NORWAY/*")])
    ss_set = SimStateSet(abr_module, qoe_module,
            [load_trace.load_trace(TRACE_FILE)])
    
    start_segment = 0
    end_segment = len(VIDEO_PROPERTIES)
    ss_set.step_till_end(VIDEO_PROPERTIES,start_segment, end_segment, use_pool=False)
    ss = ss_set.ss_set[0]


    #Write results
    result_path = "{}.csv".format(os.path.join(RESULT_DIR, ntpath.basename(TRACE_FILE)))
    logger.info("Dumping results in {}".format(result_path))
    DATAFRAME = pd.DataFrame(columns=RESULTS_DUMP)
    for idx in range(len(VIDEO_PROPERTIES)): 
        DATAFRAME = DATAFRAME.append(ss.log_dict(idx), ignore_index=True)
    DATAFRAME.to_csv(result_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_result_dir",
            help="DIRECTORY IN WHICH THE RESULTS WILL BE STORED", type=str,required=True)
    parser.add_argument("--out_log_dir", help="LOG FILE", type=str,required=True)
    parser.add_argument("--in_video_properties",
            help="JSON FILE WITH THE SEGMENT SIMULATION", type=str,required=True)
    parser.add_argument("--abr_module", help="abr module link", type=str, required=True)
    parser.add_argument("--qoe_configs", help="qoe module link", type=str, required=True)
    parser.add_argument("--in_trace_file", help="Trace to run", type=str, required=True)

    args = parser.parse_args()
    
    assert os.path.exists(args.abr_module) and os.path.exists(args.qoe_configs),\
        "ABR and QOE module must exist!"

  
    Path(args.out_result_dir).mkdir(parents=True, exist_ok=True)
    Path(args.out_log_dir).mkdir(parents=True, exist_ok=True)
    

    main(args.out_log_dir, args.out_result_dir, args.in_video_properties,
         args.in_trace_file, args.abr_module, args.qoe_configs)
