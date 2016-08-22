from __future__ import print_function

import StringIO
import json
import boto3
from lxml import etree

#from lxml import etree

print('Loading function')

class CAPFilter:
	
	officialOnly=False
	langOnly=False
	filterXpath=None
	priorityOnly=False
	
	def __init__(self,options):
		
		default_options = { "official" : False, "priortiy" : False, "xpath" : None, "language" : []  }
		default_options.update(options)
		
		for option,val in options.items():
			if (option=="official"):
				self.officialOnly=val
			elif (option=="priority"):
				self.priorityOnly=val
			elif (option=="xpath"):
				self.filterXpath= False if (val == "none") else val
			elif (option=="language"):
				self.langOnly = False if (val == "none"  ) else val.split(",")
			else:
				raise Exception("argument "+option+" not supported")
		
	def __str__(self):	
	
		#rough_string = ET.tostring(root, 'utf-8')
		#reparsed = parseString(rough_string)
		#print(reparsed.toprettyxml(indent="\t"))
	
		ret = ""
		if (self.officialOnly):
			ret+=" official"
		if (self.langOnly):
			ret+=" languages" + ( ",".join(self.langOnly) )
		if (self.priorityOnly):
			ret+=" priority"
		if (self.filterXpath):
			ret+=" expression {}".format(self.filterXpath)
		if (len(ret)>0):
			ret = "filtering for "+ret
		else: 
			ret = "not filtering" 
		return ret
		
	def matches(self,alert):
	
		root = None
		capxml = alert["capXml"]
		temp = StringIO.StringIO(capxml.encode('utf-8'))
		tree = etree.parse( temp )
		root = tree.getroot()

		if (self.officialOnly):
			if not alert["sourceIsOfficial"]:
				return False
		
		if (self.langOnly):
			if not alert["sourceLanguage"] in self.langOnly:
				return False
				
		if (self.priorityOnly):
			if not self.checkPriority(alert,tree):
				return False
		
		if (self.filterXpath):
			if not self.checkPath(root,self.filterXpath):
				return False
				
		return True
	
	def checkPath(self,root,xpexpression):
		namespaces = {'cap': 'urn:oasis:names:tc:emergency:cap:1.1'}
		return root.xpath(xpexpression,namespaces=namespaces)
	
	def checkPriority(self,alert,root):

		namespaces = {'cap': 'urn:oasis:names:tc:emergency:cap:1.1'}

		passActualAlertPublic = "//cap:status='Actual' and (//cap:msgType='Alert' or //cap:msgType='Update') and //cap:scope='Public'"
		if not root.xpath(passActualAlertPublic,namespaces=namespaces):
			return False
				
		passHighPriority = "//cap:urgency[.='Immediate' or .='Expected'] and //cap:severity[.='Extreme' or .='Severe'] and //cap:certainty[.='Observed' or .='Likely']"
		if not root.xpath(passHighPriority,namespaces=namespaces):
			return False
		
		blockUsWea = "//cap:parameter/cap:valueName[.='BLOCKCHANNEL']/../cap:value[.= 'CMAS' or .= 'EAS' or .= 'NWEM' or .= 'Public']"
		if root.xpath(blockUsWea,namespaces=namespaces):
			return False
		
		return True
		
def parseEvent(event):

	message = json.loads(event["Records"][0]["Sns"]["Message"])

	alert = message["alert"]
	subscription = message["subscription"]
	alertId = alert["hubRecordKey"]
	feedid = subscription["subscriptionId"]
	
	print("processing alert {} for subscription: {}".format(alertId,feedid))
	
	# TODO: check if actually present
	filterOptions = {
		"official" : subscription["officialOnly"],
		"priority" : subscription["highPriorityOnly"],
		"language" : subscription["languageOnly"],
		"xpath" : subscription["xPathFilter"]
	}
	
	
	capFilter = CAPFilter(filterOptions)
	
	#print(capFilter)
	
	if capFilter.matches( alert ) :
		url = subscription["subscriptionUrl"]
		print("adding {} to subscription {} id:{} ..off to Kinesis".format(alertId,url,feedid))

		kinesismessage = { "alert" : alert , "subscription" : subscription  }
		
		kinesis = boto3.client('kinesis')
		kinesis.put_record(StreamName="testkinesisstream", Data=json.dumps(kinesismessage), PartitionKey = feedid)

		

def lambda_handler(event, context):
	#print("Received event: " + json.dumps(event, indent=2))
	#print("one more line")
	parseEvent(event)
	return True 
	#raise Exception('Something went wrong')