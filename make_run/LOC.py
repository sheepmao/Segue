import os
BASEPATH = 'configs'
def conc(mainf, subf, filename):
    if subf != '':
        return os.path.join(BASEPATH, mainf, subf, '{}.json'.format(filename))
    else:
        return os.path.join(BASEPATH, mainf, '{}.json'.format(filename))






# MAP HERE A VIDEO KEY TO THEIR CONFIGURATION FILE #

VIDEO_LOC = {}
#VIDEO_LOC['TEMPLATE'] = conc('videos', '', 'TEMPLATE')
VIDEO_LOC['BBB'] = conc('videos', '', 'BBB')


# MAP HERE A TRACE SET KEY TO THEIR FOLDER #

TRACES_LOC = {}
#TRACES_LOC['TRACE-ID'] = 'path/to/traceset'
TRACES_LOC['dummy'] = './traces/dummy'
TRACES_LOC['dummy1'] = './traces/dummy1'
TRACES_LOC['oboe_traces'] = './traces/oboe_traces'

SIM_FILE_LOC = {}
SIM_FILE_LOC['MOBILE'] = conc('simulation_file','','simulation_file_vmaf_mobile')
SIM_FILE_LOC['HDTV'] = conc('simulation_file','','simulation_file_vmaf_hdtv')
SIM_FILE_LOC['4K'] = conc('simulation_file','','simulation_file_vmaf_4k')


ABR_SIM_LOC = {}
ABR_SIM_LOC['RB-SIM'] = conc('simulator', 'simulate', 'rb_simulate')
ABR_SIM_LOC['BB-SIM'] =  conc('simulator', 'simulate', 'bb_simulate')
ABR_SIM_LOC['RMPC-A-SIM'] =  conc('simulator', 'simulate', 'rmpc_aware_simulate')
ABR_SIM_LOC['RMPC-O-SIM'] =  conc('simulator', 'simulate', 'rmpc_oblivious_simulate')


GROUPER_LOC = {}
GROUPER_LOC['K-1'] = conc('groupers', 'constant_length', 'grouper_h264_consts_1')
GROUPER_LOC['K-2'] = conc('groupers', 'constant_length', 'grouper_h264_consts_2')
GROUPER_LOC['K-3'] = conc('groupers', 'constant_length', 'grouper_h264_consts_3')
GROUPER_LOC['K-4'] = conc('groupers', 'constant_length', 'grouper_h264_consts_4')
GROUPER_LOC['K-5'] = conc('groupers', 'constant_length', 'grouper_h264_consts_5')
GROUPER_LOC['GOP-1'] = conc('groupers', 'gop', 'grouper_h264_fully_fragmented_1') 
GROUPER_LOC['GOP-2'] = conc('groupers', 'gop', 'grouper_h264_fully_fragmented_2')
GROUPER_LOC['GOP-3'] = conc('groupers', 'gop', 'grouper_h264_fully_fragmented_3')
GROUPER_LOC['GOP-4'] = conc('groupers', 'gop', 'grouper_h264_fully_fragmented_4')
GROUPER_LOC['GOP-5'] = conc('groupers', 'gop', 'grouper_h264_fully_fragmented_5')
GROUPER_LOC['TIME'] = conc('groupers', 'heuristics', 'grouper_h264_time_opt_5')
GROUPER_LOC['BYTES'] =  conc('groupers', 'heuristics', 'grouper_h264_bytes_opt_5')
GROUPER_LOC['TIME+BYTES'] =  conc('groupers', 'heuristics', 'grouper_h264_time_bytes_opt_5')
GROUPER_LOC['BB-SIM'] = conc('groupers', 'bb_optimized', 'grouper_h264_sim_opt_bb_global_vmaf_4k')
GROUPER_LOC['BB-WIDE-EYE'] =  conc('groupers', 'bb_optimized', 'grouper_h264_wide_eye_sim_opt_bb_global_vmaf_4k')
GROUPER_LOC['RB-SIM'] = conc('groupers', 'rb_optimized', 'grouper_h264_sim_opt_rb_global_vmaf_4k') 
GROUPER_LOC['RB-WIDE-EYE'] = conc('groupers', 'rb_optimized', 'grouper_h264_wide_eye_sim_opt_rb_global_vmaf_4k')
GROUPER_LOC['RMPC-A-SIM'] =  conc('groupers', 'rmpc_aware_optimized', 'grouper_h264_sim_opt_rmpc_aware_global_vmaf_4k')
GROUPER_LOC['RMPC-A-WIDE-EYE'] = conc('groupers', 'rmpc_aware_optimized', 'grouper_h264_wide_eye_sim_opt_rmpc_aware_global_vmaf_4k')
GROUPER_LOC['RMPC-O-SIM'] =  conc('groupers', 'rmpc_oblivious_optimized', 'grouper_h264_sim_opt_rmpc_oblivious_global_vmaf_4k')
GROUPER_LOC['RMPC-O-WIDE-EYE'] = conc('groupers', 'rmpc_oblivious_optimized', 'grouper_h264_wide_eye_sim_opt_rmpc_oblivious_global_vmaf_4k')

AUGMENTER_LOC = {}

AUGMENTER_LOC['NONE'] = conc('augmenter', '', 'no_augmentation_h264')
AUGMENTER_LOC['RMPC-O-SIGMA-BV'] = conc('augmenter', 'rmpc_oblivious_optimized', 'sigma_bv_sim_rmpc_oblivious_h264')
AUGMENTER_LOC['RMPC-A-SIGMA-BV'] = conc('augmenter', 'rmpc_aware_optimized', 'sigma_bv_sim_rmpc_aware_h264')
AUGMENTER_LOC['BB-SIGMA-BV'] = conc('augmenter', 'bb_optimized', 'sigma_bv_sim_bb_h264')
AUGMENTER_LOC['RB-SIGMA-BV'] = conc('augmenter', 'rb_optimized', 'sigma_bv_sim_rb_h264')
AUGMENTER_LOC['CBF-40'] = conc('augmenter', 'cbf', 'cbf_h264_40')
AUGMENTER_LOC['CBF-60'] = conc('augmenter', 'cbf', 'cbf_h264_60')
AUGMENTER_LOC['CBF-80'] = conc('augmenter', 'cbf', 'cbf_h264_80')
AUGMENTER_LOC['SIVQ-5'] = conc('augmenter', 'sivq', 'sivq_va_h264_SWEEP_5')
AUGMENTER_LOC['SIVQ-10'] = conc('augmenter', 'sivq', 'sivq_va_h264_SWEEP_10')
AUGMENTER_LOC['SIVQ-15'] = conc('augmenter', 'sivq', 'sivq_va_h264_SWEEP_15')
AUGMENTER_LOC['LAMBDA-B'] = conc('augmenter', 'heuristics', 'lambda_b_h264')
AUGMENTER_LOC['LAMBDA-V'] = conc('augmenter', 'heuristics', 'lambda_v_h264')
AUGMENTER_LOC['LAMBDA-BV-5-5'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_5_5') 
AUGMENTER_LOC['LAMBDA-BV-5-6'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_5_6')
AUGMENTER_LOC['LAMBDA-BV-5-7'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_5_7')
AUGMENTER_LOC['LAMBDA-BV-5-8'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_5_8')
AUGMENTER_LOC['LAMBDA-BV-5-9'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_5_9')
AUGMENTER_LOC['LAMBDA-BV-5-10'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_5_10')
AUGMENTER_LOC['LAMBDA-BV-5-11'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_5_11')
AUGMENTER_LOC['LAMBDA-BV-5-12'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_5_12')
AUGMENTER_LOC['LAMBDA-BV-5-13'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_5_13')
AUGMENTER_LOC['LAMBDA-BV-5-14'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_5_14')
AUGMENTER_LOC['LAMBDA-BV-10-5'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_10_5')
AUGMENTER_LOC['LAMBDA-BV-10-6'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_10_6')
AUGMENTER_LOC['LAMBDA-BV-10-7'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_10_7')
AUGMENTER_LOC['LAMBDA-BV-10-8'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_10_8')
AUGMENTER_LOC['LAMBDA-BV-10-9'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_10_9')
AUGMENTER_LOC['LAMBDA-BV-10-10'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_10_10') 
AUGMENTER_LOC['LAMBDA-BV-10-11'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_10_11')
AUGMENTER_LOC['LAMBDA-BV-10-12'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_10_12')
AUGMENTER_LOC['LAMBDA-BV-10-13'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_10_13')
AUGMENTER_LOC['LAMBDA-BV-10-14'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_10_14')
AUGMENTER_LOC['LAMBDA-BV-15-5'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_15_5')
AUGMENTER_LOC['LAMBDA-BV-15-6'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_15_6')
AUGMENTER_LOC['LAMBDA-BV-15-7'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_15_7')
AUGMENTER_LOC['LAMBDA-BV-15-8'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_15_8')
AUGMENTER_LOC['LAMBDA-BV-15-9'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_15_9')
AUGMENTER_LOC['LAMBDA-BV-15-10'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_15_10')
AUGMENTER_LOC['LAMBDA-BV-15-11'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_15_11')
AUGMENTER_LOC['LAMBDA-BV-15-12'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_15_12')
AUGMENTER_LOC['LAMBDA-BV-15-13'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_15_13')
AUGMENTER_LOC['LAMBDA-BV-15-14'] = conc('augmenter', 'heuristics', 'lambda_bv_h264_SWEEP_15_14')



def check(struc):
    for key, val in struc.items():
        try:
            assert os.path.exists(val)
        except:
            print(val)
