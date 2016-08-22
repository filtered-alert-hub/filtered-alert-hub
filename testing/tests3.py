from __future__ import print_function

import json
import urllib
import boto3
from io import BytesIO
from lxml import etree as ET


print('Loading function')



s3 = boto3.client('s3')
response = s3.get_object(Bucket="alert-feeds",Key="unfiltered/rss.xml")

parser = ET.XMLParser(remove_blank_text=True)
rssdom = ET.parse(response["Body"],parser)
rssroot = rssdom.getroot()

with BytesIO() as outdata:
	rssdom.write(outdata, xml_declaration=True ,pretty_print=True, encoding="UTF-8")
	outdata.seek(0)

	s3.put_object(Bucket="test-rss-output",Key="mytest-rss.xml",ACL='public-read',ContentType="application/rss+xml",Body=outdata.read())	

