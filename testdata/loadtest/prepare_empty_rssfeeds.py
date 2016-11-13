import io
import os  
import json
from datetime import datetime,date,time
import boto3
try:
	from BytesIO import BytesIO
except ImportError:
	from io import BytesIO


s3 = boto3.client('s3')
bucket = 'test-rss-output'

for subscription in os.listdir('subscriptions'):
	
	with open("subscriptions\{}".format(subscription)) as s_data:
		sub = json.load(s_data)
		sub = sub["subscription"]

		feed_data = open("rss_empty.xml").read()
		
		feed_data=feed_data.replace('#ID#',sub["subscriptionId"] )
		feed_data=feed_data.replace('#TITLE#',sub["subscriptionName"] )
		feed_data=feed_data.replace('#DESCRIPTION#',sub["subscriptionName"] )

		timenow = datetime.utcnow()
		pubdate =  "{} GMT".format(timenow.strftime("%a, %d %b %Y %H:%M:%S %z")) 
		dcdate = "{}Z".format(timenow.isoformat())

		
		feed_data=feed_data.replace('#LANGUAGE#',  sub["languageOnly"] if sub["languageOnly"] else "all"   )
		feed_data=feed_data.replace('#PUBDATE#',  pubdate )
		feed_data=feed_data.replace('#DCDATE#',   dcdate )
	
		bio = BytesIO(feed_data.encode("UTF-8"))
		bio.seek(0)

		key = "{}/rss.xml".format(sub["subscriptionId"])
		
		s3.put_object(Bucket=bucket,Key=key,ACL='public-read',ContentType="application/rss+xml",Body=bio.read())	

				