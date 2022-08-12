from src.utils.video_factory import Video, FullVideo, EXTENSION
import json, argparse, os, sys, importlib, traceback
from src.utils.logging.logging_segue import create_logger
from src.consts.reward_consts import *
from src.consts.postprocessing_consts import *
from src.consts.video_configs_consts import *
from src.consts.grouper_configs_consts import *
from src.consts.augmenter_consts import *
from src.postprocesser.postprocesser import PostProcesser
import pandas as pd
def jload(f):
    with open(f, 'r') as fin:
        data = json.load(fin)
    return data


def pmkdir(kdir):
    if not os.path.exists(kdir):
        os.makedirs(kdir)

def empty(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print("Error in empyting log folder")
            sys.exit(-1)



def create_postprocessing(experiments_tuples, args, logger):
    postprocesser_traces_seen = PostProcesser(experiments_tuples, args.traces_seen, logger)
    return postprocesser_traces_seen


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiments_list", action="append", nargs=8, metavar=('video_config', 'abr_config', 'grouper_config', 'augmenter_config', 'nickname', 'simulation_file', 'experiments_dir', 'cache_dir'), help='List of the manifests to analyze', required=True)
    parser.add_argument("--reward_configs", type=str, required=True)
    parser.add_argument("--out_csv_dir", type=str, required=True)
    parser.add_argument("--traces_seen", type=str, required=True)
    parser.add_argument("--logs_dir", type=str)
    parser.add_argument("--figs_dir", type=str, required=True)
    parser.add_argument("--verbose", action="store_true")
    
    #### Plot options ####
    

    args = parser.parse_args()
    if os.path.exists(args.logs_dir):
            empty(args.logs_dir)
        
    pmkdir(args.logs_dir)
    log_file = os.path.join(args.logs_dir, 'make_postprocessing.log')
    logger = create_logger('Postprocessing', log_file, verbose=args.verbose)
    logger.info("Postprocessing: start")
    logger.info("Logs file stored in {}".format(log_file))
 
    try:
            logger.info("loading reward data from module {}".format(args.reward_configs))
            reward_data = jload(args.reward_configs)
            reward_module = reward_data[REWARD_MODULE].replace('/', '.').replace('.py', '')
            reward_class = reward_data[REWARD_CLASS]            
            RewardClass = getattr(importlib.import_module(reward_module), reward_class)
    except:
            logger.info("Error while loading the reward module")
            traceback.print_exc()
            sys.exit(-1)
    
    reward_args = reward_data[REWARD_PARAMETERS]
    
    experiments_tuples = {}
    

    for exp in args.experiments_list:
        video_data = jload(exp[0])
        video_name = video_data[K_NAME_VIDEO]
        
        if video_name not in experiments_tuples.keys():
            experiments_tuples[video_name] = []


        abr_data = jload(exp[1])
        abr_name = abr_data["name"]

        grouper_data = jload(exp[2])
        grouper_name = grouper_data[K_NAME_GROUPER]

        augmenter_data = jload(exp[3])
        augmenter_name = augmenter_data[K_NAME_AUGMENTER]
        
        
        video_path = video_data[K_VIDEO_PATH]
        fps = Video(video_path, args.logs_dir).load_fps()
        reward_module = RewardClass(logger, fps, reward_args)
        if not os.path.exists(exp[6]):
            print("{} does not exists".format(exp[6]))
            continue
        pmkdir(exp[7])
        
        logger.debug("Loading experiment: Video => {}, abr name => {}, grouper_name => {},\
                        augmenter_name => {}, nickname => {}, simulation file => {},\
                        results dir => {}, caches dir => {}".format(video_name, abr_name, grouper_name,
                                                                    augmenter_name, exp[4], exp[5], exp[6], exp[7]))


        t = (video_name, abr_name, grouper_name, augmenter_name, exp[4], exp[5], exp[6], reward_module, exp[7])
        already_in = False

        # does it really happen?
        for t2 in experiments_tuples[video_name]:
            if t2[4] == t[4] and t[1] == t2[1]:
                already_in = True
                break
        if already_in:
            continue
        experiments_tuples[video_name].append(t)
    
    logger.info("Loading processer with traces seen => {}".format(args.traces_seen))
    pmkdir(args.out_csv_dir)
    
    csv_distribution_list = {}

    for video, t in experiments_tuples.items():
        print("Analyzing video {}".format(video))       
        p_plot = create_postprocessing(  experiments_tuples[video], args, logger)
        metrics = p_plot.get_distributions()

        for (video, abr), csv in metrics.items():
            for i, row in csv.iterrows():
                label = row['label']
                
                if label not in csv_distribution_list.keys():
                    csv_distribution_list[label] = []
                
                distr = {}

                distr['video'] = video
                distr['abr'] = abr

                
                distr[REBUFFER_RATIO_DISTRIBUTION] = row[REBUFFER_RATIO_DISTRIBUTION]
                distr[VMAF_DISTRIBUTION] = row[VMAF_DISTRIBUTION]
                distr[VMAF_SWITCHES_DISTRIBUTION] = row[VMAF_SWITCHES_DISTRIBUTION]
                distr[QOE_DISTRIBUTION] = row[QOE_DISTRIBUTION]
                distr[STARTUP_DISTRIBUTION] = row[STARTUP_DISTRIBUTION]
                
                csv_distribution_list[label].append(distr)
    
    for label, df in csv_distribution_list.items():
        out2 = "{}/{}_distr.csv".format(args.out_csv_dir, label)
        df2_out = pd.DataFrame(csv_distribution_list[label])
        df2_out.to_csv(out2)
