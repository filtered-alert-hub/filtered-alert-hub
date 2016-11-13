import json
import psycopg2
import datetime
import requests
import sys

def match_PG(coords,cur):

	try:
		conn = psycopg2.connect("dbname='wahdb' user='wah_db_user' host='wah-database.cg46hbeal28c.eu-west-1.rds.amazonaws.com' port='5432' password='wahpostgres'  connect_timeout=10")
		cur = conn.cursor()
	except Exception as e:
		print("I am unable to connect to the database ({})".format(e))
		sys.exit(1)


	s = {}
	s["geoms"] = "POLYGON((" + ",".join(coords) + "))"

	sql = """ SELECT subscriptionId from subscriptions WHERE ST_Intersects( ST_GeomFromText(%(geoms)s,4326) ,  geom  )   """
			
	cur.execute(sql,s)
	rows = []
	for res in cur.fetchall():
		rows.append(res[0])
	
	return rows

def match_ES(coords,session):

	session = requests.Session()

	
	coords = [ item.split() for item in coords ] 
	coords = [ [ float(item[0]) , float(item[1]) ] for item in coords ] 

	data = {      "from":0,
                         "size":1000,
                         "query":{
                           "bool": {
                             "must": {
                               "match_all": {}
                             },
                             "filter": {
                                 "geo_shape": {
                                   "subshape": {
                                     "shape": {
										  "type": "polygon",
										  "coordinates" : [ coords ]
										},
                                     "relation":'intersects'
                                   }
                                 }
                               }
                             }
                           },
                           "sort":{
                             "recid":{"order":'asc'}
                           }
	}

	
	r = session.post('http://wah.semweb.co/es/_search', json =  data )

	ret = []
	if r.status_code == 200:
		response = json.loads( r.text )
		if "timed_out" in response and not response["timed_out"]:
			for hit in response["hits"]["hits"]:
				ret.append(hit["_id"])
	
	#print(r.text)
	return ret
	

def lambda_handler(event, context):

	#print("incoming {}".format(event))

	outerstarttime = datetime.datetime.now()

	if 'Records' in event:
		message = json.loads(event["Records"][0]["Sns"]["Message"])
		#print("records mode.. type:{}".format(message["type"]))
	else:
		message = event
		#print("other mode.. type:{}".format(event["type"]))
		
	#print(message)

	alerts = message["alerts"]
	pg = message["type"] == "pg" 
	factor = message["factor"] if  "factor" in message else 1
		
	print("processing with factor {}".format(factor))	
	
	cur = None

	i=0
	j=0
	res = { 'alerts' : [] }
	while j<factor :
		for uid,coords in alerts.items():
			#print("processing {}".format(uid))
			starttime = datetime.datetime.now()
			
			if pg:
				matches = match_PG(coords,cur)
			else:
				matches = match_ES(coords,cur)
				
			endtime = datetime.datetime.now()
			timing = (endtime - starttime).total_seconds()
			
			if not matches:
				#print("{} did not match at all".format(uid))
				res["alerts"].append(  { 'alert' : uid, 'status' : 'nomatch' , 'timing' : timing  } )
			else:
				res["alerts"].append(  { 'alert' : uid, 'status' : 'match' , 'timing' : timing ,  'matches' : matches  } )

			i=i+1
		j=j+1
		
		#if i==3:
		#	break
		
	outerendtime = datetime.datetime.now()
	res["timing"] = (outerendtime - outerstarttime).total_seconds()
	res["count"] = i
	print("finished.. type: {} nr_records: {} overall_time: {}".format( "PG" if pg else "ES" ,i,res["timing"]))
	
	return res