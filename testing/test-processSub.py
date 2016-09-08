import io,os,sys
import json
from pprint import pprint

sys.path.append( ".." )

import ProcessSubscription


def makeEvent(file):
	event = json.loads(open('event.json').read())
	event["Records"][0]["Sns"]["Message"] = open(file).read()
	
	return event
	

datadir = "C:\\Users\\Timo\\Documents\\aws\\test\\loadtest\\alertsubmerge"

count=1		


for file in os.listdir(datadir):
	
	if not file.endswith(".json"):
		continue
	
	file = 	os.path.realpath(os.path.join(datadir,file))
	event = makeEvent(file)
	
	#print("testing {}".format(file))
	ProcessSubscription.lambda_handler(event,None)  
	
	#print json.dumps(event)
	count=count+1