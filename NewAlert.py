from __future__ import print_function
from datetime import datetime
import json
import urllib
import boto3
from boto3.dynamodb.conditions import Key, Attr
from lxml import etree
import json

print('Loading function')

test = True

def loadandvalidateCAP(capXML):
	
	if "urn:oasis:names:tc:emergency:cap:1.1" in capXML:
		capschema = "xsds\\cap1-1.xsd"
		namespace = "urn:oasis:names:tc:emergency:cap:1.1"
	elif "urn:oasis:names:tc:emergency:cap:1.2" in capXML:
		capschema = "xsds\\cap1-2.xsd"
		namespace = "urn:oasis:names:tc:emergency:cap:1.2"
	else:
		raise Exception("unknown schema")
   
	xmlschema_doc = etree.parse(capschema)
	xmlschema = etree.XMLSchema(xmlschema_doc)	

	doc = etree.fromstring(capXML)
	if not xmlschema.validate(doc):
		raise Exception("alert not valid CAP")
	
	return [namespace,doc]
	
def lambda_handler(event, context):
    #print("Received event: " + json.dumps(event, indent=2))

	
	session = boto3.Session(profile_name='wah')
		
	s3 = session.client("s3")
	
	for record in event["Records"]:
	
		bucket = record["s3"]["bucket"]["name"]
		key = record["s3"]["object"]["key"]
		print("b:{} k:{}".format(bucket,key))
		
		if test:
			capXML = open('..\\test\\capAlertTestAreas\\2016-03-10-10-53-13-217.xml').read()
		else:
			capXML = s3.get_object(Bucket=bucket,Key=key)["Body"]
			
		hubbucket = "alert-hub"
		folder = key[0:key.rfind('/')]
		timekey = datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S-%f')[:-3]

		#     	String hubRecordKey = folderName+"/"+generateKey();  

		hubrecordkey = "{}/{}".format(folder, timekey )
		
		print("hubb: {} and folder: {} key:{}".format(hubbucket,folder,key))

		if test:
			print("s3.copy( { 'Bucket' : bucket , 'Key' : key } , hubbucket, hubrecordkey )")
		else:
			s3.copy( { 'Bucket' : bucket , 'Key' : key } , hubbucket, hubrecordkey )
		
		#parser = ET.XMLParser(remove_blank_text=True)
		#rssdom = ET.parse(,parser)
		#rssroot = rssdom.getroot()

		[namespace,doc] = loadandvalidateCAP(capXML)
		
		# check for duplicates
		
		namespaces = {'cap': namespace }

		capAlertIdentifier = doc.xpath("//cap:identifier/text()", namespaces=namespaces)[0]
		capAlertSender = doc.xpath("//cap:sender/text()", namespaces=namespaces)[0]
		capAlertSent = doc.xpath("//cap:sent/text()", namespaces=namespaces)[0]
	
		print("id: {} sender: {} sent: {}".format(capAlertIdentifier,capAlertSender,capAlertSent))

		id = '{}|{}|{}'.format(capAlertIdentifier,capAlertSender,capAlertSent)
		
		dynamodb = session.resource('dynamodb') 
		table = dynamodb.Table('wah-received-alerts')
		response = table.query(
			KeyConditionExpression=Key('id').eq(id)
		)
		
		#print(response)
		if response["Count"]>0:
			print("{} already processed.. doing nothing".format(id))
			#return

		table.put_item(  Item={ 'id': id } )
		
		
		# send message on to area filter
		topicArn = "arn:aws:sns:eu-west-1:381798314226:wah_post-alert-capture";

		sourceMetadataObjectKey = "{}/metadata.json".format(folder)

		print("getting source metadata from {} {}".format(bucket,sourceMetadataObjectKey))
		
		response = s3.get_object(Bucket=bucket,Key=sourceMetadataObjectKey)
		sourceMetadata= json.load(response["Body"])

		
		alert = { "alert" : { 
			'sourceName' : sourceMetadata['sourceName'],
			'sourceIsOfficial' : sourceMetadata['sourceIsOfficial'],
			'sourceLanguage' : sourceMetadata['sourceLanguage'],
			'folderName' : folder,
			'inputRecordKey' : key,
			'inputBucketName' : bucket,
			'hubRecordKey' : hubrecordkey,
			'hubBucketName' : hubbucket,
			'capNamespaceUri' : namespace,
			'capXml' : capXML
		}}
		
		print(json.dumps(alert))
		
		sns = session.client('sns')
		sns.publish(
			TopicArn = topicArn,
			Message = json.dumps(alert)
		)
				
		
		
		print("done")
