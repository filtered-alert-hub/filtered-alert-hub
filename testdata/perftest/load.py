import json
import psycopg2

try:
	conn = psycopg2.connect("dbname='wahdb' user='wah_db_user' host='wah-database.cg46hbeal28c.eu-west-1.rds.amazonaws.com' password='wahpostgres'")
	cur = conn.cursor()
	cur.execute(""" DELETE from subscriptions """)
except:
	print("I am unable to connect to the database")
	sys.exit(1)

with open('C:\\Users\\Timo\\Documents\\aws\\alert-hub-filter\\testing\\all-subscriptions.json') as json_data:
	subscriptions = json.load(json_data)

	processed = {}
	
	for s in subscriptions["subscriptions"]:
		s=s["subscription"]
		print(s["subscriptionId"])
		
		if s["subscriptionId"] in processed:
			print("{} duplicate".format(s["subscriptionId"]))
			continue;
		
		mycoords=s["areaFilter"]["polygonCoordinates"] if not isinstance(s["areaFilter"]["polygonCoordinates"], str) else json.loads(s["areaFilter"]["polygonCoordinates"])
		coordinates = [ "{} {}".format(item[0],item[1]) for item in mycoords ]
	
		
		
		sql = """ INSERT INTO subscriptions(subscriptionId,subscriptionName, subscriptionUrl, languageOnly ,highPriorityOnly, officialOnly , 
		xPathFilterId , xPathFilter,areaFilterId,circleCenterRadius,feed_rss_xml,geom) VALUES 
		( %(subscriptionId)s, %(subscriptionName)s, %(subscriptionUrl)s,%(languageOnly)s,%(highPriorityOnly)s,%(officialOnly)s,%(xPathFilterId)s,
		%(xPathFilter)s,%(areaFilterId)s,%(circleCenterRadius)s,%(feed-rss-xml)s, {} ) """
		
		sql = sql.format(  'ST_GeomFromText(%(geoms)s,4326)' if  len(coordinates) > 0 else 'NULL'  )
		
		
		s["geoms"] = "POLYGON((" + ",".join(coordinates) + "))"
		print(s["geoms"])
		
		s["circleCenterRadius"]=  s["areaFilter"]["circleCenterRadius"] if s["areaFilter"]["circleCenterRadius"] not in ("none","") else None 
		
		cur.execute(sql, s )
		
		processed[s["subscriptionId"]]=True
		
conn.commit()
cur.close()
conn.close()