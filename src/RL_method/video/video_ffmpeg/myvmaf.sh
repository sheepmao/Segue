#!/bin/bash
set -e
#Usage: ./myvmaf.sh REFERENCE DISTORTED WIDHT HEIGHT MODEL EXTRAVMAFOSSEXECARGS

S1=$(mktemp -u).yuv
S2=$(mktemp -u).yuv
mkfifo $S1
mkfifo $S2
ffmpeg -i $1 -vsync 0 -vf scale=$3:$4 -pix_fmt yuv420p -y $S1 &
ffmpeg -i $2 -vsync 0 -vf scale=$3:$4 -pix_fmt yuv420p -y $S2 &
vmafossexec yuv420p $3 $4 $S1 $S2 $5 "${@:6:99}"
rm $S1
rm $S2




