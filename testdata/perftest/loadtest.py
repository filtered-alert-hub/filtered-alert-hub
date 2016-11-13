from __future__ import print_function

from os import listdir
from os.path import isfile, join
from lxml import etree as ET
import stopwatch

import json
import psycopg2

def loadandvalidateCAP(capXML):
	
	

	if "urn:oasis:names:tc:emergency:cap:1.1" in capXML:
		capschema = "xsds/cap1-1.xsd"
		namespace = "urn:oasis:names:tc:emergency:cap:1.1"
	elif "urn:oasis:names:tc:emergency:cap:1.2" in capXML:
		capschema = "xsds/cap1-2.xsd"
		namespace = "urn:oasis:names:tc:emergency:cap:1.2"
	else:
		raise Exception("unknown schema: {}".format( capXML[0:100] ))
   
	
	doc = ET.fromstring(capXML)
	
	return [namespace,doc]



try:
	#conn = psycopg2.connect("dbname='wahdb' user='wah_db_user' host='wah-database.cg46hbeal28c.eu-west-1.rds.amazonaws.com' password='wahpostgres'")
	#cur = conn.cursor()
	pass
except:
	print("I am unable to connect to the database")
	sys.exit(1)

mypath="..\\..\\test\\capAlertTestAreas\\"
onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]


out = {}

for file in onlyfiles:
	with open(join(mypath, file)) as myfile:
		
		with stopwatch.Stopwatch() as sw:
			[namespace,doc] = loadandvalidateCAP(myfile.read())
			
			namespaces = {'cap': namespace }

			identifier = doc.xpath("//cap:identifier/text()", namespaces=namespaces)[0]
			
			coords = doc.xpath("//cap:polygon/text()", namespaces=namespaces)[0]
			coords = coords.split()
			coords = [ coord.split(',') for coord in coords ]
			coords = [ (item[1],item[0]) for item in coords ] # reverse coordinates
			
			coordinates = [ "{} {}".format(item[0],item[1]) for item in coords ]

			#problemcoords = [ item for item in coords if float(item[0])>180 or float(item[0]) < -180 or float(item[1]) < -90 or float(item[1])>90 ]
			
			out[identifier] = coordinates
			continue
			
			#SELECT ST_GeomFromText('LINESTRING(-71.160281 42.258729,-71.160837 42.259113,-71.161144 42.25932)',4269);
			
			s = {}
			s["geoms"] = "POLYGON((" + ",".join(coordinates) + "))"

			sql = """ SELECT subscriptionId from subscriptions WHERE ST_Intersects( ST_GeomFromText(%(geoms)s,4326) ,  geom  )   """
			
			cur.execute(sql,s)
			rows = cur.fetchall()
			for row in rows:
				print("{} matched with {}".format(file,row[0]))
			if not rows:
				print("{} did not match at all".format(file))
			
		print(sw.total_run_time)

with open("coords.json",'w') as out_json:
	json.dump(out,out_json)