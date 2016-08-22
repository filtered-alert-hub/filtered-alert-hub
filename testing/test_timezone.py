from datetime import datetime,date,time
import dateutil
import dateutil.parser



time="2016-08-08T19:53:00-04:00"
time2="2016-08-08T19:53:00-01:00"
time3="2016-08-08T19:53:00+01:00"

times = [time,time2,time3, "2016-08-08T23:53:00-04:00", "2016-08-08T23:53:00" ]


for t in times:

	alerttime = dateutil.parser.parse(t)

	print(alerttime)
	print(alerttime.utcoffset())
	
	timenew =  (alerttime - alerttime.utcoffset()).replace(tzinfo=None) if alerttime.utcoffset() else alerttime
	
	print(timenew)
	print("====")
