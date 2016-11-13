import io
import os  
import json


for fnalert in os.listdir('alerts\json'):
	
	with open("alerts\json\{}".format(fnalert)) as json_data:
		alert = json.load(json_data)
		alert["alert"]["hubRecordKey"] = fnalert
	
		for fnsub in os.listdir('subscriptions'):
			
			with open("subscriptions\{}".format(fnsub)) as sub_data:
				sub = json.load(sub_data)
				
				mergefname="{}-_-{}".format(fnalert.replace('.json',''),fnsub.replace('.txt',''));
				#print(mergefname)
				
				d = { "subscription" : sub["subscription"] , "alert" : alert["alert"]  }
				
				
				with open("alertsubmerge\{}.json".format(mergefname),"w") as merge_data:
					json.dump(d, merge_data,indent=4, sort_keys=False)
	
	

			