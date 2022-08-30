#!/bin/bash
set -e

if [ "$#" -le 5 ]; then
    echo "Illegal number of parameters (POSITIONAL). USAGE:"
    echo " REQUIRED: VIDEO [ VIDEO IDs IDENTIFIERS ]"
    echo " REQUIRED: ABR [ BB | RB | RMPC-A | RMPC-O ]"
    echo " REQUIRED: TRACES [ TRACE SET IDENTIFIERS ]"
    echo " REQUIRED: VMAF ID IDENTIFIER [ MOBILE - HDTV - 4K]"
    echo " REQUIRED: GROUPER [ K-{1..5} | GOP-{1..5} | TIME | BYTES | TIME+BYTES | SIM | WIDE-EYE')  "
    echo " REQUIRED: AUGMENTER [ NONE | SIGMA-BV | CBF-{40,60,80} | SIVQ-{5,10,15} | LAMBDA-B | LAMBDA-V | LAMBDA-BV-{5,10,15}-{5..14}'"
    echo " OPTIONAL: GROUPER COMPARE -> defaulT: K-5"
    echo " OPTIONAL: AUGMENTER COMPARE -> defaulT: NONE"

    exit
fi

VIDEO=$1
ABR=$2
TRACES=$3
VMAF=$4
GROUPER=$5
AUGMENTER=$6
GROUPER_C=K-5
AUGMENTER_C=NONE

if [ "$#" -eq 8 ]; then
    echo "CUSTOM COMPARISON SELECTED"
	GROUPER_C=$7
	AUGMENTER_C=$8
    exit
fi

echo "Executing Segue for video => $VIDEO, abr => $ABR, traces => $TRACES, vmaf_model => $VMAF"
echo "Generating execution Makefile for grouper => $GROUPER and augmented => $AUGMENTER"
PYTHONPATH=`pwd` python3 make_run/build_single_execution.py 	--video $VIDEO\
								--abr $ABR\
								--traces $TRACES\
								--vmaf $VMAF\
								--grouper $GROUPER\
								--augmenter $AUGMENTER\
								--fname to_compare\
								--cache_dir make_run/caches_compare\
								--post_out POST_TEMP


echo "Executing Segue pipeline"
make -f make_run/caches_compare/to_compare
echo "Executing postprocessing"
make -f make_run/caches_compare/to_compare_post




echo "Generating execution Makefile for grouper => $GROUPER_C and augmented => $AUGMENTER_C"
PYTHONPATH=`pwd` python3 make_run/build_single_execution.py 	--video $VIDEO\
								--abr $ABR\
								--traces $TRACES\
								--vmaf $VMAF\
								--grouper $GROUPER_C\
								--augmenter $AUGMENTER_C\
								--fname reference\
								--cache_dir make_run/caches_reference\
								--post_out POST_TEMP



echo "Executing Segue pipeline for reference"
make -f make_run/caches_reference/reference
echo "Executing postprocessing for reference"
make -f make_run/caches_reference/reference_post


echo "Executing post processing"
PYTHONPATH=`pwd` python3 make_run/elaborate_single_execution.py --traces $TRACES --reference POST_TEMP/csv/reference_distr.csv --compare POST_TEMP/csv/to_compare_distr.csv
rm -r POST_TEMP

