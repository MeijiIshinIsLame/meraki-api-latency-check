import requests
import json
import pprint
import sys
import time
import smtplib
from email.message import EmailMessage
from datetime import datetime
from zoneinfo import ZoneInfo
import os

api_key = os.environ["MERAKI_APIKEY"]
org_id = os.environ["MERAKI_ORGID"]

headers = {
	"Content-Type": "application/json",
	"Accept": "application/json",
	"X-Cisco-Meraki-API-Key" : api_key
}

def convert_time_to_hst(timestr):
	dt = datetime.fromisoformat(timestr.replace('Z', '+00:00')) # convert to UTC
	dt_hst = dt.astimezone(ZoneInfo("Pacific/Honolulu"))
	date_string = f'{dt_hst:%Y-%m-%d %H:%M:%S%z}'
	return date_string

def get_request(url, payload):
	# Send request and get response
	payload = json.dumps(payload)

	response = requests.request(
	   "GET", 
	   url,
	   headers=headers,
	   data = payload
	)
	return json.loads(response.text)



def get_router_sn(network_id):
	json_data = get_request(f"https://api.meraki.com/api/v1/organizations/{org_id}/networks/{network_id}/devices", None)

	router_sn = None
	for device in json_data:
		if device["model"] == "MX68W":
			router_sn = device["serial"]

	return router_sn

def get_packet_loss(network_id, router_sn):
	data = payload = {"ip": "8.8.8.8", "uplink": "wan1"}
	json_data = get_request(f"https://api.meraki.com/api/v1/organizations/{org_id}/networks/{network_id}/devices/{router_sn}/lossAndLatencyHistory", data)
	return json_data


def send_alert_email(msg):
	mailserver = smtplib.SMTP('smtp.office365.com',587)
	mailserver.ehlo()
	mailserver.starttls()
	mailserver.login('redacted', os.environ["MERAKI_EMAIL_ALERT_PASSWORD"])
	#Adding a newline before the body text fixes the missing message body
	senders = 'redacted'
	recievers = ['redacted']
	mailserver.sendmail(senders, recievers, msg.as_string())
	mailserver.quit()


def check_latency_and_email(data):
	j = 0
	for i in data:
		print(i)
		if i['lossPercent'] is not None and float(i['lossPercent']) > 25.0:
			j+=1

	if j >= 2:
		print("sending alert!")
		formatted_data = ""
		for entry in data:
			entry['startTs'] = convert_time_to_hst(entry['startTs'])
			entry['endTs'] = convert_time_to_hst(entry['endTs'])
			formatted_entry = str(entry) + "\n"
			formatted_data += formatted_entry
		subject = "ALERT: Hilton packet loss over 25%!!"
		msg = EmailMessage()
		msg.set_content(f'Hilton appliance packet loss is over 25%\n\n{formatted_data}')
		msg['Subject'] = subject
		msg['From'] = "redacted"
		msg['To'] = "redacted"
		send_alert_email(msg)
		return True
	return False

hilton_sn = get_router_sn("L_634444597505860664")

while True:
	has_latency = check_latency_and_email(get_packet_loss("redacted", hilton_sn)[-10:])
	if has_latency:
		print("next email in 1 hour")
		time.sleep(3600) # 1 hour
	else:
		time.sleep(600) #10 minutes