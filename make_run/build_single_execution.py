# This script generates the Makefiles necessary for a single
# Segue execution


import os
import argparse
from glob import glob 
import pandas as pd
import tempfile
import shutil
from os.path import join
import json

## STATIC PATHS
from make_run.LOC import *

def jload(f):
    with open(f, 'r') as fin:
        data = json.load(fin)
    return data


def remove_and_create(out_dir='run'):
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)


def parse_video_args(video):
    assert video in VIDEO_LOC.keys()
    video_json = VIDEO_LOC[video]
    assert os.path.exists(video_json)
    video_data = jload(video_json)
    assert os.path.exists(video_data['video_path'])
    return video_data['name'], video_json

def parse_grouper_args(grouper):
    assert grouper in GROUPER_LOC.keys()
    grouper_json = GROUPER_LOC[grouper]
    assert os.path.exists(grouper_json)
    grouper_name = os.path.basename(grouper_json).split('.')[0]
    return grouper_name, grouper_json

def parse_augmenter_args(augmenter):
    assert augmenter in AUGMENTER_LOC.keys()
    augmenter_json = AUGMENTER_LOC[augmenter]
    assert os.path.exists(augmenter_json)
    augmenter_data = jload(augmenter_json)
    return augmenter_data['name'], augmenter_json

def parse_sim_file_args(simfile):
    assert simfile in SIM_FILE_LOC.keys()
    simfile_json = SIM_FILE_LOC[simfile]
    assert os.path.exists(simfile_json)
    simfile_data = jload(simfile_json)
    return simfile_data['name'], simfile_json



def parse_simulator_args(sim):
    sim =  sim + '-SIM'
    assert sim in ABR_SIM_LOC.keys()
    sim_json = ABR_SIM_LOC[sim]
    assert os.path.exists(sim_json)
    sim_data = jload(sim_json)
    assert os.path.exists(sim_data["simulation_traces_path"])
    assert os.path.exists(sim_data["simulation_abr_module"])
    assert os.path.exists(sim_data["simulation_reward_configs"])

    return  sim_data['name'],\
            sim_data["simulation_traces_path"],\
            sim_data["simulation_abr_module"],\
            sim_data["simulation_reward_configs"],\
            sim_json




if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache_dir", default='make_run/caches_single_exec')
    parser.add_argument("--template", default='make_run/MAKEFILE_TEMPLATES/Template')
    parser.add_argument("--template_post", default='make_run/MAKEFILE_TEMPLATES/TemplatePOST')
    parser.add_argument("--video", required='True', help='VIDEO IDs KEYS: see loc.py')
    parser.add_argument("--abr", required='True', help='BB | RB | RMPC-A | RMPC-O')
    parser.add_argument("--traces", required='True', help='TRACES ID KEYS: see loc.py')
    parser.add_argument("--vmaf", required='True', help='VMAF MODEL ID KEYS: [MOBILE, HDTV, 4K]')
    parser.add_argument("--grouper", required='True', help='K-{1..5} | GOP-{1..5} | TIME | BYTES | TIME+BYTES | SIM | WIDE-EYE')
    parser.add_argument("--augmenter", required='True', help='NONE | SIGMA-BV | CBF-{40,60,80} | SIVQ-{5,10,15} | LAMBDA-B | LAMBDA-V | LAMBDA-BV-{5,10,15}-{5..14}')
    parser.add_argument("--fname", required='True', help='File name of the generated Make')
    parser.add_argument("--results_dir", default='results')
    parser.add_argument("--post_out", required=True)

    args = parser.parse_args()
    remove_and_create(args.cache_dir)
   


    with open(args.template, 'r') as fin:
        template_lines = fin.readlines()
 
    
    
    new_lines = []
    
    if args.grouper == 'SIM' or args.grouper == 'WIDE-EYE':
        args.grouper = args.abr + '-' + args.grouper

    if args.augmenter == 'SIGMA-BV':
        args.augmenter = args.abr + '-' + args.augmenter



    TYP = 'REAL'
    VIDEO_NAME, VIDEO_CONFIG = parse_video_args(args.video)
    GROUPER_NAME, GROUPER_CONFIG = parse_grouper_args(args.grouper)
    AUGMENTER_NAME, AUGMENTER_CONFIG = parse_augmenter_args(args.augmenter)
    SIM_FILE_NAME, SIM_FILE_CONFIG = parse_sim_file_args(args.vmaf)
    SIM_NAME, SIM_TRACES, SIM_ABR, SIM_REWARD, SIM_CONFIG = parse_simulator_args(args.abr)
    
    
    

    for line in template_lines:
        # GENERAL
        line = line.replace("<<VIDEO_TYPE>>", TYP)
        line = line.replace("<<RESULT_DIR>>", args.results_dir)
        
        #VIDEO RELATED CONFIGS
        line = line.replace("<<VIDEO_CONFIG_FILE>>", VIDEO_CONFIG)
        line = line.replace("<<VIDEO_NAME>>", VIDEO_NAME)


        #GROUPER RELATED CONFIGS
        line = line.replace("<<GROUPING_POLICY_FOLDER>>", GROUPER_NAME)
        line = line.replace("<<GROUPING_POLICY_CONFIG_FILE>>", GROUPER_CONFIG)

        #AUGMENTER RELATED CONFIGS
        line = line.replace("<<SEGMENTS_HANDLER_FOLDER>>", AUGMENTER_NAME)
        line = line.replace("<<SEGMENTS_HANDLER_CONFIG_FILE>>", AUGMENTER_CONFIG)
        
       
        #SIM FILE RELATED DATA
        line = line.replace("<<SIM_FILE_CONFIGS>>", SIM_FILE_CONFIG)
        line = line.replace("<<SIM_FILE_DIROUT>>", SIM_FILE_NAME)
        
        #SIM RELATED DATA
        line = line.replace("<<SIMULATION_POLICY_RESULTS_FOLDER>>", SIM_NAME)
        line = line.replace("<<TRACES_PATH>>", SIM_TRACES)
        line = line.replace("<<ABR_MODULE>>", SIM_ABR)
        line = line.replace("<<QOE_CONFIGS>>", SIM_REWARD)
        new_lines.append(line)

    with open(join(args.cache_dir, args.fname), 'w') as fout:
        fout.writelines(new_lines)
    
    
    
    
    SIM_FILE = '{}/{}/{}/files/{}/{}/simulation.json'.format(args.results_dir, VIDEO_NAME, GROUPER_NAME, AUGMENTER_NAME, SIM_FILE_NAME)
    RESULT_DIR = '{}/{}/{}/simulation/{}/{}/{}/results'.format(args.results_dir, VIDEO_NAME, GROUPER_NAME, AUGMENTER_NAME, SIM_FILE_NAME, SIM_NAME)
    CACHE_DIR = '{}/{}/{}/simulation/{}/{}/{}/{}'.format(args.results_dir, VIDEO_NAME, GROUPER_NAME, AUGMENTER_NAME, SIM_FILE_NAME, SIM_NAME, 'caches')

    EXPERIMENT_LIST= '--experiments_list {} {} {} {} {} {} {} {}'.format(   VIDEO_CONFIG,\
                                                                            SIM_CONFIG,\
                                                                            GROUPER_CONFIG,\
                                                                            AUGMENTER_CONFIG,\
                                                                            args.fname,\
                                                                            SIM_FILE,\
                                                                            RESULT_DIR,\
                                                                            CACHE_DIR)
    
    with open(args.template_post, 'r') as fin:
        template_lines = fin.readlines()
 
    new_lines = []

    for line in template_lines:
        line = line.replace("<<OUT_DIR>>", args.post_out)
        line = line.replace("<<DEPENDENCIES>>", '')
        line = line.replace("<<EXPERIMENTS_LIST>>", EXPERIMENT_LIST)
        line = line.replace("<<REWARD_CONFIGS>>", SIM_REWARD)
        line = line.replace("<<TRACES_SEEN>>", TRACES_LOC[args.traces])
        line = line.replace("<<LOGS_DIR>>", os.path.join(args.post_out,'logs'))
        line = line.replace("<<FIGS_DIR>>", os.path.join(args.post_out, 'figs'))
        line = line.replace("<<OUT_CSV>>", os.path.join(args.post_out, 'csv'))
        new_lines.append(line) 

    with open(join(args.cache_dir, args.fname + '_post'), 'w') as fout:
            fout.writelines(new_lines)
