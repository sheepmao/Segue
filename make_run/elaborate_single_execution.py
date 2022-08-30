import argparse
import os
import pandas as pd
import ast 
import numpy as np

NORMALIZATION_VMAF_INSTABILITY = 3.2
NORMALIZATION_QOE = 25



if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--traces", required=True)
    args = parser.parse_args()

    assert os.path.exists(args.compare)
    assert os.path.exists(args.reference)
   
    reference = pd.read_csv(args.reference).iloc[0]
    compare = pd.read_csv(args.compare).iloc[0]

    assert reference['video'] == compare['video']
    assert reference['abr'] == compare['abr']

    vmaf_default_o_v = reference['vmaf_distr']
    vmaf_default_o_v = [ float(x) for x in list(ast.literal_eval(vmaf_default_o_v))]
                
    vmaf_compare_o_v = compare['vmaf_distr']
    vmaf_compare_o_v = [ float(x) for x in list(ast.literal_eval(vmaf_compare_o_v))]

    vmaf_impro_mean = (np.mean(vmaf_compare_o_v) - np.mean(vmaf_default_o_v))*100/np.mean(vmaf_default_o_v)
    vmaf_impro_5_perc = (np.percentile(vmaf_compare_o_v, 5) - np.percentile(vmaf_default_o_v, 5))*100/np.mean(vmaf_default_o_v)
                    
    stability_default_o_v_r = reference['vmaf_switches_distr']
    stability_default_o_v = [ float(x)/NORMALIZATION_VMAF_INSTABILITY for x in list(ast.literal_eval(stability_default_o_v_r))]
                
    stability_compare_o_v_r = compare['vmaf_switches_distr']
    stability_compare_o_v = [ float(x)/NORMALIZATION_VMAF_INSTABILITY for x in list(ast.literal_eval(stability_compare_o_v_r))]
                    

    stability_impro_mean = (np.mean(stability_default_o_v) - np.mean(stability_compare_o_v))*100
    stability_impro_95_perc= (np.percentile(stability_default_o_v, 95) - np.percentile(stability_compare_o_v, 95))*100
                    

    rebuffer_ratio_default_o_v = reference['rebuffer_ratio_distr']
    rebuffer_ratio_default_o_v = [ float(x)*60 for x in list(ast.literal_eval(rebuffer_ratio_default_o_v))]
                    
    rebuffer_ratio_compare_o_v = compare['rebuffer_ratio_distr']
    rebuffer_ratio_compare_o_v = [ float(x)*60 for x in list(ast.literal_eval(rebuffer_ratio_compare_o_v))]
                    

    rebuffer_ratio_impro_mean = np.mean(rebuffer_ratio_default_o_v) - np.mean(rebuffer_ratio_compare_o_v)
    rebuffer_ratio_impro_95_perc = np.percentile(rebuffer_ratio_default_o_v, 95) - np.percentile(rebuffer_ratio_compare_o_v, 95)
                    

    qoe_default_o_v = reference['qoe_distr']
    qoe_default_o_v = [ float(x)*100/NORMALIZATION_QOE for x in list(ast.literal_eval(qoe_default_o_v))]
                
    qoe_compare_o_v = compare['qoe_distr']
    qoe_compare_o_v = [ float(x)*100/NORMALIZATION_QOE for x in list(ast.literal_eval(qoe_compare_o_v))]
                    
    qoe_impro_mean = np.mean(qoe_compare_o_v) - np.mean(qoe_default_o_v)
    qoe_impro_5_perc = np.percentile(qoe_compare_o_v, 5) - np.percentile(qoe_default_o_v, 5)

    

    print("Video: {}, ABR: {}, Traces: {}".format(reference['video'], reference['abr'], args.traces))
    print("VMAF impro mean: {}, VMAF impro 5-perc: {}".format(round(vmaf_impro_mean,2), round(vmaf_impro_5_perc,2)))
    print("Stability impro mean: {}, Stability impro 95-perc: {}".format(round(stability_impro_mean,2), round(stability_impro_95_perc,2)))
    print("Rebuffer Ratio impro mean: {}, Rebuffer ratio impro 95-perc: {}".format(round(rebuffer_ratio_impro_mean, 2), round(rebuffer_ratio_impro_95_perc,2)))
    print("QOE impro mean: {}, QOE impro 5-perc: {}".format(round(qoe_impro_mean, 2), round(qoe_impro_5_perc,2)))
