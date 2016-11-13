from __future__ import print_function
import json
import base64
import sys
from datetime import datetime,date,time,timedelta
import dateutil
import dateutil.parser
from lxml import etree as ET
import StringIO
from io import BytesIO

import boto3

debug = True

maxfeeditems=200
maxfeedsecs = 60*60*2 # 2 hours 

def makeItem(caproot,metadata):

	newitem = ET.Element("item")
	ET.register_namespace('dc', "http://purl.org/dc/elements/1.1/" )


	title = ET.SubElement(newitem, "title")
	link = ET.SubElement(newitem, "link")
	description = ET.SubElement(newitem, "description")
	category = ET.SubElement(newitem, "category")
	itempubDate = ET.SubElement(newitem, "pubDate")
	guid = ET.SubElement(newitem, "guid")
	creator = ET.SubElement(newitem, "{http://purl.org/dc/elements/1.1/}creator")
	itemdate = ET.SubElement(newitem, "{http://purl.org/dc/elements/1.1/}date")


	namespaces = {'cap': 'urn:oasis:names:tc:emergency:cap:1.1'}

	alerttime = dateutil.parser.parse(caproot.xpath("string(cap:sent/text())", namespaces=namespaces ))
	#print("got time {} from cap".format(alerttime))
	alerttime =  (alerttime - alerttime.utcoffset()).replace(tzinfo=None) if alerttime.utcoffset() else alerttime #convert to UTC
	#print("converted to  {} ".format(alerttime))


	title.text = caproot.xpath("string(cap:info/cap:headline/text())", namespaces=namespaces )
	link.text = metadata["link"]
	description.text = caproot.xpath("string(cap:info/cap:description/text())", namespaces=namespaces )
	itempubDate.text = alerttime.strftime("%a, %d %b %Y %H:%M:%S %z")
	itemdate.text = alerttime.isoformat()
	guid.text = caproot.xpath("string(cap:identifier/text())", namespaces=namespaces )

	sender = caproot.xpath("string(cap:sender/text())", namespaces=namespaces )
	senderName = caproot.xpath("string(cap:senderName/text())", namespaces=namespaces )

	creator.text =  "{} ({})".format(sender,senderName) if senderName else sender 
	category.text = ",".join(caproot.xpath("cap:info/cap:category/text()",namespaces=namespaces))

	return newitem

def writeItemsToFeed(feedroot,items):

	#prune old items 
	timenow = datetime.utcnow() #now timezone aware. need to add in formating
	i=1
	for olditem in feedroot.xpath("/rss/channel/item"):
		itemnr = len(items)+i #need to consider the newly arrived items
		remove=False
		try:
			itemdate = dateutil.parser.parse(olditem.find('pubDate').text).replace(tzinfo=None)
			if itemnr > maxfeeditems and (timenow - itemdate) > timedelta(seconds=maxfeedsecs) :
				remove=True
		except TypeError as te:
			print("problem pruning item {} (nr:{} date:{} date:{} ) ({}) ".format(olditem,itemnr,itemdate,timenow,te))
		except AttributeError as ae:
			print("problem getting date of item {} ({}) .. pruning anyway".format( ET.tostring(olditem),ae) )
			remove = itemnr > maxfeeditems
		
		if remove:
			olditem.getparent().remove(olditem)
			if debug:
				print("removed item {} from feed".format(olditem))
			
		i=i+1

	existingitems = feedroot.xpath("/rss/channel/item")
	if existingitems:
		firstitem = existingitems[0]
		parent = firstitem.getparent()
		idx = parent.index(firstitem)

	else:
		parent = feedroot.xpath("/rss/channel")
		parent = parent[0]
		idx = len(parent)

	for i,newitem in enumerate(items):
		parent.insert(idx, newitem)

	#update pubdates

	timenow = datetime.utcnow() #now timezone aware. need to add in formating
	pubdate =  "{} GMT".format(timenow.strftime("%a, %d %b %Y %H:%M:%S")) 
	dcdate = "{}Z".format(timenow.isoformat())
	
	#print("setting date feed update to {} and {}".format(pubdate,dcdate))

	pubdateelem = feedroot.xpath("/rss/channel/pubDate")
	if pubdateelem:
		pubdateelem = pubdateelem[0]
		pubdateelem.text = pubdate

	namespaces = {'dc': 'http://purl.org/dc/elements/1.1/'}
	dcdateelem = feedroot.xpath("/rss/channel/dc:date",namespaces=namespaces)	
	if dcdateelem:
		dcdateelem = dcdateelem[0]
		dcdateelem.text = dcdate

	
def updateRss(feedupdate):

	feedinfo = feedupdate["feedinfo"]
	feedid =  feedinfo["id"]
	feedurl = feedinfo["url"]
	alerts = feedupdate["alerts"]

	print("updating {} with {} items".format(feedid,str(len(alerts))))
	items = []
	for alert in alerts:
		capxml = alert["capXml"]
		alertId = alert["hubRecordKey"]
		
		if debug:
			print("storing alert {} for feed {}".format(alertId,feedid))

		temp = StringIO.StringIO(capxml.encode('utf-8'))
		capdom = ET.parse(temp)
		caproot = capdom.getroot()

		metadata = {  "link" : "https://alert-hub.s3.amazonaws.com/{}".format( alert["hubRecordKey"] ) }
		
		newitem=makeItem(caproot,metadata)
		items.append(newitem)
		
		#print(ET.tostring(newitem, pretty_print=True))

		
	# get RSS from S3 and parse it
	s3 = boto3.client('s3')
	
	s3keyold =  "{}/rss.xml".format(feedid)
	s3bucketold = "alert-feeds"
	if debug:
		print("downloading old feed {} from S3 bucket {}".format(s3keyold,s3bucketold))
	
	response = s3.get_object(Bucket=s3bucketold,Key=s3keyold)
	parser = ET.XMLParser(remove_blank_text=True)
	rssdom = ET.parse(response["Body"],parser)
	rssroot = rssdom.getroot()
	
	writeItemsToFeed(rssroot,items)
	
	with BytesIO() as outdata:
		rssdom.write(outdata, xml_declaration=True ,pretty_print=True, encoding="UTF-8")
		outdata.seek(0)
		
		s3key = "{}/rss.xml".format(feedid)
		s3bucket = 'alert-feeds'
		if debug:
			print("writing back updated RSS feed to {} {}".format(s3bucket,s3key))
		s3.put_object(Bucket=s3bucket,Key=s3key,ACL='public-read',ContentType="application/rss+xml",Body=outdata.read())	


def lambda_handler(event, context):

	rssfeedupdates = {}
	feedmetadata = {}
	
	records = event['Records']
	
	if debug:
		print("start kinesis processing of {} records".format( str(len(records)) ))


	# we group the alerts by feed 
	for record in records:
		#Kinesis data is base64 encoded so decode here and parse the json
		message = json.loads(base64.b64decode(record["kinesis"]["data"])) 
		
		alert = message["alert"]
		subscription = message["subscription"]
		
		feedinfo = { "id" : subscription["subscriptionId"] , "url" : subscription["subscriptionUrl"] }
	
		#kinesis info
		eventid=record["eventID"]
	
		if debug:
			print("processing feedid:{}, eventID:{}".format(feedinfo["id"],eventid))

		if feedinfo["id"] in rssfeedupdates:
			rssfeedupdates[feedinfo["id"]]["alerts"].append(   alert )
		else: 
			rssfeedupdates[feedinfo["id"]] = { "feedinfo" : feedinfo ,  "alerts" : [ alert, ] }
			
	
	for feedid,feedupdate in rssfeedupdates.iteritems():
		updateRss(feedupdate)
		
