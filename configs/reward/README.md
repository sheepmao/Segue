## Reward configurations instructions

These parameters indicate the configurations for 
the reward function. In this work, only a linear
version has been implemented.


List of parameters:

- **simulation\_reward\_module**: module at which the reward function is implemented
- **simulation\_reward\_class**: name of the class at which the reward function is implemented
- **reward\_id**: id of the reward implementation
- **simulation\_reward\_parameters**: list of the weights of different parameters for the QoE function and 
time normalisation (i.e. at which granularity the reward should be computed).
