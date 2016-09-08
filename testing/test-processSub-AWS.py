import io,os,sys,re
import json
import boto3
from pprint import pprint



def makeEvent(file):
	event = json.loads(open('event.json').read())
	event["Records"][0]["Sns"]["Message"] = open(file).read()
	
	return event
	

datadir = "C:\\Users\\Timo\\Documents\\aws\\test\\loadtest\\alertsubmerge"

count=1		

s3 = boto3.client("sns")

for file in os.listdir(datadir):
	
	if not file.endswith(".json"):
		continue
	
	filepath = 	os.path.realpath(os.path.join(datadir,file))
	
	#event = makeEvent(file)
	
	print("sending {}".format(file))

	message = open(filepath).read()
	
	for n in range(1,100):
	
		# <cap:identifier>msg_actual-public_en_noof_hp</cap:identifier>
		messagenew =  re.sub(r'<cap:identifier>(.*)</cap:identifier>', r"<cap:identifier>\1-{}</cap:identifier>".format(n), message )
		
		m = json.loads(messagenew)
		m["alert"]["hubRecordKey"] = "{}.{}".format(m["alert"]["hubRecordKey"], n )
		
		r = s3.publish( TopicArn = "arn:aws:sns:eu-west-1:921181852858:timo-test-sns" , Message = json.dumps(m)	)
		print(r)
	
	#sys.exit(1)
	
	#print json.dumps(event)
	count=count+1