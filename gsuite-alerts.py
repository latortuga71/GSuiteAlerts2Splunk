import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import requests
import datetime
from sys import exit
from time import sleep
import logging

logging.basicConfig(filename='/opt/gsuite-alerts.log',level=logging.INFO)

'''
	    scopes = ["https://www.googleapis.com/auth/apps.alerts"]
	    SERVICE_ACCOUNT_FILE = 'json creds'
	    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, subject="acount here", scopes=scopes)
	    service = build('alertcenter', 'v1beta1', credentials=credentials).alerts()
'''

#recent_alerts = service.list().execute().get("alerts", [])
#https://developers.google.com/resources/api-libraries/documentation/alertcenter/v1beta1/python/latest/alertcenter_v1beta1.alerts.html#list
#https://developers.google.com/admin-sdk/alertcenter/reference/filter-fields.html
#https://github.com/googleapis/google-api-python-client/issues/777
#filter = "createTime >= \"2018-04-05T00:00:00Z\""
# FILTER NEEDS TO BE IN STRING FORMAT THE WHOLE THING ESCAPE DOUBLE QUOTES


class AlertAPI(object):
	alert_id = None
	scopes = ["https://www.googleapis.com/auth/apps.alerts"]
	SERVICE_ACCOUNT_FILE = 'appcreds.json'
	credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, subject="account here", scopes=scopes)
	#service = build('alertcenter', 'v1beta1', credentials=credentials).alerts()



	def check_new_alerts(self):
		self.service = build('alertcenter', 'v1beta1', credentials=self.credentials).alerts()
		self.one_min_behind = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
		self.now = datetime.datetime.utcnow()
		self.time_filter_str1 = self.one_min_behind.isoformat().split(".")[0] + "Z"
		self.time_filter_str2 = self.now.isoformat().split(".")[0] + "Z"
		self.final_filter = "createTime >= \"{}\" AND createTime < \"{}\" ".format(self.time_filter_str1,self.time_filter_str2)
		logging.info(self.final_filter)
		orderfilter = "create_time asc"
		self.recent_alerts = self.service.list(orderBy=orderfilter,filter=self.final_filter).execute() #pageSize=2 filter=self.final_filter OR type=\"*\"
		#print(self.recent_alerts)
		if not self.recent_alerts:
			# write this to a log file eventually
			#print(self.recent_alerts)
			self.num_of_alerts = 0
		else:
			self.num_of_alerts = len(self.recent_alerts['alerts'])
			logging.info("Alerts found => {}".format(self.num_of_alerts))
			logging.info(self.recent_alerts)



	def post_to_splunk(self,payload):
		self.ready2post = {}
		self.ready2post['sourcetype'] = "gsuite_alerts_api"
		self.ready2post['event'] = payload
		self.finalpayload = json.dumps(self.ready2post,indent=2)
		self.headers = {"Authorization":"Splunk tokenhere ",
						"Content-type":"application/json"}
		resp = requests.post("splunk hec url",headers=self.headers,data=self.finalpayload)
		logging.info(resp)
		logging.info(resp.text)
		resp_dict = json.loads(resp.text)
		if resp_dict['text'] != "Success":
			logging.warning("Failed Posting to splunk")
		else:
			logging.info("Successfully Posted to splunk")




	def main(self):
		while True:
		    #self.check_new_alerts()
		    try:
		    	self.check_new_alerts()
		    except Exception as e:
		    	logging.warning("ERROR {}".format(e))
		    	sleep(60)
		    	continue

		    if self.num_of_alerts == 0:
		    	logging.info("No Alerts Found!")
		    	sleep(60)
		    	continue
		    else:
		    	if self.recent_alerts['alerts'][0]['alertId'] == self.alert_id:
		    		logging.info("Last Alert Posted ID is same as oldest pulled alert...")
		    		logging.info("Continue to top of loop until this is resolved")
		    		sleep(60)
		    		continue

		    	for x in range(0,self.num_of_alerts):
		    		#print(x)
		    		self.post_to_splunk(self.recent_alerts['alerts'][x])
		    		if x + 1 == self.num_of_alerts:
		    			logging.info("attemping to get last alerts alert id")
		    			self.alert_id = self.recent_alerts['alerts'][x]['alertId']
		    logging.info("below is last alerts alert id")
		    logging.info(self.alert_id)
		    logging.info("done sleeping running loop again... checking for new alerts")
		    sleep(60)


if __name__ == '__main__':
    AlertAPI().main()