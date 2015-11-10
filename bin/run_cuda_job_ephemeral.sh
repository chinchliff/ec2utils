#!/bin/bash

# shell script to spin up amazon ec2 cuda spot instance, execute a job on it, and shut
# down the instance once the job is complete

pem=$1
user=$2
jobcommand=$3

# spin up a spot instance and collect the ip
#echo "requesting spot instance..."
#domain="$(python -c 'from EC2Utils import SpotInstanceManager; s = SpotInstanceManager(verbose=False); print(s.init_cuda_instance().public_ip_address)')"

domain=54.193.55.43

echo "will execute job on temporary instance at $domain"
#echo "sleeping for 2 minutes while remote initializes (hopefully)"
#sleep 120
cmd="ssh -o StrictHostKeyChecking=no $domain"
echo $cmd
$cmd

# push the job script to the spot instance
#cmd="scp -i $pem $jobscript $user@$domain:~/CURRENT_JOB_COMMAND"

# write the job command into a file to be executed on the remote
cmd="ssh -i $pem $user@$domain echo '$jobcommand' > CURRENT_JOB_COMMAND && chmod +x CURRENT_JOB_COMMAND"
echo $cmd
$cmd

# start a screen and execute $jobscript within it, terminate the instance when $jobscript
# completes. note, $jobscript must push its output somewhere external to the instance or
# it will be lost when the instance terminates
cmd="ssh -i $pem $user@$domain screen -d -m ./CURRENT_JOB_COMMAND && sudo shutdown -f now"
echo $cmd
#$cmd