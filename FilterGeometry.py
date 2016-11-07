import os
import json
from ctypes import cdll
import boto3

#Set environment variables and load shared libraries
path = os.path.dirname(os.path.realpath(__file__))

testing = False
debug = True

if not testing:
	lib1 = cdll.LoadLibrary(os.path.join(path, 'local/lib/libgeos-3.6.0.so'))
	lib3 = cdll.LoadLibrary(os.path.join(path, 'local/lib/libgeos_c.so'))
	lib2 = cdll.LoadLibrary(os.path.join(path, 'local/lib/libgeos_c.so.1.10.0'))	

from shapely.geometry import Polygon

def lambda_handler(event, context):

	#if debug:
		#print("incoming {}".format(json.dumps(event)))
	
	alerts = []
	
	if 'Records' in event: # sns processing
		for record in event['Records']:
			alerts.append( json.loads(record["Sns"]["Message"]) ) 
	else: # we get the alert directly
		alerts.append(event)
	
	
	if testing: 
		session = boto3.Session(profile_name='wah')
	else:
		session = boto3.Session()

	
	if testing:
		with open('testing/all-subscriptions.json') as data:
			subscriptions = json.load(data)
	else:  #get subscriptions from S3
		s3 = session.client("s3")
		response = s3.get_object(Bucket="alert-hub-subscriptions",Key="json")
		subscriptions = json.load(response["Body"])
		
	# pre-process subscriptions to have polygons and subcsription info available by ID
	subscriptionids = {}
	subscriptionpolygons = {}
	
	for s in subscriptions["subscriptions"]:
		s=s["subscription"]
		subscriptionids[s["subscriptionId"]]=s
		
		mycoords=s["areaFilter"]["polygonCoordinates"] if not isinstance(s["areaFilter"]["polygonCoordinates"], basestring) else json.loads(s["areaFilter"]["polygonCoordinates"])
		coordinates = [ (item[0],item[1]) for item in mycoords ]
	
		if len(coordinates) > 0:
			subscriptionpolygons[s["subscriptionId"] ] = Polygon(  coordinates  )

	# process alerts. 	
	for alert in alerts:
		polygons = []

		if debug:
			print("processing alert {}".format(alert["alert"]["hubRecordKey"]))

		# We first collect all the area polygons in an alert
		info = alert["alert"]["capJson"]["alert"]["info"]
		infos =  info if type(info) is list else [info]
		
		for info in infos:
			area = info["area"]
			areas = area if type(area) is list else [area]

			for area in areas:
				points = area["polygon"]["$"].split()
				coordinates = [ point.split(',') for point in points ]
				coordinates = [ (float(coordinate[0]),float(coordinate[1]))  for coordinate in coordinates  ]
				
				if len(coordinates) > 0:
					polygons.append( Polygon(coordinates) )
					
		if len(polygons) == 0: #if we found no polygons in the alert we do not process it. FIXME: is this ok with the specs?
			continue
			
		if debug:
			print("checking for intersections")

		# now we intersect with the subscriptions
		for id,polygon in subscriptionpolygons.items():
			for object in polygons:

				if polygon.intersects(object): # send alert if match and continue with next subscription

					topicArn = "arn:aws:sns:eu-west-1:381798314226:wah_post-geofilter";
					alert["subscription"] = subscriptionids[id]
					
					sns = session.client('sns')
					sns.publish(
						TopicArn = topicArn,
						Message = json.dumps(alert)
					)
					if debug:
						print("alert {} sent to {}".format(alert["alert"]["hubRecordKey"], id ))

					break
	if debug:
		print("done")
