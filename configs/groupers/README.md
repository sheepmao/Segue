# Grouper configurations instructions #

These files configure the setup
of __grouping__ policies.
In these folder we published the preset of 
grouping strategies with the parameters used 
in our work.

In the following paragraph, the meaning of 
different parameters are explained.


## Common parameters ##

This is a list of the common parameters
among all the grouping strategies configurations

- **name**: name of the grouping strategy
- **store\_folder**: subfolder of the grouping strategy, it should be set to be parameter dependent
- **module**: path to the module in which the grouping strategy is implemented
- **class**: class name of the implemented strategy
- **parameters/bitrate\_ladders\_csv**: path to the CSV containing the target bitrate configurations

## Constant length segments encoding ##

Constant length encoding configurations used in this work are located in the folder "constant\_length".
It requires only an additional parameter:

- **parameters/seconds**: target segment length in seconds


## Common parameters for variable length segments ##

All variable length segments grouping strategies have some 
parameters in common, that are briefly listed here:

- **parameters/gop\_seconds**: refers to the wanted gop size for encoding (in seconds)

Given that most of the strategy reuse the same encoded video (i.e. encoded at the same
gop size), these parameters indicate the path at which these cache can be stored/retrieved.
- **parameters/cache\_store\_folder\_template**: where to save/recover the previously encoded video. The
formatting parameters are the video name and the various resolutions
- **parameters/cache\_file\_name**: the name of the cached video
- **parameters/fragments\_folder\_template**: the already fragmented video (each fragment is a GOP, the grouping
strategy has not been computed).  The formatting parameters are the video name and the various resolutions


Some grouping strategies already compute the VMAF score.
In such a case, the parameter that indicates which model to use is **simulation\_vmaf\_model\_name**.


## Heuristics parameters ##

The implemented heuristics are __Time__, __Bytes__ and __Time+Bytes__. Please refer to our
paper for details in the implementation.

The configuration parameters utilised are:

- **lookahead\_opt**: the lookahead in fragment steps at which the optimisation runs.
- **target\_segments\_length\_opt**: target segment length in seconds. Used in __Time__ and __Time+Bytes__.
- **bytes\_like\_average\_seconds\_opt**: target bytes length expressed as the average bytes length for a segment of **param** second. 
Used in __Bytes__ and __Time+Bytes__.


## ABR based grouping optimisation ##

The ABR based grouping optimisation use the following parameters.

- **lookahead\_opt**: the lookahead in fragment steps at which the optimisation runs.
- **sim\_config**: configuration file for the simulator. Details can be found in the README in configs/simulator
- **simulation\_reward\_look\_past** and  **simulation\_reward\_look\_future**: define the locality of the reward computation per combo. If **simulation\_reward\_look\_past** is set to -1, the reward is always calculated globally.

WideEye grouping optimisation also takes as an input the parameters of __Time+Bytes__.
Additionally, the following parameters need to be specified.


- **wide\_eye\_step**: how many fragment steps should be taken per iteration
- **wide\_eye\_combo\_filte**: how many different combos of __Time+Bytes__ should be tested
- **wide\_eye\_filtering\_res**: at which resolution index __Time+Bytes__ grouping should be performed

