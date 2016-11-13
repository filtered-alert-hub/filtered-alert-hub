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
from sqlalchemy.pool import NullPool 
import requests 
import threading

exitFlag = 0

class myThread (threading.Thread):
	def __init__(self, threadID):
		threading.Thread.__init__(self)
		self.threadID = threadID
		
	def run(self):
		print("Starting " + self.name)
		processSource(self.threadID)
		print("Exiting " + self.name)




def processSource(threadID):

 
	r = db_engine.connect().execute("SELECT etag,modified from feedinfo where feedid=:feedid order by date DESC", {"feedid" : threadID }  ).fetchone()
	print(r)

db_engine = create_engine("sqlite:///feedfetcher.db", echo=False, 
  #connect_args={'check_same_thread':False}, 
  poolclass=NullPool  
 )
 


	
threads = []
for t in range(0,10):
	thread = myThread(t)
	thread.start()
	threads.append(thread)

for t in threads:
	t.join()
print("Exiting Main Thread")
		
