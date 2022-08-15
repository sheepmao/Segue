## Simulator configurations instructions

These parameters configure the simulator.
Usually they are divided into two sets: the configuration
files used for training purposes (e.g. for running the WideEye
grouping strategy) and the one used for inference.

The list of used parameters are the same, they only differ for the
used traces.

List of parameters:

- **name**: name of the ABR
- **simulation\_abr\_module**: file in which the ABR is implemented
- **simulation\_traces\_path**: which traces to use during the simulation
- **simulation\_reward\_config**: which reward function configuration to use (configs/reward)
