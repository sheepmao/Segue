# Welcome to Segue!

Welcome! 
We will now guide you in the setup and first run of Segue.
Segue is a video preparation system that adapts video
chunking depending on the expected rate adaptation and
network behavior.


If you haven't yet, please read our [paper](https://escholarship.org/uc/item/8m39f25q)
published at JSys!

## Install

Install docker according to your OS and make sure your current user is able to
use docker. In a default installation on Ubuntu Linux, only root is allowed to
run docker containers. In this case, make sure to follow the instructions as
root user.

Download the docker image (about 2 GB) with the following command:

```
docker pull melissalicc/maya
```

Clone or unpack Segue, open a terminal and change directory to the `docker`
subdirectory: `cd segue/docker`. Then, enter the docker container with the
`run.sh` command. This script uses some relative paths, so it is important to
run it while being in the `docker` directory. (I.e don't do a `./docker/run.sh`
this will not work).

This script will start bash within the docker container, the segue directory
will be mounted in `/segue`. So after you do a `cd /segue` you can invoke
the execution script.



## Configs

Instructions coming soon!


## Executions

Exec script coming soon!
