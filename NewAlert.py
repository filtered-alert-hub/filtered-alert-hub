from __future__ import print_function
from datetime import datetime
import json
import urllib
import boto3
import botocore

from boto3.dynamodb.conditions import Key, Attr
from lxml import etree,objectify
import json
from xml.etree.ElementTree import fromstring
from xmljson import badgerfish as bf

print('Loading function')

test = False
debug = True

def removeNamespaces(capXML):
	root = etree.fromstring(capXML)

	####    
	for elem in root.getiterator():
		if not hasattr(elem.tag, 'find'): continue  # (1)
		i = elem.tag.find('}')
		if i >= 0:
			elem.tag = elem.tag[i+1:]
	objectify.deannotate(root, cleanup_namespaces=True)
	####

	return root
	
def loadandvalidateCAP(capXML):
	
	if "urn:oasis:names:tc:emergency:cap:1.1" in capXML:
		capschema = "xsds/cap1-1.xsd"
		namespace = "urn:oasis:names:tc:emergency:cap:1.1"
	elif "urn:oasis:names:tc:emergency:cap:1.2" in capXML:
		capschema = "xsds/cap1-2.xsd"
		namespace = "urn:oasis:names:tc:emergency:cap:1.2"
	else:
		raise Exception("unknown schema: {}".format( capXML[0:100] ))
   
	xmlschema_doc = etree.parse(capschema)
	xmlschema = etree.XMLSchema(xmlschema_doc)	

	doc = etree.fromstring(capXML)
	if not xmlschema.validate(doc):
		raise Exception("alert not valid CAP")
	
	return [namespace,doc]
	
def lambda_handler(event, context):
    #print("Received event: " + json.dumps(event, indent=2))

	
	if test: 
		session = boto3.Session(profile_name='wah')
	else:
		session = boto3.Session()
	
	s3 = session.client("s3")
	
	for record in event["Records"]:
	
		bucket = record["s3"]["bucket"]["name"]
		key = urllib.unquote(record["s3"]["object"]["key"])
		if debug: 
			print("received record in S3. b:{} k:{}".format(bucket,key))
		
		if test:
			capXML = open('..\\test\\capAlertTestAreas\\2016-03-10-10-53-13-217.xml').read()
		else:
			capXML = s3.get_object(Bucket=bucket,Key=key)["Body"].read()
			
		hubbucket = "alert-hub"
		folder = key[0:key.rfind('/')]
		timekey = datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S-%f')[:-3]

		hubrecordkey = "{}/{}.xml".format(folder, timekey)
		
		if debug:
			print("bucket {} key {} folder {} ".format(bucket,key,folder))
			print("copying b:{}/k:{} to b:{}/k:{}".format(bucket,key,hubbucket,hubrecordkey))

		if test:
			pass
		else:
			s3.copy( { 'Bucket' : bucket , 'Key' : key } , hubbucket, hubrecordkey )
		

		[namespace,doc] = loadandvalidateCAP(capXML)
		
		# check for duplicates
		namespaces = {'cap': namespace }

		capAlertIdentifier = doc.xpath("//cap:identifier/text()", namespaces=namespaces)[0]
		capAlertSender = doc.xpath("//cap:sender/text()", namespaces=namespaces)[0]
		capAlertSent = doc.xpath("//cap:sent/text()", namespaces=namespaces)[0]
	
		id = '{}|{}|{}'.format(capAlertIdentifier,capAlertSender,capAlertSent)
		
		if debug:
			print("checking records {} for duplication ".format(id))

		if not test:
			dynamodb = session.resource('dynamodb') 
			table = dynamodb.Table('wah-received-alerts')
			response = table.query(
				KeyConditionExpression=Key('id').eq(id)
			)
			
			if response["Count"]>0:
				print("{} already processed.. doing nothing".format(id))
				return

			table.put_item(  Item={ 'id': id } )
		
		# send message on to area filter
		topicArn = "arn:aws:sns:eu-west-1:381798314226:wah_post-alert-capture";
		highlevelfolder =  folder[0:folder.find('/')] if '/' in folder else folder
		sourceMetadataObjectKey = "{}/metadata.json".format(highlevelfolder)

		if debug: 
			print("getting source metadata from {} {}".format(bucket,sourceMetadataObjectKey))
		
		try:
			response = s3.get_object(Bucket=bucket,Key=sourceMetadataObjectKey)
			sourceMetadata= json.load(response["Body"])
			if 'source' in sourceMetadata: # some metadata seem to have the source attribute, others not
				sourceMetadata = sourceMetadata["source"]

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
				'capXml' : capXML,
				'capJson' : bf.data( removeNamespaces(capXML)  ) # JSON representation of alert for later use
			}}

		except botocore.exceptions.ClientError as ce:
			print("erorr getting source metadata {} {} ({})".format(bucket,sourceMetadataObjectKey,ce))
			return False
		except ValueError as ve:
			print("error parsing JSON metadata for {} {} ({})".format(bucket,sourceMetadataObjectKey,ve))
			return False
		except KeyError as ke:
			print("{} error getting source metadata: {}".format(ke,json.dumps(sourceMetadata)))
			return False
		
		#if debug: 
		#	print(json.dumps( alert["alert"]["capJson"] ))
		
		sns = session.client('sns')
		sns.publish(
			TopicArn = topicArn,
			Message = json.dumps(alert)
		)
		
	
		if debug:
			print("sent new alert {} on to arn: {}".format(hubrecordkey,topicArn))
