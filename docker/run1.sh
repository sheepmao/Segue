set -e
NAME=segue_bash_`shuf -i 2000-65000 -n 1`
CT=sheepmao
HOSTNAME=segue_root

echo "Starting container name=$NAME with image $CT"
echo "Hostname --> $HOSTNAME"
echo "PWD --> $(pwd)"

sudo docker run \
    --hostname $HOSTNAME\
    --mount type=bind,source=$(pwd)/..,target=/segue \
    --name $NAME --rm -i -t $CT bash 
