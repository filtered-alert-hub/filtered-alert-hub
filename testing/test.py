import io,os
import json
from pprint import pprint

import ProcessSubscription


def makeEvent(file):
	event = json.loads(open('event.json').read())
	message = json.loads(event["Records"][0]["Sns"]["Message"])
	message["alert"]["capXml"] = open(file).read()

	event["Records"][0]["Sns"]["Message"] = json.dumps(message)
	
	
	return event
	

print("event")
event = json.loads(open('event.json').read())
ProcessSubscription.lambda_handler(event,None)  

# official only false, filter official true
print("event2... should be filtered")
event = json.loads(open('event2.json').read())
ProcessSubscription.lambda_handler(event,None)  

# language ku, filter language ku
print("event3... should not be filtered")
event = json.loads(open('event3.json').read())
ProcessSubscription.lambda_handler(event,None)  

# language ku, filter language en
print("event4... should be filtered")
event = json.loads(open('event4.json').read())
ProcessSubscription.lambda_handler(event,None)  

# language priority filter
print("event5... should not be filtered")
event = json.loads(open('event5.json').read())
ProcessSubscription.lambda_handler(event,None)  

# custom xpath
print("event6... should  be filtered")
event = json.loads(open('event6.json').read())
ProcessSubscription.lambda_handler(event,None)  


datadirs = ("../capAlertTestAreas","../capAlertTestFilters")
#datadirs = ("../capTest",)

count=1		
for ddir in datadirs:
	# traverse root directory, and list directories as dirs and files as files
	for root, dirs, files in os.walk(ddir):
		path = root.split('/')
		#print ((len(path) - 1) * '---' , os.path.basename(ddir))       
		files = [ fi for fi in files if fi.endswith( (".xml") ) ]
		for file in files:
			file = 	os.path.realpath(os.path.join(root,file))
			event = makeEvent(file)
			
			#with open("{}/event_{}.json".format(ddir,count),"w" ) as f:
			#	json.dump(event,f)			
			ProcessSubscription.lambda_handler(event,None)  
			
			#print json.dumps(event)
			count=count+1