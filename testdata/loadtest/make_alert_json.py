import io
import os  
import json


for fn in os.listdir('alerts'):
	xml = open("alerts\{}".format(fn)).read().replace("\n","")

	with open('sns_test_skel.txt') as json_data:
		d = json.load(json_data)
		d["alert"]["capXml"] = xml
		
		newname = fn.replace(".xml",".json")
		with open("alerts\{}".format(newname),"w" ) as outfile:
			json.dump(d, outfile,indent=4, sort_keys=False)

			