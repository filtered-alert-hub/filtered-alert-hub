import feedparser
import json
import sqlite3
import sys 
import urllib
from urllib.parse import urlparse
import boto3
import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.pool import StaticPool
import requests 
import threading

exitFlag = 0

class myThread (threading.Thread):
	def __init__(self, threadID, name, source, db_engine):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.source = source
		self.name = name
		self.db_engine = db_engine
		
	def run(self):
		print("Starting " + self.name)
		processSource(self.name,self.source,self.db_engine)
		print("Exiting " + self.name)


def processItems(threadName,items,feedid,db_engine):

	httpsession = requests.Session()
	haderror = False
	s3 = boto3.client("s3")

	for item in items:
		id = item["id"]
		try:
			mod = item["modified"] 
		except KeyError:
			try:
				mod = item["pubDate"]
			except KeyError:
				mod = "" #TODO: what's the right behaviour here
		
		link = item["link"]
		
		params = { "feedid" : feedid ,"itemid" : id ,"date" : mod }
		if not db_engine.connect().execute("SELECT * FROM receiveditems WHERE feedid=:feedid AND itemid=:itemid AND date=:date", params ).fetchone():
			if debug: print("processing item {} {} {}".format(id,mod,link))
			
			try:
				inputBucketName = "alert-hub-input-t"
				inputRecordKey = "{}{}".format(feedid,urlparse(link).path)
				capXML =  httpsession.get(link).text #TODO: need some protection against too large files..
				if debug: print("received {} from {}".format(id,link))
				
				s3.put_object(Bucket=inputBucketName,Key=inputRecordKey,ACL='private',ContentType="text/xml",Body=capXML)	
				if debug: print("stored {} in s3: {}".format(id,inputRecordKey))

				with db_engine.begin() as conn:
					conn.execute("INSERT INTO receiveditems (feedid, itemid, date) VALUES (:feedid,:itemid,:date)", params )

			except Exception as e:
				print("problem processing {} {}: {}".format(feedid,id,e))
				haderror=True
		
		if exitFlag:
			threadName.exit()
		
	return haderror


def processSource(threadName,source,db_engine):

	source=source["source"]
	capAlertFeed = source["capAlertFeed"]
	feedid = "{}".format(source["sourceId"])
	
	if "http" not in capAlertFeed: 
		return False
	
	#session = Session()

	etag=None
	modified=None

	
	r = db_engine.connect().execute("SELECT etag,modified from feedinfo where feedid=:feedid order by date DESC", {"feedid" : feedid }  ).fetchone()
	if r:
		etag=r["etag"]
		modified=r["modified"]

	if debug: print("requesting {} with etag:{} modified:{}".format(capAlertFeed,etag,modified))
	f = feedparser.parse(capAlertFeed, etag=etag , modified=modified , request_headers = extraheaders )
	if debug: print("{} has {} entries".format(feedid,len(f.entries)))
	
	haderror = processItems(threadName,f.entries,feedid,db_engine)

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
		
	if not haderror and (newetag or newmodified):
		with db_engine.begin() as conn:
			conn.execute("DELETE FROM feedinfo where feedid=:feedid",{"feedid" : feedid} )
			if debug: print("storing {} {} {}".format(feedid,newetag,newmodified))
			conn.execute("INSERT INTO feedinfo(feedid,etag,modified,date) VALUES (:feedid,:etag,:modified,'datetime()') ", { "feedid": feedid ,"etag" : newetag ,"modified" : newmodified }  )

	return not haderror

debug=False

extraheaders = { 'Cache-control': 'max-age=60' }

feedparser.USER_AGENT = "WMO-Alert-Hub/1.0 +http://www.wmo.int/"

dbname = 'feedfetcher.db'

db_engine = create_engine("sqlite:///{}".format(dbname), echo=False, 
  connect_args={'check_same_thread':False}, 
  #poolclass=StaticPool 
 )

#Session = scoped_session(
#   sessionmaker(
#        autoflush=True,
#        autocommit=False,
#        bind=db_engine
#    )
#)

#session = Session()

with db_engine.connect() as conn:
	if conn.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='receiveditems' or name='feedinfo' ").fetchone()[0] < 2:
		print("creating DB")
		conn.execute('''CREATE TABLE receiveditems (feedid text, date text, itemid text)''')
		conn.execute('''CREATE TABLE feedinfo (feedid text, etag text, modified text , date text )''')
	
with open("alert-hub-sources-json.txt") as data:
	sources = json.load(data)
	
	
	threads = []
	for idx,source in enumerate(sources["sources"]):
		thread = myThread(idx, "Thread-{}".format(idx), source,db_engine)
		thread.start()
		threads.append(thread)

	for t in threads:
		t.join()
	print("Exiting Main Thread")
		
