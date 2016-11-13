from lxml import etree as ET
import io,os,sys,re
import json
import boto3
from pprint import pprint
import urllib2
import StringIO

data = urllib2.urlopen("http://www.google.com").read(20000) # read only 20 000 chars
data = data.split("\n") # then split it into lines


datadir = "C:\\Users\\Timo\\Documents\\aws\\test\\loadtest\\subscriptions"
xslt = ET.parse("extract-guids.xslt")

res = {}

for file in os.listdir(datadir):

	filepath = 	os.path.realpath(os.path.join(datadir,file))
	with open(filepath) as sub_data:
		sub = json.load(sub_data)
		
		url = sub["subscription"]["subscriptionUrl"]
		id = sub["subscription"]["subscriptionId"]
		print(url)

		dom = ET.parse(urllib2.urlopen(url))
		transform = ET.XSLT(xslt)
		newdom = transform(dom)
		root = newdom.getroot()
		
		for guid in root.findall('guid'):
			m = re.match(r'(.*)-([0-9]+)', guid.text)
			alertid = m.group(1)
			alertseq = int(m.group(2))
			
			#print("{} and {}".format(alertid,alertseq))
			
			if id not in res: res[id] = {}
			if alertid not in res[id]: res[id][alertid] = []
			res[id][alertid].append(alertseq)
		
		#print(ET.tostring(newdom, pretty_print=True))

#print(res)

y = range(1,100)

for subid,content in res.items():
	print("{}".format(subid))
	for alertid,seqs in content.items():
		missing = [item for item in seqs if item not in y]
		print("\t{}: {} ({})".format(alertid,str(len(seqs)), ",".join(sorted(missing)) ))