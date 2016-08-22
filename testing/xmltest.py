#import xml.etree.ElementTree as ET
from lxml import etree

def checkPriority(root):
	namespaces = {'cap': 'urn:oasis:names:tc:emergency:cap:1.1'}

	passActualAlertPublic = "//cap:status='Actual' and (//cap:msgType='Alert' or //cap:msgType='Update') and //cap:scope='Public'"
	#passActualAlertPublic = "//cap:status='Actual'"
	
	if not root.xpath(passActualAlertPublic,namespaces=namespaces):
		print "not actually public"
		return False
			
	passHighPriority = "//cap:urgency[.='Immediate' or .='Expected'] and //cap:severity[.='Extreme' or .='Severe'] and //cap:certainty[.='Observed' or .='Likely']"
	if not root.xpath(passHighPriority,namespaces=namespaces):
		print "not actually high priority"
		return False
	
	blockUsWea = "//cap:parameter/cap:valueName[.='BLOCKCHANNEL']/../cap:value[.= 'CMAS' or .= 'EAS' or .= 'NWEM' or .= 'Public']"
	if root.xpath(blockUsWea,namespaces=namespaces):
		print "blocked by UsWea"
		return False
	
	return True


tree = etree.parse('../capAlertTestAreas/2016-03-10-10-53-13-217.xml')
root = tree.getroot()

print etree.tostring(root)

checkPriority(root)






