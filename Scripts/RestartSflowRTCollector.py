#!/usr/bin/env python

import os
import sys
import requests
import json
from time import sleep
path = "/home/flowspec/sflow-rt"
sflowIP = '127.0.0.1'

def main():
	os.chdir( path )
	data = {"user": "flowspec",
		"host": "localhost",
		"password": "flowspec",
		"commands": "cd /home/flowspec/sflow-rt;  screen -dm bash start.sh"}
	command = "sshpass -p {password} ssh -o StrictHostKeyChecking=no {user}@{host} {commands}"
	os.system(command.format(**data))
	print ("\n\nStarting Sflow Collector ........\n\n\n")
	ipflow = {'keys':'agent,ipprotocol,ipsource,or:tcpsourceport:udpsourceport:icmptype,inputifindex,ipdestination,or:tcpdestinationport:udpdestinationport:icmpcode', 'value':'bytes'}
	intflow = {'keys':'agent,outputifindex,mplslabels','value':'bytes','t':'4','log':True}

	try:
		print ("\n\nProgramming Sflow Collector ........\n\n\n")
		while True:
			try:
				r=requests.put('http://%s:8008/flow/%s/json' % (sflowIP,'interface'),data=json.dumps(intflow))
				r=requests.put('http://%s:8008/flow/%s/json' % (sflowIP,'ipdest'),data=json.dumps(ipflow))
				False
				print ("\n\nDone! ........\n\n\n")
				print ("\n\nFlowspec Controller Running! ........\n\n\n")
				return
			except:
				pass
	except:
		pass
	exit(0)

if __name__ == "__main__":
	main()
