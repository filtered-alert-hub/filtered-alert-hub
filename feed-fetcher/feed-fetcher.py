import feedparser
import json
import sqlite3
import sys 
import urllib
from urllib.parse import urlparse
import boto3

debug=True

extraheaders = { 'Cache-control': 'max-age=60' }

dbname = 'feedfetcher.db'
conn = sqlite3.connect(dbname)
conn.row_factory = sqlite3.Row

c = conn.cursor()

if c.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='receiveditems' or name='feedinfo' ").fetchone()[0] < 2:
	print("creating DB")
	c.execute('''CREATE TABLE receiveditems (feedid text, date text, itemid text)''')
	c.execute('''CREATE TABLE feedinfo (feedid text, etag text, modified text , date text )''')
	conn.commit()
	
	
with open("alert-hub-sources-json.txt") as data:
	sources = json.load(data)
	
	s3 = boto3.client("s3")
	
	for source in sources["sources"]:
		source=source["source"]
		capAlertFeed = source["capAlertFeed"]
		feedid = source["sourceId"]
		
		if "http" not in capAlertFeed: continue
		

		etag=None
		modified=None
		r = c.execute("SELECT etag,modified from feedinfo where feedid=? order by date DESC", (feedid,) ).fetchone()
		if r:
			etag=r["etag"]
			modified=r["modified"]
		
		if debug: print("requesting {} with etag:{} modified:{}".format(capAlertFeed,etag,modified))
		f = feedparser.parse(capAlertFeed, etag=etag , modified=modified , request_headers = extraheaders )
		if debug: print("{} has {} entries".format(feedid,len(f.entries)))
		
		for item in f.entries:
			id = item["id"]
			try:
				mod = item["modified"] 
			except KeyError:
				try:
					mod = item["pubDate"]
				except KeyError:
					mod = None #TODO: what's the right behaviour here
			
			link = item["link"]
			
			if not c.execute("SELECT * FROM receiveditems WHERE feedid=? AND itemid=? AND date=?",(feedid,id,mod)).fetchone():
				if debug: print("processing item {} {} {}".format(id,mod,link))
				
				try:
					inputBucketName = "alert-hub-input-t"
					inputRecordKey = "{}{}".format(feedid,urlparse(link).path)
					capXML = urllib.request.urlopen(link).read() #TODO: need some protection against too large files..
					if debug: print("received {} from {}".format(id,link))
					
					s3.put_object(Bucket=inputBucketName,Key=inputRecordKey,ACL='private',ContentType="text/xml",Body=capXML)	
					if debug: print("stored {} in s3: {}".format(id,inputRecordKey))
				
					c.execute("INSERT INTO receiveditems (feedid, itemid, date) VALUES (?,?,?)", (feedid,id,mod) )
					conn.commit()

				except Exception as e:
					print("problem processing {} {}: {}".format(feedid,id, e))


		# store the feedinfo (etag and modified) in DB to avoid repeated fetching
		newetag=None
		newmodified=None
		try:
			newetag=f.etag
		except AttributeError:
			pass
		try:
			newmodified=f.modified
		except AttributeError:
			pass
		
		c.execute("DELETE FROM feedinfo where feedid=?",(feedid,))
		if newetag or newmodified:
			if debug: print("storing {} {} {}".format(feedid,newetag,newmodified))
			c.execute("INSERT INTO feedinfo(feedid,etag,modified,date) VALUES (?,?,?,'datetime()') ", (feedid,newetag,newmodified ) )

		
conn.commit()
conn.close()