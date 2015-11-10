#!/usr/bin/env python

import boto3, time, sys
from boto3.exceptions import ResourceLoadException

class SpotInstanceManager():
    def __init__(self, dry_run=False, timeout=300, verbose=True):
        self.timeout = timeout # seconds
        self.dry_run = dry_run
        self.verbose = verbose
        self.client = boto3.client('ec2')
        self.ec2 = boto3.resource('ec2')

    def get_instance_id_for_request(self, request_id):
        instance_id = None
        n = 0
        while instance_id == None and n < self.timeout:
            if n % 3 == 0 and self.verbose:
                sys.stdout.write('\rwaiting for instance to be created' + ('.' * (n/3)))
                sys.stdout.flush()
            d = self.client.describe_spot_instance_requests(DryRun=self.dry_run, \
                    SpotInstanceRequestIds=[request_id,])['SpotInstanceRequests'][0]
            if 'InstanceId' in d:
                instance_id = d['InstanceId']
            n += 1
            time.sleep(1)
        if self.verbose:
            print('')
    
        if n >= self.timeout:
            raise ResourceLoadException('\nTimed out waiting for instance to be created.\n' +
                  'IMPORTANT: instance will probably still be created ' +
                  'and may need to be canceled manually.')

        return instance_id


    def get_ip_address(self, instance):
        n = 0
        start = time.time()
        while instance.state['Name'] != 'running' and n < self.timeout:
            if n % 3 == 0 and self.verbose:
                sys.stdout.write('\rwaiting for instance to initialize' + ('.' * (n/3)))
                sys.stdout.flush()
            instance.reload()
            n += 1
            time.sleep(1)
        if self.verbose:
            print('')

        if n >= self.timeout and instance.public_ip_address is None:
            raise ResourceLoadException('\nTimed out waiting for instance to respond.\n' +
                  'Instance may still be initializing?')

        return instance.public_ip_address


    def init_spot_instance(self, price, instance_count, spec, callback):

        try:
            r = self.client.request_spot_instances( 
                DryRun=self.dry_run, 
                SpotPrice=price, 
                InstanceCount=instance_count, 
                LaunchSpecification=spec)

            request_id = r['SpotInstanceRequests'][0]['SpotInstanceRequestId']
            if self.verbose:
                print('spot instance request submitted. id: ' + request_id)

            instance = self.ec2.Instance(self.get_instance_id_for_request(request_id))
            if self.verbose:
                print('instance created. id: ' + instance.instance_id)

            public_ip = self.get_ip_address(instance)
            if self.verbose:
                print('public ip address: ' + str(public_ip))

            if callback is not None:
                callback(instance)

            return instance

        except:
            self.client.cancel_spot_instance_requests(SpotInstanceRequestIds=[request_id,])
            if self.verbose:
                print('\nCaught exception.\n' + 
                  'Making final attempt to terminate any spawned instances, do not interrupt!')
            instance_id = self.get_instance_id_for_request(request_id)
            if instance_id is not None:
                self.client.terminate_instances(InstanceIds=[instance_id,])
            raise

    def init_cuda_instance(self, price='3.5', instance_count=1, callback=None):
        spec = {
                'ImageId': 'ami-6bf29d0b', # cuda 11/9 #2
#                'ImageId': 'ami-df6a8b9b', # raw ubuntu 14.04
                'KeyName': 'cuda',
                'SecurityGroups': ['ui-access','ssh'],
                'InstanceType': 'g2.2xlarge',
                'BlockDeviceMappings': [
                    {
                        'DeviceName': '/dev/sda1',
                        'Ebs': {
                            'VolumeSize': 16,
                            'DeleteOnTermination': True,
                            'VolumeType': 'gp2',
                            'Encrypted': False
                        },
                    },
                ],}
        return self.init_spot_instance(price, instance_count, spec, callback)
            
    def add_instance_to_bash_scripts(self, instance, local_label):
        # TODO: add items to bash files to make instance accessible via terminal
        # use the local label for the commands
        pass
    
    def cancel_requests(self, request_ids):
        self.client.cancel_spot_instance_requests(SpotInstanceRequestIds=request_ids)
    
    def terminate_instances(self, instance_ids):
        self.client.terminate_instances(InstanceIds=instance_ids)

if __name__ == '__main__':
    manager = SpotInstanceManager()
    instance = manager.init_cuda_instance()
#    manager.cancel_requests([instance.spot_instance_request_id,])
#    print('Spot request ' + instance.spot_instance_request_id + ' cancelled.')
#    manager.terminate_instances([instance.instance_id,])
#    print('Instance ' + instance.instance_id + ' terminated.')
