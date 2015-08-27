#!/usr/bin/python
import boto3,sys,math,time

def get_elb(elbName):
  instance_list = []
  client = boto3.client('elb')
  response = client.describe_load_balancers(LoadBalancerNames=[elbName])
  respond_raw = response['LoadBalancerDescriptions']
  for x,y in respond_raw[0].items():
    if x == 'Instances':
      for item in y:
        instance_list.append(item['InstanceId']) 
  return instance_list

def choose_instance(instance_list):
  for index, instance in enumerate(instance_list):
    print index+1, ": " , instance
  
  instance_id = raw_input('Choose instance that you want to create image: ')
  if instance_id not in instance_list:
    print "Invalid instance"
    instance_id = raw_input('Choose instance that you want to create image: ')
  return instance_id

def standby_instance_autoscale(autoscale_name,instance):
  client = boto3.client('autoscaling')
  response = client.enter_standby(
    InstanceIds=[
        instance,
    ],
    AutoScalingGroupName=autoscale_name,
    ShouldDecrementDesiredCapacity=False)

def stop_chosen_instance(instance):
  ec2 = boto3.resource('ec2')
  instance = ec2.Instance(instance)
  print "Stopping ", instance.id, " to create new AMI"
  response = instance.stop()
  count = 0
  while (count < 5):
    if instance.state['Name'] != 'stopped':
      print "Waiting for instance to stop"
      time.sleep(45)
      count = count + 1
    else: 
      break
  
def create_image(instance_id):
  ec2 = boto3.resource('ec2')
  instance = ec2.Instance(instance_id)
  image_name = instance_id + '_image'
  image = instance.create_image(
    Name=image_name,
    Description='image from automation')
  print "Taking image of ", instance_id
  print "Sleeping for 45 second"
  return image.id

def create_launch_config(ami_id):
  client = boto3.client('autoscaling')
  ami_name = ami_id + '_name'
  response = client.create_launch_configuration(

    LaunchConfigurationName=ami_name,
    ImageId=ami_id,
    KeyName='testssh',
    SecurityGroups=[
        'sg-8a78aaee',
    ],
    InstanceType='t1.micro',
    )     
  print "New launch config name is " + ami_name
  return ami_name
def update_autoscaling_group(autoscale_name,lcfg_name):
  client = boto3.client('autoscaling')
  response = client.update_auto_scaling_group(
    AutoScalingGroupName=autoscale_name,
    LaunchConfigurationName=lcfg_name)
  print "Update auto scaling group ", autoscale_name, " with launch config ", lcfg_name

def terminate_old_instance(chosen_instance,instance_list_after):
  client = boto3.client('ec2')
  print "Terminating old instance ", chosen_instance
  terminate_chosen_instance = client.terminate_instances(InstanceIds=[chosen_instance])
  for instance in instance_list_after:
    print "Terminating old instance ", instance
    terminate_loadbalancer_instance = client.terminate_instances(InstanceIds=[instance])
  
if __name__ == "__main__":
  instance_list_before = get_elb(sys.argv[1])
  chosen_instance_id = choose_instance(instance_list_before)
  standby_instance_autoscale(sys.argv[2],chosen_instance_id)
  stop_chosen_instance(chosen_instance_id)
  new_ami_id = create_image(chosen_instance_id)
  time.sleep(45)  
  new_launch_config = create_launch_config(new_ami_id)
  update_autoscaling_group(sys.argv[2], new_launch_config)
  
  instance_list_after = get_elb(sys.argv[1])
  terminate_old_instance(chosen_instance_id,instance_list_after)
