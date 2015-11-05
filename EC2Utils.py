#!/usr/bin/env python

import boto3, time, sys
from boto3.exceptions import ResourceLoadException

class SpotInstanceManager():
    def __init__():
        self.timeout = 300 # seconds
        self.dry_run = False
        self.client = boto3.client('ec2')
        self.ec2 = boto3.resource('ec2')

    def get_instance_id_for_request(self, request_id):
        instance_id = None
        n = 0
        while instance_id == None and n < timeout:
            if n % 3 == 0:
                sys.stdout.write('\rwaiting for instance to be created' + ('.' * (n/3)))
                sys.stdout.flush()
            d = self.client.describe_spot_instance_requests(DryRun=dry_run, \
                    SpotInstanceRequestIds=[request_id,])['SpotInstanceRequests'][0]
            if 'InstanceId' in d:
                instance_id = d['InstanceId']
            n += 1
            time.sleep(1)
        print('')
    
        if n >= timeout:
            print('\nTimed out waiting for instance to be created.\n' +
                  'IMPORTANT: instance will probably still be created ' +
                  'and may need to be canceled manually.')
            raise ResourceLoadException()

        return instance_id


    def get_ip_address_for_instance(self, instance):
        n = 0
        start = time.time()
        while instance.state['Name'] != 'running' and n < timeout:
            if n % 3 == 0:
                sys.stdout.write('\rwaiting for instance to initialize' + ('.' * (n/3)))
                sys.stdout.flush()
            instance.reload()
            n += 1
            time.sleep(1)
        print('')

        if n >= timeout and instance.public_ip_address is None:
            print('\nTimed out waiting for instance to initialize.\n' +
                  'IMPORTANT: Instance may still be initializing but ' +
                  'has NOT been terminated.')

        return instance.public_ip_address


    def init_spot_instance(self, price, instance_count, ami_id, key_name, security_groups, instance_type):

        spec = {'ImageId': ami_id,
                'KeyName': key_name,
                'SecurityGroups': security_groups,
                'InstanceType': instance_type}

        try:
            r = self.client.request_spot_instances( 
                DryRun=dry_run, 
                SpotPrice=price, 
                InstanceCount=instance_count, 
                LaunchSpecification=spec)

            request_id = r['SpotInstanceRequests'][0]['SpotInstanceRequestId']
            print('spot instance request submitted. id: ' + request_id)

            instance = self.ec2.Instance(get_instance_id(request_id))
            print('instance created. id: ' + instance.instance_id)

            public_ip = get_ip_address(instance)
            print('public ip address: ' + str(public_ip))

            return instance

        except:
            self.client.cancel_spot_instance_requests(SpotInstanceRequestIds=[request_id,])
            print('\nCaught exception.\n' + 
                  'Making final attempt to terminate any spawned instances, do not interrupt!')
            instance_id = get_instance_id(request_id)
            if instance_id is not None:
                self.client.terminate_instances(InstanceIds=[instance_id,])

    def init_cuda_instance(self, price='3.5', instance_count=1, callback=None):
        instance = init_spot_instance(price, instance_count, 
            ami_id = 'ami-79cd0e3d', 
            key_name = 'cuda', 
            security_groups = ['ui-access','ssh'], 
            instance_type = 'g2.2xlarge')
        if callback is not None:
            callback(instance)
        return instance
            
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
    manager.cancel_requests([instance.spot_instance_request_id,])
    print('Spot request ' + instance.spot_instance_request_id + ' cancelled.')
    manager.terminate_instances([instance.instance_id,])
    print('Instance ' + instance.instance_id + ' terminated.')
