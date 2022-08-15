# Augmenter configurations instructions

These files configure the setup
of __augmentation__ policies.
As for the __grouping__ policies,
in these folders we published the preset of 
the strategies with the parameters used 
in our work.

In the following paragraph, the meaning of 
different parameters are explained.


## Common parameters ##

This is a list of the common parameters
among all the augmentation strategies configurations:

- **name**: name of the augmentation strategy

As the decision are taken per segments, also
splitters need to be configured.

- **splitting\_module**: the module in which the splitter is implemented
- **splitting\_class**: name of the class of the splitter
- **splitting\_args/splitting\vmaf**: vmaf model that the splitter is going to use to assign to segments perceptual quality scores.
These perceptual quality scores are the one that will be accounted for augmentation.

- **augmenter\_module**: module of the augmenter
- **augmenter\_class**: class name of the augmenter
- **augmenter\_module\_args/augmenter\_encoding\_name**: name of the encoder for augmented segments 
- **augmenter\_module\_args/augmenter\_encoding\_module**: module in which the augmented segments encoder is implemented
- **augmenter\_module\_args/augmenter\_encoding\_class**: class name of the encoder for augmented segments

All strategies use some thresholds in VMAF (**vmaf\_th**) and/or bitrate (**percentage\_br\_th**). How these
thresholds are used to determine the final set of segments depends on the specific implementations.


## ABR based augmentation strategies ##

The ABR based augmentation optimisation use the following parameters.

- **look\_ahead**: the lookahead in segments steps at which the optimisation runs.
- **sim\_config**: configuration file for the simulator. Details can be found in the README in configs/simulator
- **look\_past** and  **look\_future**: define the locality of the reward computation. If **simulation\_reward\_look\_past** is set to -1, the reward is always calculated globally
- **range specific parameters**: define the ranges of VMAF and bitrate at which the augmentation strategies should be tested

