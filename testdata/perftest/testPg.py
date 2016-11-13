import json
import boto3
import datetime

types = ("es","pg")
nr = 60
iter = 10
factor=10


epoch = datetime.datetime.utcfromtimestamp(0)
dt = datetime.datetime.utcnow()
msecs = (dt - epoch).total_seconds() * 1000.0


with open('coords.json') as json_data:

	session = boto3.Session(profile_name='wah')
	client = session.client('sns')
		
	alerts = {}

	i=1
	for key,coords in json.load(json_data).items():
		alerts[key]=coords
		if i==nr:
			break
		i=i+1
	
	j=0
	while  j<iter:
		for type in types:
			message = { 
			"type" : type,
			"alerts" : alerts,
			"factor" : factor
			}
		
			response = client.publish(
				TopicArn='arn:aws:sns:eu-west-1:381798314226:performanceTesting',
				Message= json.dumps(message)
			)
			
			print("posted sns iter {} {}".format(j,type))
		j=j+1

	
	
print("{:20f}".format(msecs))