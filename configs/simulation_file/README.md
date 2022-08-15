## Simulation file configurations instructions

Most of the strategies in this work utilise VMAF-4K
as the template VMAF to run both grouping and 
augmentation of videos. These configurations files
tell Segue to create some simulation files with
a specific vmaf model, and split the encoded
videos in segments.


List of parameters:

- **name**: name of the splitter, usually bound to the perceptual quality model used
- **splitting\_module**: the module in which the splitter is implemented
- **splitting\_class**: name of the class of the splitter
- **splitting\_args/splitting\vmaf**: vmaf model that the splitter is going to use to assign to segments perceptual quality scores

