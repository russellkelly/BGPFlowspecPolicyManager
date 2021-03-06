#!/usr/bin/env python


import os
import re
import json
import requests
import ipaddress
try:
	import win_inet_pton
except:
	pass
import socket
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import threading
import yaml
try:
    import tkinter as tk
    import tkinter.ttk as ttk
except:
    import Tkinter as tk
    import ttk as ttk
try:
	from ScrolledText import ScrolledText
except:
	from tkinter.scrolledtext import ScrolledText

from multiprocessing import Process
from multiprocessing import Queue
try:
	from Queue import Empty, Full
except:
	from queue import Empty, Full
from multiprocessing import JoinableQueue
import copy
import schedule
import time
import sys
from datetime import datetime  
from datetime import timedelta  
from pprint import pprint as pp



## Initial Open TopologyVariable.yaml To populate Variables

script_dir = os.path.dirname(__file__)
rel_path = "TopologyVariables.yaml"
abs_file_path = os.path.join(script_dir, rel_path)
file=open(abs_file_path)
if sys.version_info[0] < 3:
	topo_vars = yaml.load(file.read(),Loader=yaml.FullLoader)
else:
	topo_vars = yaml.load(file.read(),Loader=yaml.FullLoader)
topo_vars['home_directory'] = os.path.dirname(os.path.realpath(__file__))
file.close()


## Derived Policy Manager Variables 


sflowIP=str(topo_vars['sflow_rt_ip'])
ExabgpIP=str(topo_vars['exabgp_ip'])
SflowMultiplier=int(topo_vars['SflowMultiplier'])
AppRunTimer=int(topo_vars['AppRunWaitTime'])
FlowPopUpRefreshInterval = int(topo_vars['FlowPopUpRefreshInterval'])
MaxSflowEntries=str(topo_vars['MaxSflowEntries'])
DeadSflowTimer=str(topo_vars['SflowDeadTimer'])
DeadFlowRemovalTimer=int(topo_vars['DeadSflowRemovalWaitTime'])
DeadFlowRemoval=str(topo_vars['DeadFlowRemoval'])


sflowrt_url = 'http://'+sflowIP+':'+str(topo_vars['sflow_rt_port'])
exabgpurl= 'http://'+ExabgpIP+':'+str(topo_vars['exabgp_port'])


ProtocolList = []					# Example Format: ProtocolList = [{'TCP':6},{'UDP':17}]
for entry in topo_vars['IPProtocol']:
	ProtocolList.append(entry)


NHVRFDict = {}
NHIPDict = {}
NHIP6Dict = {}
ListOfLERs = []
ConfiguredLERs = []

try:
	for Router in topo_vars['EdgeRouters']:
		ListOfLERs.append(Router['RouterID'])
except:
	pass
try:
	for Router in topo_vars['EdgeRouters']:
		NHIPDict[Router['RouterID']]=Router['IPNH']
except:
	pass
try:
	for Router in topo_vars['EdgeRouters']:
		NHIP6Dict[Router['RouterID']]=Router['IP6NH']
except:
	pass
try:
	for Router in topo_vars['EdgeRouters']:
		NHVRFDict[Router['RouterID']]=Router['VRF']
except:
	pass
	
PortList = []						# Example Format: PortList = ['TCP-80','UDP-53', 'TCP-445','TCP>1024','TCP<1024','UDP>1024','UDP<1024']
for entry in topo_vars['PortList']:
	PortList.append(entry)

ipflow = {'keys':'agent,or:ip6nexthdr:ipprotocol,or:ipsource:ip6source,or:tcpsourceport:udpsourceport:icmptype:icmp6type,inputifindex,or:ipdestination:ip6destination,or:tcpdestinationport:udpdestinationport:icmpcode:icmp6code', 'value':'bytes'}



# Start the server python processes afresh (used with Program switch or script)



def ProgramSflowrt():
	# program sFlow-RT to monitor LER uplinks
	try:
		print ("\n\nProgramming Sflow Collector ........\n\n\n")
		while True:
			try:
				r=requests.put('http://%s:8008/flow/%s/json' % (sflowIP,'ipdest'),data=json.dumps(ipflow))
				False
				print ("\n\nDone! ........\n\n\n")
				print ("\n\nFlowspec Controller Running! ........\n\n\n")
				return
			except:
				pass
	except:
		pass


def FindAndProgramDdosFlows(SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,ManualRouteQueue,ManualRouteDisplayQueue,UpdatePolicyQueue,SignalResetQueue,ExaBGPQueue):
	ExabgpAndQueueCalls = FindAndProgramDdosFlowsHelperClass()
	ListOfFlows = []
	DeadSflowList = []
	ListOfManualRoutesToRemove = []
	ManualRouteCopy = []
	TimeStampedFlowDict = {}
	FlowBandwidthDict = {}
	FlowActionDict = {}
	DefaultBandwidth = 0
	RateLimitPolicyUpdate = ['rate-limit', 0, [], []]
	RedirectNHPolicyUpdate = ['redirect next-hop', 0, [], []]
	RedirectVRFPolicyUpdate = ['redirect VRF', 0, [], []]
	_cached_stamp = 0
	TopologyVariables = abs_file_path
	sflowcount = 0
	deadflowcount = 0
	
	while True:
		try:
			ResetSignalled = ExabgpAndQueueCalls.SignalResetQueuePoll(SignalResetQueue)
			if ResetSignalled[0] == 'RESET SIGNALED':
				ListOfFlows = []
				ListOfManualRoutesToRemove = []
				ExabgpAndQueueCalls.ResetActiveFlowspecRoutes()
				ExabgpAndQueueCalls.ResetActiveManualFlowspecRoutes()
				FlowBandwidthDict = {}
				FlowActionDict = {}
				DeadSflowList = []
				TimeStampedFlowDict = {}
				DefaultBandwidth = 0
				DefaultAction = ''
				DefaultRateLimit = ''
				RateLimitPolicyUpdate = ['rate-limit', 0, [], [],'']
				RedirectNHPolicyUpdate = ['redirect next-hop', 0, [], []]
				RedirectVRFPolicyUpdate = ['redirect VRF', 0, [], []]
			else:
				pass
		except:
			pass
		try:
			ManualRoute = ExabgpAndQueueCalls.ManualRouteQueuePoll(ManualRouteQueue)
			
			# Removes all Manual Routes in ListOfManualRoutesToRemove
			if ManualRoute[0] == "DELETEALLMANUALROUTES":
				for ManualRoute in ListOfManualRoutesToRemove:
					ExabgpAndQueueCalls.ExaBgpWithdrawManualRoute(str(ManualRoute[0]),str(ManualRoute[1]),str(ManualRoute[2]),str(ManualRoute[3]),str(ManualRoute[4]),str(ManualRoute[5]),str(ManualRoute[6]),ExaBGPQueue)
			if sys.version_info[0] < 3:
				UnicodeSourceNetwork = make_unicode(ManualRoute[1])
				UnicodeDestinationNetwork = make_unicode(ManualRoute[2])
			elif sys.version_info[0] >= 3:
					unicode = str
					UnicodeSourceNetwork = ManualRoute[1]
					UnicodeDestinationNetwork = ManualRoute[2]
			if str(ManualRoute[7]) == 'redirect next-hop' :
				if is_valid_network(UnicodeSourceNetwork) and is_valid_network(UnicodeDestinationNetwork) and type_of_network(UnicodeSourceNetwork).version == 4:
					try:
						Action = 'redirect '+str(NHIPDict[str(ManualRoute[0])])
					except:
						pass
				elif is_valid_network(UnicodeSourceNetwork) and is_valid_network(UnicodeDestinationNetwork) and type_of_network(UnicodeSourceNetwork).version == 6:
					try:
						Action = 'redirect '+str(NHIP6Dict[str(ManualRoute[0])])
					except:
						pass
				else:
					pass
			elif str(ManualRoute[7]) == 'redirect VRF':
				Action = 'redirect '+str(NHVRFDict[str(ManualRoute[0])])
			else:
				# Only left with rate-limit so just take Manual[7] value
				Action = str(ManualRoute[7])
			if ManualRoute == None:
				pass
			elif [str(ManualRoute[0]),str(ManualRoute[3]),str(ManualRoute[1]),str(ManualRoute[4]),str(ManualRoute[2]),str(ManualRoute[5]),Action] in ListOfManualRoutesToRemove:
				pass
			else:
				if ManualRoute[6] == str(1):
					# First check if a rule with same source and destinations and ports is in the list.  If so remove it
					for entry in ListOfManualRoutesToRemove:
						if [str(entry[0]),str(entry[1]),str(entry[2]),str(entry[3]),str(entry[4]),str(entry[5])] == [str(ManualRoute[0]),str(ManualRoute[3]),str(ManualRoute[1]),str(ManualRoute[4]),str(ManualRoute[2]),str(ManualRoute[5])]:
							ExabgpAndQueueCalls.ExaBgpWithdrawManualRoute(str(entry[0]),str(entry[1]),str(entry[2]),str(entry[3]),str(entry[4]),str(entry[5]),str(entry[6]),ExaBGPQueue)
							ListOfManualRoutesToRemove.remove(entry)
							break
					try:
						ExabgpAndQueueCalls.ExaBgpAnnounceManualRoute(str(ManualRoute[0]),str(ManualRoute[3]),str(ManualRoute[1]),str(ManualRoute[4]),str(ManualRoute[2]),str(ManualRoute[5]),Action,ExaBGPQueue)
						ListOfManualRoutesToRemove.append([str(ManualRoute[0]),str(ManualRoute[3]),str(ManualRoute[1]),str(ManualRoute[4]),str(ManualRoute[2]),str(ManualRoute[5]),Action])
					except:
						pass
				if ManualRoute[6] == str(2):
					try:
						ExabgpAndQueueCalls.ExaBgpWithdrawManualRoute(str(ManualRoute[0]),str(ManualRoute[3]),str(ManualRoute[1]),str(ManualRoute[4]),str(ManualRoute[2]),str(ManualRoute[5]),Action,ExaBGPQueue)
						ListOfManualRoutesToRemove.pop([str(ManualRoute[0]),str(ManualRoute[3]),str(ManualRoute[1]),str(ManualRoute[4]),str(ManualRoute[2]),str(ManualRoute[5]),Action])
					except:
						pass
				else:
					pass
			
		except:
			pass

		try:
			NewPolicyUpdate = ExabgpAndQueueCalls.UpdatePolicyQueuePoll(UpdatePolicyQueue)
			if NewPolicyUpdate[0] == 'DefaultBandwidth:':
				DefaultBandwidth = float(NewPolicyUpdate[1])
				DefaultAction = str(NewPolicyUpdate[2])
				DefaultRateLimit = str(NewPolicyUpdate[3])
			if NewPolicyUpdate[0] == 'rate-limit':
				RateLimitPolicyUpdate = copy.deepcopy(NewPolicyUpdate)
			if NewPolicyUpdate[0] == 'redirect next-hop':
				RedirectNHPolicyUpdate = copy.deepcopy(NewPolicyUpdate)
			if NewPolicyUpdate[0] == 'redirect VRF':
				RedirectVRFPolicyUpdate = copy.deepcopy(NewPolicyUpdate)
		except:
			pass
		
		ListOfPolicyUpdates = [RedirectNHPolicyUpdate,RedirectVRFPolicyUpdate,RateLimitPolicyUpdate]
		SortedListOfPolicyUpdates = copy.deepcopy(Sort(ListOfPolicyUpdates))
		SortedListOfPolicyUpdates = [item for item in SortedListOfPolicyUpdates if item[1] != 0]
		

		#Min Value to Include in Sflow Collection (Just everything)
		MinValue = 0

		if sflowcount == 0 or sflowcount == (AppRunTimer*SflowMultiplier):
			###--("running sflow")
			try:
				session = requests.Session()
				retry = Retry(connect=3, backoff_factor=0.5)
				adapter = HTTPAdapter(max_retries=retry)
				session.mount('http://', adapter)
				session.mount('https://', adapter)
				try:
					r = session.get(str(sflowrt_url)+'/activeflows/ALL/ipdest/json?maxFlows='+str(MaxSflowEntries)+'&minValue='+str(MinValue))
				except:
					pass
			except requests.exceptions.ConnectionError:
				r.status_code = "Connection refused"
			rawflows = r.json()
			sflowcount = 0
		try:
			for i in rawflows:
				Data = str(i["key"])
				DataList = Data.split(",")
				bw = int(int(i["value"]*8/1000/1000))
				FlowBandwidthDict[str(DataList)]=str('('+str(bw)+' Mbps)')
				if SortedListOfPolicyUpdates != [] and str(DataList[0]) in ListOfLERs:
					for entry in SortedListOfPolicyUpdates:
						if entry[0] == 'rate-limit':
							CurrentAction = 'rate-limit ' +str(entry[4])
						elif entry[0] == 'redirect next-hop':
							if is_valid_ipv4_address(str(DataList[2])):
								try:
									CurrentAction = 'redirect '+str(NHIPDict.get(str(DataList[0])))
								except:
									pass
							if is_valid_ipv6_address(str(DataList[2])):
								try:
									CurrentAction = 'redirect '+str(NHIP6Dict.get(str(DataList[0])))
								except:
									pass
						elif entry[0] == 'redirect VRF':
							try:
								CurrentAction = 'redirect '+str(NHVRFDict.get(str(DataList[0])))
							except:
								pass
						PolicyBandwidth = entry[1]
						CurrentConfiguredSourceProtocolPortList = GetPortList(entry[2])
						CurrentConfiguredDestinationProtocolPortList = GetPortList(entry[3])
						try:
							if CheckPolicy(DataList,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList,CurrentAction,PolicyBandwidth,bw):
								###--("Flow Passed the Check (returned true) and is about to be Programmed")
								ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction,ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
								
								# Add a timestamped version of the DataList
								if not TimeStampedFlowDict.get(str(DataList)):
									TimeStampedFlowDict[str(DataList)]=datetime.now()
									###--("Datalist not in TimeStamped Flow Dict so adding")
									
								if Data.split(",") in DeadSflowList:
									DeadSflowList.remove(Data.split(","))
									TimeStampedFlowDict[str(DataList)]=datetime.now()
									###--("must have been a dead flow, removing from dead flow and adding to TimestampedFlowDict now that it's ALIVE!")
								
								if TimeStampedFlowDict.get(str(DataList)) and TimeStampedFlowDict.get(str(DataList)) > datetime.now() - timedelta(seconds=int(DeadSflowTimer)):
									###--("refreshing entry")
									TimeStampedFlowDict.pop(str(DataList))
									TimeStampedFlowDict[str(DataList)]=datetime.now()
								
								break
							else:
								try: ## Try adding with default policy values (pass if none)
									if DefaultAction == 'rate-limit':
										CurrentAction = CurrentAction = 'rate-limit ' +str(DefaultRateLimit)
									elif DefaultAction == 'redirect next-hop':
										try:
											CurrentAction = 'redirect '+str(NHIPDict.get(str(DataList[0])))
										except:
											pass
									elif DefaultAction == 'redirect VRF':
										try:
											CurrentAction = 'redirect '+str(NHVRFDict.get(str(DataList[0])))
										except:
											pass
									if bw > DefaultBandwidth and DefaultBandwidth != 0 and SortedListOfPolicyUpdates.index(entry) == int(len(SortedListOfPolicyUpdates)-1) and 'None' not in CurrentAction:
										ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction,ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
										###-- ("Checked all Policies For Flow, Doesn't exist yet, so add it using Default Policy")
										
										# Add a timestamped version of the DataList
										if not TimeStampedFlowDict.get(str(DataList)):
											TimeStampedFlowDict[str(DataList)]=datetime.now()
											###--("Datalist not in TimeStamped Flow Dict so adding")
										if Data.split(",") in DeadSflowList:
											DeadSflowList.remove(Data.split(","))
											TimeStampedFlowDict[str(DataList)]=datetime.now()
											###--("must have been a dead flow, removing from dead flow and adding to TimestampedFlowDict now that it's ALIVE!")
										if TimeStampedFlowDict.get(str(DataList)) and TimeStampedFlowDict.get(str(DataList)) > datetime.now() - timedelta(seconds=int(DeadSflowTimer)):
											###-- ("refreshing entry")
											TimeStampedFlowDict.pop(str(DataList))
											TimeStampedFlowDict[str(DataList)]=datetime.now()
										
								
										break
								except:
									pass
						except:
							pass

							# This means the Source Port or Destination port is not in this policy (or we got a False)
							
						try:
							if not CheckPolicy(DataList,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList,CurrentAction,PolicyBandwidth,bw) and str(DataList) in FlowActionDict.keys() and SortedListOfPolicyUpdates.index(entry) == int(len(SortedListOfPolicyUpdates)-1):
								###--("Returned False  - No Source or Destination Port in the source or destination portlist - removing the flow")
								ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
								FlowActionDict.pop(str(DataList),None)
								ListOfFlows.remove(DataList)
								TimeStampedFlowDict.pop(str(DataList),None)
								DeadSflowList.remove(DataList)
								break
						except:
							pass
						
						try:
						
							if bw < DefaultBandwidth:
								ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
								FlowActionDict.pop(str(DataList),None)
								ListOfFlows.remove(DataList)
								TimeStampedFlowDict.pop(str(DataList),None)
								DeadSflowList.remove(DataList)
								###--("No flow policy but default BW > flow bw - have to remove flows.")
						except:
							pass

		# No Flow Policy Set. Just use default BW Policy
		
				if SortedListOfPolicyUpdates == [] and DefaultBandwidth != 0 and str(DataList[0]) in ListOfLERs:
					###--("Hit the default")
					try:
						if DefaultAction == 'rate-limit':
							CurrentAction = CurrentAction = 'rate-limit ' +str(DefaultRateLimit)
						elif DefaultAction == 'redirect next-hop':
							if is_valid_ipv4_address(str(DataList[2])):
								try:
									CurrentAction = 'redirect '+str(NHIPDict.get(str(DataList[0])))
								except:
									pass
							if is_valid_ipv6_address(str(DataList[2])):
								try:
									CurrentAction = 'redirect '+str(NHIP6Dict.get(str(DataList[0])))
								except:
									pass
						elif DefaultAction == 'redirect VRF':
							try:
								CurrentAction = 'redirect '+str(NHVRFDict.get(str(DataList[0])))
							except:
								pass
						PolicyBandwidth = DefaultBandwidth
						if bw > DefaultBandwidth:
							if 'None' not in CurrentAction:
								try:
									CurrentConfiguredSourceProtocolPortList = GetPortList(entry[2])
								except:
									CurrentConfiguredSourceProtocolPortList = []
								try:
									CurrentConfiguredDestinationProtocolPortList = GetPortList(entry[3])
								except:
									CurrentConfiguredDestinationProtocolPortList = []
								###--("BW > default, and there is an action.  So program the flow (using local function ProgramFlowPolicies")
								ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction,ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
								
								# Add a timestamped version of the DataList
								if not TimeStampedFlowDict.get(str(DataList)):
									TimeStampedFlowDict[str(DataList)]=datetime.now()
									###--("Datalist not in TimeStamped Flow Dict so adding")
								if Data.split(",") in DeadSflowList:
									DeadSflowList.remove(Data.split(","))
									TimeStampedFlowDict[str(DataList)]=datetime.now()
									###--("must have been a dead flow, removing from dead flow and adding to TimestampedFlowDict now that it's ALIVE!")
								if TimeStampedFlowDict.get(str(DataList)) and TimeStampedFlowDict.get(str(DataList)) > datetime.now() - timedelta(seconds=int(DeadSflowTimer)):
									###-- ("refreshing entry")
									TimeStampedFlowDict.pop(str(DataList))
									TimeStampedFlowDict[str(DataList)]=datetime.now()
						
						if DataList in ListOfFlows and 'None' in CurrentAction:
							ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
							FlowActionDict.pop(str(DataList),None)
							ListOfFlows.remove(DataList)
							TimeStampedFlowDict.pop(str(DataList),None)
							DeadSflowList.remove(DataList)
							###--("Theres a None I have to remove - Use ExabgpWithdraw so the activeflowlist is updated")
							
						if DataList in ListOfFlows and bw < DefaultBandwidth:
							ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
							FlowActionDict.pop(str(DataList),None)
							ListOfFlows.remove(DataList)
							TimeStampedFlowDict.pop(str(DataList),None)
							DeadSflowList.remove(DataList)
							###--("No flow policy but default BW > flow bw - have to remove flows. Use ExabgpWithdraw so the activeflowlist is updated")
					except:
						pass
				else:
					pass
				
			###--("Create the deadflow list")
			for entry in TimeStampedFlowDict.keys():
				try:
					if TimeStampedFlowDict.get(str(entry)) and TimeStampedFlowDict.get(str(entry)) < datetime.now() - timedelta(seconds=int(DeadSflowTimer)) :
						TimeStampedFlowDict.pop(str(entry), None)
						entry = entry.translate(None,"[] '")
						ListifiedEntry  = entry.split(",")
						if ListifiedEntry not in DeadSflowList:
							DeadSflowList.append(ListifiedEntry)
						else:
							###--(" already in deadflow")
							pass
				except:
					pass	
		except:
			pass

		# Remove Flows from the DeadFlowList

		if DeadFlowRemoval == str('True'):
			if deadflowcount >= (DeadFlowRemovalTimer):
				try:
					for Entry in DeadSflowList:
						try:
							ListOfFlows.remove(Entry)
							ExabgpAndQueueCalls.ExaBgpWithdraw(str(Entry[0]),str(Entry[1]),str(Entry[2]),str(Entry[3]),str(Entry[5]),str(Entry[6]),FlowActionDict.get(str(Entry)),ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
							FlowActionDict.pop(str(Entry),None)
						except:
							pass
						DeadSflowList.remove(Entry)
				except:
						pass
				deadflowcount = 0
				
		# Remove Flows from Topology Variables LERs that have Been Removed
		
		for DataList in ListOfFlows:
			if str(DataList[0]) not in ListOfLERs:
				ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
				FlowActionDict.pop(str(DataList),None)
				ListOfFlows.remove(DataList)
				

			
		# Else withdraw all the flows.
		
		if SortedListOfPolicyUpdates == [] and DefaultBandwidth == 0 and len(ListOfFlows) != 0:
			###-- ("Withdrawing all routes - No Policies at all matching.   All active routes will be withdrawn one by one")
			for DataList in ListOfFlows:
				ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
				FlowActionDict.pop(str(DataList),None)
				ListOfFlows.remove(DataList)
	
		# Send Lists for Printing in Main tkinter Window
		
		try:
			SflowQueue.get(0)	# Clear the Queue (otherwise it grows HUGE) - Will just send last entry now with put below
		except:
			pass
		ListOfFlowsCopy = copy.deepcopy(ListOfFlows)
		for entry in ListOfFlowsCopy:
			entry.append(FlowBandwidthDict.get(str(entry)))	
		SflowQueue.put(ListOfFlowsCopy)
		try:
			ManualRouteDisplayQueue.get(0)		# Clear the Queue (otherwise it grows HUGE) - Will just send last entry now with put below
		except:
			pass
		ManualRouteDisplayQueue.put(ExabgpAndQueueCalls.ReturnActiveManualFlowspecRoutes())
		try:
			FlowRouteQueueForQuit.get(0)		# Clear the Queue (otherwise it grows HUGE) - Will just send last entry now with put below
		except:
			pass
		FlowRouteQueueForQuit.put(ExabgpAndQueueCalls.ReturnActiveFlowspecRoutes())
		try:
			FlowRouteQueue.get(0)		# Clear the Queue (otherwise it grows HUGE) - Will just send last entry now with put below
		except:
			pass
		FlowRouteQueue.put(ExabgpAndQueueCalls.ReturnActiveFlowspecRoutes())
		stamp = os.stat(TopologyVariables).st_mtime
		if stamp != _cached_stamp: 			# Well the TopologyVariables File Changed
			_cached_stamp = stamp
			RenderTopologyVariables()
		deadflowcount += AppRunTimer
		sflowcount += AppRunTimer
		
		# Print the Application Variables and Active Data
		print ("\n\n\nApplication Variables and Data:")
		print ("===============================\n")
		print ("\nApplication Variables")
		print ("---------------------")
		print ("\nApplication Loop Time: "+str(AppRunTimer))
		print ("\nMax Number of Flows Being Monitored: "+str(MaxSflowEntries))
		print ("\nDead sFlow Age (seconds): "+str(DeadSflowTimer))
		print ("\nDead sFlow Wait Before Removal Time (seconds): "+str(DeadFlowRemovalTimer))
		print ("\nDead sFlow Removal 'True' or 'False': "+str(DeadFlowRemoval))
		print ("\nFlow PopUp Window Refresh Interval: "+str(FlowPopUpRefreshInterval))
		print ("\n\nLive Data")
		print ("----------")
		print ("Time stamped Dict Length: "+str(len(TimeStampedFlowDict)))
		print ("\nDead sFlow List Length: "+str(len(DeadSflowList)))
		print ("\nList of sFlows Length: "+str(len(ListOfFlows)))
		print ("\nFlow Action Dict Length: "+str(len(FlowActionDict)))
		
		time.sleep(AppRunTimer)
		
		
def make_unicode(input):
    if type(input) != unicode:
        input =  input.decode('utf-8')
        return input
    else:
        return input

def is_valid_ipv4_address(sourceipv4address):
	try:
		socket.inet_pton(socket.AF_INET, sourceipv4address)
	except AttributeError:  # no inet_pton here, sorry
		try:
			socket.inet_aton(sourceipv4address)
		except socket.error:
			return False
		return sourceipv4address.count('.') == 3
	except socket.error:  # not a valid address
		return False

	return True

def is_valid_ipv6_address(sourceipv6address):
	try:
		socket.inet_pton(socket.AF_INET6, sourceipv6address)
	except socket.error:  # not a valid address
		return False
	return True

def is_valid_network(sourcenetwork):
	try:
		my_net = ipaddress.ip_network(sourcenetwork, strict=False)
	except (ValueError):
		return False
	return True, my_net

def type_of_network(sourcenetwork):
	try:
		my_net = ipaddress.ip_network(sourcenetwork, strict=False)
	except (ValueError):
		return False
	return my_net

def parse_args():
    switches = []
    for IPorHM in hostname_list:
        switch = connect (username, password, IPorHM)
        switches.append(switch)
    return switches, hostname_list


def connect(user, password, address):
   #Connect to Switch via eAPI
    switch = Server("http://"+user+":"+password+"@"+address+"/command-api")
    #capture Connection problem messages:
    try:
        response = switch.runCmds(1, ["show version"])
    except socket.error as error:
        error_code = error[0]
        if error_code == errno.ECONNREFUSED:
            run_error = str("[Error:"+str(error_code)+"] Connection Refused!(eAPI not configured?)")
            print ("\n\nswitch: " + str(address))
            print (run_error)
            print ("\n\n")
            sys.exit(2)
        elif error_code == errno.EHOSTUNREACH:
            run_error = str("[Error:"+str(error_code)+"] No Route to Host(Switch powered off?)")
            print ("\n\nswitch: " + str(address))
            print (run_error)
            print ("\n\n")
            sys.exit(2)
        elif error_code == errno.ECONNRESET:
            run_error = str("[Error:"+str(error_code)+"] Connection RST by peer (Restart eAPI)")
            print ("\n\nswitch: " + str(address))
            print (run_error)
            print ("\n\n")
            sys.exit(2)
        else:
            # Unknown error - report number and error string (should capture all)
            run_error = str("[Error5:"+str(error_code) + "] "+error[1])
            #raise error;
            print ("\n\nswitch: " + str(address))
            print (run_error)
            print ("\n\n")
            sys.exit(2)
    else:
        return switch

		
def RenderTopologyVariables():
	# Updating for the main Program
	global NHVRFDict
	global NHIPDict
	global NHIP6Dict
	global SflowMultiplier
	global AppRunTimer
	global DeadSflowTimer
	global MaxSflowEntries
	global DeadFlowRemovalTimer
	global DeadFlowRemoval
	global ListOfLERs
	global ConfiguredLERs
	script_dir = os.path.dirname(__file__)
	rel_path = "TopologyVariables.yaml"
	abs_file_path = os.path.join(script_dir, rel_path)
	file=open(abs_file_path)
	if sys.version_info[0] < 3:
		topo_vars = yaml.load(file.read(),Loader=yaml.FullLoader)
	else:
		topo_vars = yaml.load(file.read(),Loader=yaml.FullLoader)
	topo_vars['home_directory'] = os.path.dirname(os.path.realpath(__file__))
	file.close()
	try:
		SflowMultiplier=int(topo_vars['SflowMultiplier'])
		AppRunTimer=int(topo_vars['AppRunWaitTime'])
		MaxSflowEntries=str(topo_vars['MaxSflowEntries'])
		DeadSflowTimer=str(topo_vars['SflowDeadTimer'])
		DeadFlowRemovalTimer=int(topo_vars['DeadSflowRemovalWaitTime'])
		DeadFlowRemoval=str(topo_vars['DeadFlowRemoval'])
	except:
		pass
	try:
		for Router in topo_vars['EdgeRouters']:
			NHVRFDict[Router['RouterID']]=Router['VRF']
	except:
		pass
	try:
		ConfiguredLERs = []
		for entry in topo_vars['EdgeRouters']:
			ConfiguredLERs.append(entry['RouterID'])
		for Router in topo_vars['EdgeRouters']:
			if Router['RouterID'] in ListOfLERs:
				pass
			if Router['RouterID'] not in ListOfLERs:
				ListOfLERs.append(Router['RouterID'])
		ListOfLERs = [a for a in ListOfLERs for b in ConfiguredLERs if a == b]
	except:
		pass

	try:
		for Router in topo_vars['EdgeRouters']:
			NHIP6Dict[Router['RouterID']]=Router['IP6NH']
	except:
		pass
	try:
		for Router in topo_vars['EdgeRouters']:
			NHIPDict[Router['RouterID']]=Router['IPNH']
	except:
		pass

def CheckPolicy(DataList,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList,CurrentAction,PolicyBandwidth, bw):
	try:
		SourcePortProtocol = str(DataList[1])+':'+str(DataList[3])
		DestinationPortProtocol = str(DataList[1])+':'+str(DataList[6])
		if 'None' in CurrentAction:
			###--("Theres a NONE as an action so returning false")
			return False
		elif SourcePortProtocol in CurrentConfiguredSourceProtocolPortList and DestinationPortProtocol in CurrentConfiguredDestinationProtocolPortList and PolicyBandwidth > bw:
			###--("The bandwidth of this flow is too low - returning False")
			return False
		elif SourcePortProtocol in CurrentConfiguredSourceProtocolPortList and DestinationPortProtocol in CurrentConfiguredDestinationProtocolPortList and bw >= PolicyBandwidth:
			###--("Caught the Rule with an Exact Match on Source and Destination Port")
			return True
		elif SourcePortProtocol in CurrentConfiguredSourceProtocolPortList and str(DataList[1]) == '1' and bw >= PolicyBandwidth:
			###--("Processed ICMP Flow (don't check destination - That specific match  S & D can be caught by above rule)")
			return True
		elif DestinationPortProtocol in CurrentConfiguredDestinationProtocolPortList and bw >= PolicyBandwidth and CurrentConfiguredSourceProtocolPortList != []:
			for entry in CurrentConfiguredSourceProtocolPortList:
				if '>' in entry:
					if DataList[1] == entry.split('>')[0] and DataList[3] > entry.split('>')[1]:
						###--("Specific Destination Port Match and Source is explicitly > 1024 (well known ports)")
						return True
				elif '<' in entry:
					if DataList[1] == entry.split('<')[0] and DataList[3] < entry.split('<')[1]:
						###--("Specific Destination Port Match and Source is explicitly < 1024 (well known ports)")
						return True
				else:
					###--("Specific Destination Port (don't check Source Port - That specific match S & D can be caught by above rule)")
					return True
			
		elif SourcePortProtocol in CurrentConfiguredSourceProtocolPortList and bw >= PolicyBandwidth and CurrentConfiguredDestinationProtocolPortList != []:
			for entry in CurrentConfiguredDestinationProtocolPortList:
				if '>' in entry:
					if DataList[1] == entry.split('>')[0] and DataList[6] > entry.split('>')[1]:
						###--("Specific Source Port Match and Destination is explicitly > 1024 (well known ports)")
						return True	
				elif '<' in entry:
					if DataList[1] == entry.split('<')[0] and DataList[6] < entry.split('<')[1]:
						###--("Specific Source Port Match and Destination is explicitly < 1024 (well known ports)")
						return True
				else:
					###--("Specific Source Port  (don't check Destination Port - That specific match S & D can be caught by above rule)")
					return True
				
		elif DestinationPortProtocol in CurrentConfiguredDestinationProtocolPortList and bw >= PolicyBandwidth:
			###--("Specific Destination Port (No Source Port List at all - That specific match S & D can be caught by above rule)")
			return True
		elif SourcePortProtocol in CurrentConfiguredSourceProtocolPortList and bw >= PolicyBandwidth:
			###--("Specific Source Port  (No Destination Port List at all - That specific match S & D can be caught by above rule)")
			return True
		
		elif bw >= PolicyBandwidth:
			DestinationGreaterThanDict = {}
			DestinationLessThanDict = {}
			SourceGreaterThanDict = {}
			SourceLessThanDict = {}
			try:
				for entry in CurrentConfiguredDestinationProtocolPortList:
					if '>' in entry:
						DestinationGreaterThanDict[entry.split('>')[0]]=entry.split('>')[1]
					if '<' in entry:
						DestinationLessThanDict[entry.split('<')[0]]=entry.split('<')[1]
			except:
				pass
			try:
				for entry in CurrentConfiguredSourceProtocolPortList:
					if '>' in entry:
						SourceGreaterThanDict[entry.split('>')[0]]=entry.split('>')[1]
					if '<' in entry:
						SourceLessThanDict[entry.split('<')[0]]=entry.split('<')[1]
			except:
				pass

			try:
				if int(DataList[3]) < int(SourceLessThanDict.get(DataList[1])) and DataList[1] in SourceLessThanDict.keys():
					if DataList[1] in DestinationLessThanDict.keys() or DataList[1] in DestinationGreaterThanDict.keys():
						try:
							if int(DataList[6]) < int(DestinationLessThanDict.get(DataList[1])):
								###--("Source < 1024 and Destination is < 1024 (well known ports)")
								return True
						except:
							pass
						try:
							if int(DataList[6]) > int(DestinationGreaterThanDict.get(DataList[1])):
								###--("Source < 1024 and Destination is > 1024 (well known ports)")
								return True
						except:
							pass
					else:
						pass
			except:
				pass
			try:	
				if int(DataList[3]) > int(SourceGreaterThanDict.get(DataList[1])) and DataList[1] in SourceGreaterThanDict.keys():
					if DataList[1] in DestinationLessThanDict.keys() or DataList[1] in DestinationGreaterThanDict.keys():
						try:
							if int(DataList[6]) < int(DestinationLessThanDict.get(DataList[1])):
								###--("Source > 1024 and Destination is < 1024 (well known ports)")
								return  True
						except:
							pass
						try:
							if int(DataList[6]) > int(DestinationGreaterThanDict.get(DataList[1])):
								###--("Source > 1024 and Destination is > 1024 (well known ports)")
								return True
						except:
							pass
				else:
					pass
			except:
				pass
			try:	
				if int(DataList[3]) > int(SourceGreaterThanDict.get(DataList[1])) and DataList[1] in SourceGreaterThanDict.keys():
					###--("Just Check Source Greater Than Port and protocol")
					return True
				else:
					pass
			except:
				pass
			try:	
				if int(DataList[3]) < int(SourceLessThanDict.get(DataList[1])) and DataList[1] in SourceLessThanDict.keys():
					###--("Just Check Source Less Than Port and protocol")
					return True
				else:
					pass
			except:
				pass
			try:	
				if int(DataList[6]) < int(DestinationLessThanDict.get(DataList[1])) and DataList[1] in DestinationLessThanDict.keys():
					###--("Just Check Destination Less Than Port and protocol")
					return True
				else:
					pass
			except:
				pass
			try:	
				if int(DataList[6]) > int(DestinationGreaterThanDict.get(DataList[1])) and DataList[1] in DestinationGreaterThanDict.keys():
					###--("Just Check Destination Greater Than Port and protocol")
					return True
				else:
					###--("Source port or Destination Port is not in any configured Policy -> Returning False")
					return False
			except:
				pass
	except:
		pass



def ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction,ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList):
	try:
		if len(ListOfFlows) == 0:
			ListOfFlows.append(DataList)
			FlowActionDict[str(DataList)]=CurrentAction
			ExabgpAndQueueCalls.ExaBgpAnnounce(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),CurrentAction,ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
			###--("Length List of flows 0 , added the flow and Dict Entry")
		elif FlowActionDict.get(str(DataList)) != None and FlowActionDict.get(str(DataList)) != CurrentAction:
			ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
			FlowActionDict.pop(str(DataList),None)
			ListOfFlows.remove(DataList)
			###--("Popped the dict entry and List")
			ListOfFlows.append(DataList)
			FlowActionDict[str(DataList)]=CurrentAction
			ExabgpAndQueueCalls.ExaBgpAnnounce(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),CurrentAction,ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
			###--("Added flow and Dict entry and list")
		elif DataList not in ListOfFlows:
			ListOfFlows.append(DataList)
			FlowActionDict[str(DataList)]=CurrentAction
			ExabgpAndQueueCalls.ExaBgpAnnounce(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList)
			###--("Hit the else, added the flow and Dict Entry")
		else:
			if DataList in ListOfFlows:
				###--("Hit the pass rule")
				pass
	except:
		pass				



def Sort(sub_list): 
    sub_list.sort(key = lambda x: x[1]) 
    return sub_list



def GetPortList(PortList):
	PortProtocol = []
	for entry in PortList:
		for protocol in ProtocolList:
			try:
				if 'ICMPv6' in entry:
					PortProtocol.append(str(protocol[entry.split(' ')[0]])+':'+str(entry.split('=')[1]))				
			except:
				pass
			try:
				if 'ICMP' in entry:
					PortProtocol.append(str(protocol[entry.split(' ')[0]])+':'+str(entry.split('=')[1]))				
			except:
				pass
			try:
				PortProtocol.append(str(protocol[entry.split('=')[0]])+':'+str(entry.split('=')[1]))			
			except:
				pass
			try:
				PortProtocol.append(str(protocol[entry.split('>')[0]])+'>'+str(entry.split('>')[1]))				
			except:
				pass
			try:
				PortProtocol.append(str(protocol[entry.split('<')[0]])+'<'+str(entry.split('<')[1]))				
			except:
				pass
	return PortProtocol





class FindAndProgramDdosFlowsHelperClass(object):
	def __init__(self):
		self.ActiveFlowspecRoutes = []
		self.ActiveManualFlowspecRoutes = []		

	def ExaBgpAnnounceManualRoute(self, ler,protocol,sourceprefix,sourceport,destinationprefix,destinationport,action,ExaBGPQueue):
		if protocol == '1':
			command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + ' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' icmp-type [' + sourceport + '] '  + action
			ExaBGPQueue.put_nowait(command)
			command = 'neighbor ' + ler + ' source '+ sourceprefix + ' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' icmp-type [' + sourceport + '] '  + action
			self.ActiveManualFlowspecRoutes.append(command)
		elif protocol == '58':
			command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + ' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' icmp-type [' + sourceport + '] '  + action
			ExaBGPQueue.put_nowait(command)
			command = 'neighbor ' + ler + ' source '+ sourceprefix + ' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' icmp-type [' + sourceport + '] '  + action
			self.ActiveManualFlowspecRoutes.append(command)
		else:
			command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix +' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' source-port [' + sourceport + ']' ' destination-port [' + destinationport + '] ' + action
			ExaBGPQueue.put_nowait(command)
			command = 'neighbor ' + ler + ' source '+ sourceprefix +' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' source-port [' + sourceport + ']' ' destination-port [' + destinationport + '] ' + action
			self.ActiveManualFlowspecRoutes.append(command)

	def ExaBgpWithdrawManualRoute(self, ler,protocol,sourceprefix,sourceport,destinationprefix,destinationport,action,ExaBGPQueue):
		if protocol == '1':
			command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + ' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' icmp-type [' + sourceport + '] '  + action
			ExaBGPQueue.put_nowait(command)
			command = 'neighbor ' + ler +  ' source '+ sourceprefix + ' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' icmp-type [' + sourceport + '] '  + action
			self.ActiveManualFlowspecRoutes.remove(command)
		elif protocol == '58':
			command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + ' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' icmp-type [' + sourceport + '] '  + action
			ExaBGPQueue.put_nowait(command)
			command = 'neighbor ' + ler +  ' source '+ sourceprefix + ' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' icmp-type [' + sourceport + '] '  + action
			self.ActiveManualFlowspecRoutes.remove(command)
		else:
			command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix +' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' source-port [' + sourceport + ']' ' destination-port [' + destinationport + '] ' + action
			ExaBGPQueue.put_nowait(command)
			command = 'neighbor ' + ler + ' source '+ sourceprefix +' destination ' + destinationprefix+ ' protocol ' '['+ protocol +']' ' source-port [' + sourceport + ']' ' destination-port [' + destinationport + '] ' + action
			self.ActiveManualFlowspecRoutes.remove(command)

	def ExaBgpAnnounce(self, ler,protocol,sourceprefix,sourceport,destinationprefix,destinationport,action,ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList):
		if self.is_valid_ipv4_address(sourceprefix):
			if protocol == '1':
				if CurrentConfiguredDestinationProtocolPortList == []:
					command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + '] '  + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.append(command)
				elif CurrentConfiguredSourceProtocolPortList == []:
					command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + destinationport + '] '  + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.append(command)			
				else:
					command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '   + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.append(command)
			else:
				command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' + action
				#Put in the queue for Programming
				ExaBGPQueue.put_nowait(command)
				command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' + action
				self.ActiveFlowspecRoutes.append(command)
				
		if self.is_valid_ipv6_address(sourceprefix):
			if protocol == '58':
				if CurrentConfiguredDestinationProtocolPortList == []:
					command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + '] '  + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.append(command)
				elif CurrentConfiguredSourceProtocolPortList == []:
					command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + destinationport + '] '  + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.append(command)			
				else:
					command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '   + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.append(command)
			else:
				command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' + action
				#Put in the queue for Programming
				ExaBGPQueue.put_nowait(command)
				command = 'neighbor ' + ler + ' source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' + action
				self.ActiveFlowspecRoutes.append(command)
	
	def ExaBgpWithdraw(self,ler,protocol,sourceprefix,sourceport,destinationprefix,destinationport,action,ExaBGPQueue,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList):
		if self.is_valid_ipv4_address(sourceprefix):
			if protocol == '1':
				if CurrentConfiguredDestinationProtocolPortList == []:
					command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + '] '  + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.remove(command)
				elif CurrentConfiguredSourceProtocolPortList == []:
					command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']'  ' icmp-type [=' + destinationport + '] '  + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.remove(command)				
				else:
					command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.remove(command)
			else:
				command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'  + ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' +  action
				#Put in the queue for Programming
				ExaBGPQueue.put_nowait(command)
				command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'  + ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' +  action
				self.ActiveFlowspecRoutes.remove(command)
				
		if self.is_valid_ipv6_address(sourceprefix):
			if protocol == '58':
				if CurrentConfiguredDestinationProtocolPortList == []:
					command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + '] '  + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.remove(command)
				elif CurrentConfiguredSourceProtocolPortList == []:
					command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']'  ' icmp-type [=' + destinationport + '] '  + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.remove(command)				
				else:
					command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					#Put in the queue for Programming
					ExaBGPQueue.put_nowait(command)
					command = 'neighbor ' + ler + ' source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
					self.ActiveFlowspecRoutes.remove(command)
			else:
				command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'  + ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' +  action
				#Put in the queue for Programming
				ExaBGPQueue.put_nowait(command)
				command = 'neighbor ' + ler + ' source '+ sourceprefix + '/128 ' 'destination ' + destinationprefix + '/128'  + ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' +  action
				self.ActiveFlowspecRoutes.remove(command)

	def is_valid_ipv4_address(self,address):
		try:
			socket.inet_pton(socket.AF_INET, address)
		except AttributeError:  # no inet_pton here, sorry
			try:
				socket.inet_aton(address)
			except socket.error:
				return False
			return address.count('.') == 3
		except socket.error:  # not a valid address
			return False
	
		return True
	
	def is_valid_ipv6_address(self,address):
		try:
			socket.inet_pton(socket.AF_INET6, address)
		except socket.error:  # not a valid address
			return False
		return True


	
	def ReturnActiveFlowspecRoutes(self):
		return self.ActiveFlowspecRoutes

	def ResetActiveFlowspecRoutes(self):
		self.ActiveFlowspecRoutes = []
		
	def ReturnActiveManualFlowspecRoutes(self):
		return self.ActiveManualFlowspecRoutes

	def ResetActiveManualFlowspecRoutes(self):
		self.ActiveManualFlowspecRoutes = []

	def ManualRouteQueuePoll(self,c_queue):
		self.ManualRoute = []
		while not c_queue.empty():
			try:
				msg = c_queue.get()         # Read from the queue
				self.ManualRoute.append(msg)
				c_queue.task_done()
			except:
				False
		return self.ManualRoute

	def UpdatePolicyQueuePoll(self,queue):
		self.UpdatePolicy = []
		while not queue.empty():
			try:
				msg = queue.get()         # Read from the queue
				self.UpdatePolicy.append(msg)
				queue.task_done()
			except:
				False
		return self.UpdatePolicy

	def SignalResetQueuePoll(self,queue):
		self.ResetSignalled = []
		while not queue.empty():
			try:
				msg = queue.get()         # Read from the queue
				self.ResetSignalled.append(msg)
				queue.task_done()
			except:
				False
		return self.ResetSignalled

			

### Tkinter GUI Classes


class FlowspecGUI(ttk.Frame):
	def __init__(self, parent,SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,UpdatePolicyQueue,SignalResetQueue):
		
		# Use These Global File Variable to Ensure tracking right file. Change the GUI if TopologyVariables.yaml changes
		global abs_file_path
		global ListOfFlows
		
		# Set time Stamp.  Compared in UpdateGUI() within this class
		self._cached_stamp = 0
		self.TopologyVariables = abs_file_path
	

		self.ListOfRateLimitBadSourcePorts = []
		self.ListOfRateLimitBadDestinationPorts = []
		self.ListOfRedirectNHBadSourcePorts = []
		self.ListOfRedirectNHBadDestinationPorts = []
		self.ListOfRedirectVRFBadSourcePorts = []
		self.ListOfRedirectVRFBadDestinationPorts = []
		self.FlowPolicyBandwidth = ''
		self.RateLimitFlowPolicyBandwidth = ''
		self.RedirectNHFlowPolicyBandwidth = ''
		self.RedirectVRFFlowPolicyBandwidth = ''
		self.DefaultBandwidth = ''
		self.RateLimit = ''
		self.DefaultRateLimit = ''
		self.defaultaction = ''
		
		
		BG0 = 'white' #White Canvas (interior)
		BG1 = '#4e88e5' #Blue scheme

		
		ttk.Frame.__init__(self, parent=None, style='FlowspecGUI.TFrame', borderwidth=0,relief='raised')
		self.mainwindow = parent
		self.mainwindow.title('BGP Flowspec Policy Manager')
		self.mainwindow.geometry('1000x900')

		self.createWidgets(BG0, BG1)
		
		self.rowconfigure(0, weight=1)
		self.columnconfigure(0, weight=1)
		
	
	def createWidgets(self, BG0, BG1):
		self.frame = VerticalScrollFrame(self,
										pri_background=BG1,
										sec_background=BG0,
										arrowcolor='white',
										mainborderwidth=10,
										interiorborderwidth=10,
										mainrelief='raised',
										interiorrelief='sunken'
										)
		self.frame.grid(row=0, column=0, sticky='nsew')
		self.frame.interior.columnconfigure(0, weight=1)
		self.frame.interior.columnconfigure(4, weight=1)
		self.frame.interior.rowconfigure(17, weight=2)
		self.frame.interior.rowconfigure(25, weight=1)
		self.window = self.frame.interior


		
		# ---------------- ROW-0 ---------------#
		
		TitleLabel=tk.Label(self.window,font=("Verdana", 16),background='light grey', relief='ridge',text="BGP Flowspec Policy Management")
		TitleLabel.grid(row=0,columnspan=5, sticky='nswe')
		
		# ---------------- ROW-1 ---------------#
		
		SetBackGroundColor=tk.Label(self.window,background=BG0,text='',font=("Verdana", 12),justify='right')
		SetBackGroundColor.grid(column=0, row=1,columnspan=5, rowspan=40,sticky='nswe')
		
		PolicyTitleLabel=tk.Label(self.window,font=("Verdana", 12),fg='dark blue',background=BG0,text="\n########## Default Flow Inspection Policy Bandwidth & Action Policy ###########")
		PolicyTitleLabel.grid(column=1, row=1,columnspan=3, sticky='we')
		
		# ---------------- ROW-2 ---------------#
		
		DefaultActionRuleLabel=tk.Label(self.window,background=BG0,text="Select the Default Flow Policy ",font=("Verdana", 10),justify='right',anchor='nw',)
		DefaultActionRuleLabel.grid(column=1, row=2,columnspan=3,sticky='we')
		
		# ---------------- ROW-3 ---------------#

		
		self.selecteddefaultaction = tk.IntVar()
				
		self.DefaultRateLimitTrafficRad = tk.Radiobutton(self.window, background=BG0,value=1, variable=self.selecteddefaultaction, command=self.InitialDefaultRateLimitTextBoxFocus)
		self.DefaultRateLimitTrafficRadLabel = tk.Label(self.window,width=15,text='Rate-Limit',font=("Verdana",12),fg='black',background='grey95',relief='ridge')
		self.DefaultRedirectIPRad = tk.Radiobutton(self.window,background=BG0,value=2, variable=self.selecteddefaultaction, command=self.SetDefaultAction)
		self.DefaultRedirectIPRadLabel = tk.Label(self.window,width=20,text='Redirect To Next Hop',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.DefaultRedirectVRFRad = tk.Radiobutton(self.window,background=BG0,value=3, variable=self.selecteddefaultaction, command=self.SetDefaultAction)
		self.DefaultRedirectVRFRadLabel = tk.Label(self.window,width=20,text='Redirect To VRF',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.DefaultRateLimitTrafficRad.grid(column=1, row=3,sticky='w',padx=10)
		self.DefaultRedirectIPRad.grid(column=2, row=3, sticky='w',padx=10)
		self.DefaultRedirectVRFRad.grid(column=3, row=3,sticky='w',padx=10)
		self.DefaultRateLimitTrafficRadLabel.grid(column=1, row=3, sticky='w', padx=50)
		self.DefaultRedirectIPRadLabel.grid(column=2, row=3,sticky='w',padx=50)
		self.DefaultRedirectVRFRadLabel.grid(column=3, row=3,sticky='w',padx=50)
		self.DefaultDummyRad = tk.Radiobutton(self.window, value=5, variable=self.selecteddefaultaction)
		
		self.DefaultRateLimitTextBox = tk.Text(self.window, background=BG0, height = 1, width = 8, borderwidth=1, relief="ridge")
		self.DefaultRateLimitTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.DefaultRateLimitTextBox.insert('1.0','<kbps>')
		self.DefaultRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DefaultRateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.DefaultRateLimitTextBox.bind("<Button-1>", self.SetDefaultRateLimitTextBoxFocus)
		self.DefaultRateLimitTextBox.bind("<Return>", self.GetDefaultRateLimit)
		self.DefaultRateLimitTextBox.bind("<FocusOut>", self.SetDefaultRateLimitTextBoxUnFocus)
		self.DefaultRateLimitTextBox.bind("<FocusIn>", self.SetDefaultRateLimitTextBoxFocus)
		self.DefaultRateLimitTextBox.grid(column=1, row=3,sticky='e', padx=10)
		
		# ---------------- ROW-4 ---------------#
		
		DefaultFlowPolicyBwLabel=tk.Label(self.window, background=BG0, text="Default Policy Inspection Bandwidth (Mbps): ",font=("Verdana", 10),justify='right')
		DefaultFlowPolicyBwLabel.grid(column=1,row=4,sticky='e',pady=10)
		
		self.DefaultBandwidthTextBox = tk.Text(self.window, background=BG0, height = 1, width = 40, borderwidth=1, relief="ridge")
		self.DefaultBandwidthTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.DefaultBandwidthTextBox.insert('1.0','(Click <enter/return> to set policy bandwidth)')
		self.DefaultBandwidthTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DefaultBandwidthTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.DefaultBandwidthTextBox.bind("<Button-1>", self.SetDefaultBandwidthTextBoxFocus)
		self.DefaultBandwidthTextBox.bind("<Return>", self.GetDefaultFlowPolicyBandWidth)
		self.DefaultBandwidthTextBox.bind("<FocusOut>", self.SetDefaultBandwidthTextBoxUnFocus)
		self.DefaultBandwidthTextBox.bind("<FocusIn>", self.SetDefaultBandwidthTextBoxFocus)
		self.DefaultBandwidthTextBox.grid(column=2, columnspan=2, row=4,sticky='w',padx=30)
		
		# ---------------- ROW-5 ---------------#
		
		SectionLabel=tk.Label(self.window,background=BG0,text="Program Default Policy >>>",font=("Verdana", 14,'bold'),justify='left')
		SectionLabel.grid(column=1, columnspan=2,row=5,sticky='e',padx=120)
		push_button0=tk.Button(self.window, text="Click Here", command=self.ProgramDefaultPolicy,font=("Verdana", 10),fg='white',bg='dark grey')
		push_button0.grid(column=2, row=5,sticky='e')
		ClearDefaultSelection=tk.Button(self.window,background=BG0, text="Clear Selections", command=self.ClearDefaultSelection,font=("Verdana", 10,'italic'))
		ClearDefaultSelection.grid(column=3, row=5,sticky='w', padx=10)
		
		# ---------------- ROW-6 ---------------#
		
		SpacerLabel=tk.Label(self.window,background=BG0,text="\n",font=("Verdana", 10),justify='right')
		SpacerLabel.grid(column=3, columnspan=3,row=6,sticky='w')		
		
		# ---------------- ROW-7 ---------------#
		
		SectionLabel=tk.Label(self.window,background=BG0,text="Active Default Policy:",font=("Verdana", 12,'bold'),justify='left',fg='dark blue')
		SectionLabel.grid(column=1, row=7,sticky='e',padx=10)
		
		self.DefaultBandwidthTextBoxPolicy = tk.Text(self.window,background=BG0,height = 1, width = 42, borderwidth=2, relief="raised",font=("Verdana",12))
		self.DefaultBandwidthTextBoxPolicy.grid(column=2, columnspan=2,row=7,sticky='w',padx=10)
		
		ClearDefaultPolicy=tk.Button(self.window, background=BG0, text="Clear Default Policy",command=self.ClearDefaultPolicy, font=("Verdana", 10,'bold'),)
		ClearDefaultPolicy.grid(column=3, row=7,sticky='e')
		
		# ---------------- ROW-8 ---------------#
		
		PolicyTitleLabel=tk.Label(self.window,background=BG0, text='\n############ Configure Flow Inspection Policy Bandwidth, Action & Ports #############',font=("Verdana", 10),justify='left',fg='dark blue')
		PolicyTitleLabel.grid(column=1, row=8,columnspan=3, sticky='we')
		
		
		# ---------------- ROW-9 ---------------#
		
		self.selected = tk.IntVar()
		ActionRuleLabel=tk.Label(self.window, background=BG0, text="Select the Flow Policy (Required)",font=("Verdana", 10),justify='right',anchor='nw',)
		ActionRuleLabel.grid(column=1, row=9,columnspan=3,sticky='nw')
		
		# ---------------- ROW-10 ---------------#
		
		self.RateLimitTrafficRad = tk.Radiobutton(self.window, background=BG0, value=1, variable=self.selected, command=self.InitialRateLimitTextBoxFocus)
		self.RateLimitTrafficRadLabel = tk.Label(self.window,width=15,text='Rate-Limit',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.RedirectIPRad = tk.Radiobutton(self.window, background=BG0,value=2, variable=self.selected, command=self.SetAction)
		self.RedirectIPRadLabel = tk.Label(self.window,width=20,text='Redirect To Next Hop',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.RedirectVRFRad = tk.Radiobutton(self.window, background=BG0,value=3, variable=self.selected, command=self.SetAction)
		self.RedirectVRFRadLabel = tk.Label(self.window,width=20,text='Redirect To VRF',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.RateLimitTrafficRad.grid(column=1, row=10, sticky='w',padx=10)
		self.RedirectIPRad.grid(column=2, row=10, sticky='w',padx=10)
		self.RedirectVRFRad.grid(column=3, row=10,sticky='w',padx=10)
		self.RateLimitTrafficRadLabel.grid(column=1, row=10, sticky='w',padx=50)
		self.RedirectIPRadLabel.grid(column=2, row=10,sticky='w',padx=50)
		self.RedirectVRFRadLabel.grid(column=3, row=10,sticky='w',padx=50)
		self.DummyRad = tk.Radiobutton(self.window, value=5, variable=self.selected,command=self.SetAction)

		self.RateLimitTextBox = tk.Text(self.window, background=BG0, height = 1, width = 8, borderwidth=1, relief="ridge")
		self.RateLimitTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.RateLimitTextBox.insert('1.0','<kbps>')
		self.RateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.RateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.RateLimitTextBox.bind("<Button-1>", self.SetRateLimitTextBoxFocus)
		self.RateLimitTextBox.bind("<Return>", self.GetRateLimit)
		self.RateLimitTextBox.bind("<FocusOut>", self.SetRateLimitTextBoxUnFocus)
		self.RateLimitTextBox.bind("<FocusIn>", self.SetRateLimitTextBoxFocus)
		self.RateLimitTextBox.grid(column=1, row=10,sticky='e', padx=10)
		
		
		# ---------------- ROW-11 ---------------#
		
		
		FlowPolicyBwLabel=tk.Label(self.window, background=BG0, text="Flow Policy Inspection Bandwidth (Mbps): ",font=("Verdana", 10),justify='right')
		FlowPolicyBwLabel.grid(column=1,row=11,sticky='e',pady=10)
		
		self.BandwidthTextBox = tk.Text(self.window, background=BG0, height = 1, width = 40, borderwidth=1, relief="ridge")
		self.BandwidthTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.BandwidthTextBox.insert('1.0','(Click <enter/return> to set policy bandwidth)')
		self.BandwidthTextBox.tag_add("boldcentered", "1.0", 'end')
		self.BandwidthTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.BandwidthTextBox.bind("<Button-1>", self.SetBandwidthTextBoxFocus)
		self.BandwidthTextBox.bind("<Return>", self.GetFlowPolicyBandWidth)
		self.BandwidthTextBox.bind("<FocusOut>", self.SetBandwidthTextBoxUnFocus)
		self.BandwidthTextBox.bind("<FocusIn>", self.SetBandwidthTextBoxFocus)
		self.BandwidthTextBox.grid(column=2, columnspan=2, row=11,sticky='w',padx=30)
		
		
		# ---------------- ROW-15 ---------------#
		
		PortListLabel=tk.Label(self.window, background=BG0, text="Select the port(s):protocols to add/remove from the list below: ",font=("Verdana", 10),justify='right',anchor='nw')
		PortListLabel.grid(column=1, columnspan=3,row=15,sticky='w',pady=10)
		
		
		# ---------------- ROW-16 ---------------#
		
		SourcePortLabel=tk.Label(self.window, background=BG0, text="Select Source Ports/Protocols: ",font=("Verdana", 10,'bold'),anchor='n')
		SourcePortLabel.grid(column=1, row=16)
		
		DestinationPortLabel=tk.Label(self.window, background=BG0, text="Select Destination Ports/Protocols: ",font=("Verdana", 10,'bold'),anchor='n')
		DestinationPortLabel.grid(column=2, row=16)
		
		SelectPortButton = tk.Button(self.window, background=BG0,  text=" Add ", width=10, command=self.AddToPolicy,font=("Verdana",10))
		SelectPortButton.grid(column=3, row=16,padx=10,sticky='w')
		
		RemovePortButton = tk.Button(self.window, background=BG0, text=" Remove ", width=10, command=self.RemoveFromPolicy,font=("Verdana",10))
		RemovePortButton.grid(column=3, row=16,padx=30,sticky='e')
		
		
		self.RateLimitPolicyTextBox = ScrolledText(self.window, background=BG0, height = 5, borderwidth=3,width=30, relief="sunken")
		self.RateLimitPolicyTextBox.configure(bg = 'grey95', wrap='word', fg = 'white',font=("Verdana", 10))
		self.RateLimitPolicyTextBox.grid(column=1, row=25,sticky='nswe',padx=10)
		
		# ---------------- ROW-17 ---------------#
		
		scrollbar = tk.Scrollbar(self.window, background=BG1,  orient="vertical")
		scrollbar.grid(column=1, row=17,sticky='nse')
		self.SourcePorts = tk.Listbox(self.window, background='grey95',  exportselection=0, relief = 'raised', height = 5, yscrollcommand=scrollbar.set, font=("Verdana", 10,'bold'),selectmode='multiple')
		self.SourcePorts.grid(column=1, row=17,sticky='nswe',padx=15)
		scrollbar.config(command=self.SourcePorts.yview)
		
		for x in PortList:
			self.SourcePorts.insert('end', x)
			
		self.SourcePorts.bind('<<ListboxSelect>>',self.CurSourceSelet)
		
		scrollbar1 = tk.Scrollbar(self.window, background=BG0,  orient="vertical")
		scrollbar1.grid(column=2, row=17,sticky='nse')
		self.DestinationPorts = tk.Listbox(self.window, background='grey95',  exportselection=0, relief = 'raised', width=30, height = 5, yscrollcommand=scrollbar1.set, font=("Verdana", 10,'bold'),selectmode='multiple')
		self.DestinationPorts.place(relx = 0.5, rely = 0.5, anchor="center")
		self.DestinationPorts.grid(column=2, row=17,sticky='nswe',padx=15)
		scrollbar1.config(command=self.DestinationPorts.yview)
		
		for x in PortList:
			self.DestinationPorts.insert('end', x)
			
		self.DestinationPorts.bind('<<ListboxSelect>>',self.CurDestinationSelet)
		
		self.PortTextBox = ScrolledText(self.window, background=BG0, width=30,height = 5, borderwidth=3, relief="raised",font=("Verdana",10,'bold'))
		self.PortTextBox.grid(column=3, row=17,sticky='nswe',padx=10)
		
		# ---------------- ROW-22 ---------------#
		
		ProgramFlowPolicyLabel=tk.Label(self.window, background=BG0, text="Program Flow Policy >>>",font=("Verdana", 14,'bold'),justify='left')
		ProgramFlowPolicyLabel.grid(column=1, columnspan=2,row=22,sticky='e',padx=120)
		ProgramFlowPolicyButton=tk.Button(self.window, text="Click Here", command=self.UpdateFlowspecPolicy,font=("Verdana", 10),fg='white',bg='dark grey')
		ProgramFlowPolicyButton.grid(column=2, row=22,sticky='e')
		ClearPolicySelection=tk.Button(self.window, background=BG0, text="Clear Selections", command=self.ClearPolicySelection,font=("Verdana", 10,'italic'))
		ClearPolicySelection.grid(column=3, row=22,sticky='w',padx=10)
		
		
		# ---------------- ROW-23 ---------------#
		
		ProgrammedPolicyLabel=tk.Label(self.window, background=BG0, text="\n",font=("Verdana", 12),justify='right',anchor='nw')
		ProgrammedPolicyLabel.grid(column=1, columnspan=3,row=23,sticky='w')
		
		# ---------------- ROW-24 ---------------#
		
		RateLimitPolicyLabel=tk.Label(self.window, background=BG0, text="Active Rate-Limit Policy",font=("Verdana", 12,'bold'),fg='dark blue')
		RateLimitPolicyLabel.grid(column=1, row=24)
		
		RedirectNHPolicyLabel=tk.Label(self.window, background=BG0, text="Active Redirect NH Policy: ",font=("Verdana", 12,'bold'),fg='dark blue')
		RedirectNHPolicyLabel.grid(column=2, row=24)
		
		RedirectVRFPolicyLabel=tk.Label(self.window, background=BG0, text="Active Redirect VRF Policy: ",font=("Verdana", 12,'bold'),fg='dark blue')
		RedirectVRFPolicyLabel.grid(column=3, row=24)
		
		
		# ---------------- ROW-25 ---------------#
		
		self.RateLimitPolicyTextBox = ScrolledText(self.window, background=BG0, height = 5, borderwidth=3,width=20, relief="raised")
		self.RateLimitPolicyTextBox.configure(bg = 'white', wrap='word', fg = 'white',font=("Verdana", 10,'bold'))
		self.RateLimitPolicyTextBox.grid(column=1, row=25,sticky='nswe',padx=10)
		
		self.RedirectNHPolicyTextBox = ScrolledText(self.window, background=BG0, height = 5, borderwidth=3,width=20, relief="raised")
		self.RedirectNHPolicyTextBox.configure(bg = 'white', wrap='word', fg = 'white',font=("Verdana", 10,'bold'))
		self.RedirectNHPolicyTextBox.grid(column=2,sticky='nswe', row=25)
		
		self.RedirectVRFPolicyTextBox = ScrolledText(self.window, background=BG0, height = 5, borderwidth=3,width=20, relief="raised")
		self.RedirectVRFPolicyTextBox.configure(bg = 'white', wrap='word', fg = 'white',font=("Verdana", 10,'bold'))
		self.RedirectVRFPolicyTextBox.grid(column=3,sticky='nswe', row=25,padx=10)
		
		
		# ---------------- ROW-29 ---------------#
		
		ClearRateLimitPolicy=tk.Button(self.window, background=BG0,  text="Clear Rate-Limit Policy", command=self.ClearRateLimitPolicy,font=("Verdana", 10,'bold'))
		ClearRateLimitPolicy.grid(column=1, row=29,sticky='we',padx=10)
		ClearRedirectNHPolicy=tk.Button(self.window, background=BG0,  text="Clear Redirect NH Policy", command=self.ClearRedirectNHPolicy,font=("Verdana", 10,'bold'))
		ClearRedirectNHPolicy.grid(column=2, row=29,sticky='we',padx=10)
		ClearRedirectVRFPolicy=tk.Button(self.window, background=BG0,  text="Clear Redirect VRF Policy", command=self.ClearRedirectVRFPolicy,font=("Verdana", 10,'bold'))
		ClearRedirectVRFPolicy.grid(column=3, row=29,sticky='we',padx=10)
		
		# ---------------- ROW-31 ---------------#
		
		SectionLabel=tk.Label(self.window, background=BG0,text="\n###################### View Live Flow Information ###########################",font=("Verdana", 10,),justify='left',fg='dark blue')
		SectionLabel.grid(column=1, row=31,columnspan=3,sticky='we')
		
		# ---------------- ROW-32 ---------------#
		
		FlowspecRoutes=tk.Button(self.window, text="Show Flowspec Routes Click Here (Pop Up)",width=37,command=self.ShowFlowspecRoutesPopup,font=("Verdana", 10),fg='white',bg='dark grey')
		FlowspecRoutes.grid(column=1,columnspan=2,sticky='w',row=32,padx=10)
		
		ActiveSflow=tk.Button(self.window, text="Show Active sFlow Click Here (Pop Up)", width=37,command=self.ShowSflowPopup,font=("Verdana", 10),fg='white',bg='dark grey')
		ActiveSflow.grid(column=2,columnspan=2,sticky='e',row=32,padx=10)
		
		# ---------------- ROW-33 ---------------#
		
		PolicyTitleLabel=tk.Label(self.window, background=BG0,text="\n######################## Manual Flowspec Rule Push ########################",font=("Verdana", 10),justify='left',fg='dark blue')
		PolicyTitleLabel.grid(column=1, row=33,columnspan=3, sticky='we')
		
		# ---------------- ROW-35 ---------------#
		
		SectionLabel=tk.Label(self.window, background=BG0, text="Program Manual Flowspec Rule >>>",font=("Verdana", 14),justify='left')
		SectionLabel.grid(column=1, columnspan=2, row=35,sticky='e')
		push_button0=tk.Button(self.window, text="Click Here (Pop up)", command=self.ProgramFlowSpecRule, borderwidth=3, height = 1,font=("Verdana", 10),fg='white',bg='dark grey')
		push_button0.grid(column=3, row=35,sticky='w')
		
		#---------------- ROW-36 ---------------#
		
		FooterLabel=tk.Label(self.window, background=BG0, text="\n##################################################################################",font=("Verdana", 10),justify='left',fg='dark blue')
		FooterLabel.grid(column=1, row=36,columnspan=3,sticky='we')
		
		
		#---------------- ROW-37 ---------------#
		
		QuitButton=tk.Button(self.window, text="QUIT", command=self.Quit,font=("Verdana", 18), borderwidth=3, height = 1, fg = 'white', bg = 'red')
		QuitButton.grid(column=2,row=37,sticky='we',pady=10)
		
		QuitButton=tk.Button(self.window, text="RESET POLICY MANAGER", command=self.RestartPolicyManager,font=("Verdana", 12), borderwidth=3, height = 1, fg = 'white', bg = 'dark blue')
		QuitButton.grid(column=1,row=37,sticky='w',pady=10,padx=10)
		
		# Refresh Window with after call to Update the GUI for any TopologyVariables.yaml changes
		self.window.after(1000, self.UpdateGUI)




	# All the methods related to this class are below
	

	def UpdateGUI(self):
		stamp = os.stat(self.TopologyVariables).st_mtime
		if stamp != self._cached_stamp: 			# Well the TopologyVariables File Changed
			self._cached_stamp = stamp
			self.RenderTopologyVariables()
			self.SourcePorts.delete(0, 'end')
			self.DestinationPorts.delete(0, 'end')
			for x in self.PortList:
				self.SourcePorts.insert('end', x)
			self.SourcePorts.bind('<<ListboxSelect>>',self.CurSourceSelet)
			for x in self.PortList:
			    self.DestinationPorts.insert('end', x)
			self.DestinationPorts.bind('<<ListboxSelect>>',self.CurDestinationSelet)
			
		else:	#Nope no change
			pass
		self.window.after(1000, self.UpdateGUI)

	def RenderTopologyVariables(self):
		# Updating for the GUI Class
		script_dir = os.path.dirname(__file__)
		rel_path = "TopologyVariables.yaml"
		abs_file_path = os.path.join(script_dir, rel_path)
		file=open(abs_file_path)
		if sys.version_info[0] < 3:
			topo_vars = yaml.load(file.read(),Loader=yaml.FullLoader)
		else:
			topo_vars = yaml.load(file.read(),Loader=yaml.FullLoader)
		topo_vars['home_directory'] = os.path.dirname(os.path.realpath(__file__))
		file.close()
		# Update the Values in the GUI and for the route programming

		try:
			ConfiguredLERs = []
			for entry in topo_vars['EdgeRouters']:
				ConfiguredLERs.append(entry['RouterID'])
			for Router in topo_vars['EdgeRouters']:
				if Router['RouterID'] in ListOfLERs:
					pass
				if Router['RouterID'] not in ListOfLERs:
					ListOfLERs.append(Router['RouterID'])
			ListOfLERs = [a for a in ListOfLERs for b in ConfiguredLERs if a == b]
		except:
			pass	
		try:
			for Router in topo_vars['EdgeRouters']:
				NHIPDict[Router['RouterID']]=Router['IPNH']
		except:
			pass
		try:
			for Router in topo_vars['EdgeRouters']:
				NHIP6Dict[Router['RouterID']]=Router['IP6NH']
		except:
			pass
		try:
			for Router in topo_vars['EdgeRouters']:
				NHVRFDict[Router['RouterID']]=Router['VRF']
		except:
			pass
		self.ProtocolList = []					#ProtocolList = [{'TCP':6},{'UDP':17}]
		for entry in topo_vars['IPProtocol']:
			self.ProtocolList.append(entry)
		self.PortList = []						#PortList = ['TCP-80','UDP-53', 'TCP-445','TCP>1024','TCP<1024','UDP>1024','UDP<1024']
		for entry in topo_vars['PortList']:
			self.PortList.append(entry)


	def QuitPopup(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.popup.lift()
		self.popup.title("Exiting Application")
		self.TitleLabel=tk.Label(self.popup,text="\nYou're Exiting the App!\n\nSelect What you want to do with the BGP Peers and Flow Routes?",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.OneByOne=tk.Button(self.popup,text='Withdraw One By One',command=self.WithdrawRoutesOneByOne,font=("Verdana",10,'bold'),width=20,fg='black',bg='light grey')
		self.ResetAll=tk.Button(self.popup,text='Reset BGP Peers',command=self.HardExit,font=("Verdana",12,'bold'),width=20,fg='black',bg='light grey')
		self.LeaveActive=tk.Button(self.popup,text='Leave Routes Active',command=self.SoftExit,font=("Verdana",10,'bold'),width=20,fg='black',bg='light grey')
		self.close=tk.Button(self.popup,text='Cancel',command=self.popup.destroy,font=("Verdana",10,'bold'),width=20,fg='black',bg='light grey')
		self.OneByOne.grid(row=2,column=0,sticky='we',padx=10)
		self.ResetAll.grid(row=2,column=1,sticky='we',padx=10)
		self.LeaveActive.grid(row=2,column=2,sticky='we',padx=10)
		self.close.grid(row=3,column=1,sticky='we',padx=10,pady=10)
		
		
	def Quit(self):
		self.QuitPopup(self.window)


	def WithdrawRoutesOneByOne(self):
		###-- ("Withdrawing all routes")
		self.ListOfFlowsOnQuit = []
		self.ListOfFlowsOnQuit = self.SflowQueuePollOnExit(FlowRouteQueueForQuit)
		self.progress = ttk.Progressbar(self.popup, orient="horizontal",length=400, mode="determinate")
		self.progress.grid(row=4,column=1, sticky='s',pady=20)
		t = threading.Thread(target=self.RemoveRoutes)
		t.start()
		self.bytes = 0
		self.progress["value"] = 0
		try:
			self.maxbytes = len(self.ListOfFlowsOnQuit)
		except:
			self.maxbytes  = 0
		self.progress["maximum"] = self.maxbytes
		self.read_bytes()
	
	def read_bytes(self):
		'''simulate reading 200 bytes; update progress bar'''
		self.bytes += 1
		self.progress["value"] = self.bytes
		self.RemovingLabel=tk.Label(self.popup,text="\nRemoving Routes....",font=("Verdana", 10),justify='center')
		self.RemovingLabel.grid(column=0, row=4,sticky='wn',pady=20,padx=20)
		if self.bytes <= self.maxbytes:
			# read more bytes after 200 ms
			self.popup.after(200, self.read_bytes)
		else:
			self.RemovingLabel.destroy
			self.DoneLabel=tk.Label(self.popup,text="\nDone!!!",font=("Verdana", 10),justify='center')
			self.DoneLabel.grid(column=0, row=4,sticky='en',pady=20,padx=20)
			self.popup.after(1000,self.terminate)
			
	def terminate(self):
			FindAndProgramDdosFlowsProcess.terminate()
			SendFlowsToExabgpProcess.terminate()
			self.mainwindow.destroy()

	def RemoveRoutes(self):
		for DataListString in self.ListOfFlowsOnQuit:
			index = DataListString.find('source ')
			command = DataListString[:index] + 'withdraw flow route ' + DataListString[index:]
			r = requests.post(exabgpurl, data={'command':command})	
		
	def HardExit(self):
		###-- ("Withdrawing all routes")
		for Router in topo_vars['EdgeRouters']:
			try:
				print (" \n\n Hard Clearing the Controller BGP peering Session")
				command = 'neighbor '+str(Router['RouterID'])+  ' teardown 2'
				print (command)
				r = requests.post(exabgpurl, data={'command': command})
				time.sleep(.2)
			except:
				command = 'restart'
				print (command)
				print ("\n\nProblem With ExaBgp Restarting ExaBgp ........\n\n\n")
		self.DoneLabel=tk.Label(self.popup,text="\nDone!!!",font=("Verdana", 12,'bold'),justify='center')
		self.DoneLabel.grid(column=1, row=4,sticky='n',pady=20,padx=20)
		self.popup.after(1000,self.terminate)
		
	def SoftExit(self):
		self.DoneLabel=tk.Label(self.popup,text="\nClosing GUI Only!!!",font=("Verdana", 12,'bold'),justify='center')
		self.DoneLabel.grid(column=1, row=4,sticky='n',pady=20,padx=20)
		self.popup.after(1000,self.terminate)
		

	def SflowQueuePollOnExit(self,c_queue):
		self.ListOfFlowsOnQuit = []
		while not c_queue.empty():
			try:
				msg = c_queue.get()         # Read from the queue
				self.ListOfFlowsOnQuit = msg
				queue.task_done()
			except:
				False
		return self.ListOfFlowsOnQuit

	
	def ProgramFlowSpecRule(self):
		popup = ProgramFlowSpecRuleClass(ManualRouteQueue,ManualRouteDisplayQueue)
	
	def ShowFlowspecRoutesPopup(self):
		popup = ShowFlowspecRoutesPopup(FlowRouteQueue,self.window)
	
	def ShowSflowPopup(self):
		popup = ShowSflowPopup(SflowQueue,self.window)

	def ResetDefaultAction(self):
		self.DefaultRedirectIPRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.DefaultRedirectVRFRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.DefaultRateLimitTrafficRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.DefaultDummyRad.select()
		self.defaultaction = ''
	
	def SetDefaultAction(self):
		self.defaultaction = ''
		if self.selecteddefaultaction.get() == 1:
			self.DefaultRateLimitTrafficRadLabel.configure(font=("Verdana", 12),justify='left',fg='white',bg='dark green',relief='sunken')
			self.DefaultRedirectIPRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.DefaultRedirectVRFRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.defaultaction = 'rate-limit'
		elif self.selecteddefaultaction.get() == 2:
			self.DefaultRedirectIPRadLabel.configure(font=("Verdana", 12),justify='left',fg='white',bg='dark green',relief='sunken')
			self.DefaultRateLimitTrafficRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.ResetDefaultRateLimit()
			self.DefaultRedirectVRFRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.defaultaction = 'redirect next-hop'
		elif self.selecteddefaultaction.get() == 3:
			self.DefaultRedirectVRFRadLabel.configure(font=("Verdana", 12),justify='left',fg='white',bg='dark green',relief='sunken')
			self.DefaultRateLimitTrafficRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.ResetDefaultRateLimit()
			self.DefaultRedirectIPRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.defaultaction = 'redirect VRF'
		elif self.selecteddefaultaction.get() == 5:
			self.defaultaction = ''
			self.ResetDefaultRateLimit()


	def GetDefaultRateLimit(self, event):
		self.DefaultRateLimit = (self.DefaultRateLimitTextBox.get(1.0,'end'))
		self.DefaultRateLimit = int(int(self.DefaultRateLimit.strip('\n'))*1000/8)
		self.DefaultRateLimit = str(self.DefaultRateLimit)
		if self.DefaultRateLimit != '':
			self.DefaultRateLimitTextBox.delete('1.0', 'end')
			self.DefaultRateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.DefaultRateLimitTextBox.insert('1.0',str(int(int(self.DefaultRateLimit)*8/1000))+'  kbps')
			self.DefaultRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
			self.DefaultRateLimitTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetDefaultRateLimit()

	def SetDefaultRateLimitTextBoxFocus(self, event):
		self.DefaultRateLimitTextBox.focus_set()
		self.DefaultRateLimitTextBox.delete('1.0','end')
		self.DefaultRateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.DefaultRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DefaultRateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')

	def InitialDefaultRateLimitTextBoxFocus(self):
		self.DefaultRateLimitTextBox.focus_set()
		self.DefaultRateLimitTextBox.delete('1.0','end')
		self.DefaultRateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.DefaultRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DefaultRateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.SetDefaultAction()
		
	def SetDefaultRateLimitTextBoxUnFocus(self, event):
		if self.DefaultRateLimit != '':
			self.DefaultRateLimitTextBox.delete('1.0', 'end')
			self.DefaultRateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.DefaultRateLimitTextBox.insert('1.0',self.DefaultRateLimit+'  kbps')
			self.DefaultRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
			self.DefaultRateLimitTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetDefaultRateLimit()

	def ResetDefaultRateLimit(self):
		self.DefaultRateLimitTextBox.delete(1.0,'end')
		self.DefaultRateLimitTextBox.configure(bg = 'white')
		self.DefaultRateLimit = ''
		self.DefaultRateLimitTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.DefaultRateLimitTextBox.insert('1.0','<kbps>')
		self.DefaultRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DefaultRateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')
		
		
	def GetDefaultFlowPolicyBandWidth(self, event):
		self.DefaultBandwidth = self.DefaultBandwidthTextBox.get(1.0,'end')
		self.DefaultBandwidth = self.DefaultBandwidth.strip('\n')
		if self.DefaultBandwidth != '':
			self.DefaultBandwidthTextBox.delete('1.0', 'end')
			self.DefaultBandwidthTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.DefaultBandwidthTextBox.insert('1.0','Default Flow Policy BW: ')
			self.DefaultBandwidthTextBox.insert('insert',self.DefaultBandwidth+'  Mbps')
			self.DefaultBandwidthTextBox.tag_add("boldcentered", "1.0", 'end')
			self.DefaultBandwidthTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetDefaultBandwidth()

	def SetDefaultBandwidthTextBoxUnFocus(self, event):
		if self.DefaultBandwidth == 0:
			self.ResetDefaultBandwidth()
		elif self.DefaultBandwidth != '':
			self.DefaultBandwidthTextBox.delete('1.0', 'end')
			self.DefaultBandwidthTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.DefaultBandwidthTextBox.insert('1.0','Flow Policy BW: ')
			self.DefaultBandwidthTextBox.insert('insert',str(self.DefaultBandwidth)+'  Mbps')
			self.DefaultBandwidthTextBox.tag_add("boldcentered", "1.0", 'end')
			self.DefaultBandwidthTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetDefaultBandwidth()

	def SetDefaultBandwidthTextBoxFocus(self, event):
		self.DefaultBandwidthTextBox.focus_set()
		self.DefaultBandwidthTextBox.delete('1.0','end')
		self.DefaultBandwidthTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.DefaultBandwidthTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DefaultBandwidthTextBox.tag_configure("boldcentered",justify='center',background='white')

	def ResetDefaultBandwidth(self):
		self.DefaultBandwidthTextBox.delete(1.0,'end')
		self.DefaultBandwidthTextBox.configure(bg = 'white')
		self.DefaultBandwidth = ''
		self.DefaultBandwidthTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.DefaultBandwidthTextBox.insert('1.0','(Click <enter/return> to set policy bandwidth)')
		self.DefaultBandwidthTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DefaultBandwidthTextBox.tag_configure("boldcentered",justify='center',background='white')


	def ProgramDefaultPolicy(self):
		self.DefaultBandwidthPolicy = []
		self.DefaultBandwidthPolicy.append('DefaultBandwidth:')
		try:
			if self.defaultaction == '':
				self.SelectActionPopup(self.window)
				pass
		except:
			self.defaultaction = ''
			self.SelectActionPopup(self.window)
			pass
		try:
			if self.DefaultBandwidth == '':
				self.SelectBandwidthPopup(self.window)
			else:
				self.DefaultBandwidthPolicy.append(self.DefaultBandwidth)
		except:
			pass
		try:
			self.DefaultBandwidthPolicy.append(self.defaultaction)
		except:
			self.defaultaction =''
			self.DefaultBandwidthPolicy.append(self.defaultaction)
		try:
			if self.defaultaction == 'rate-limit':
				if self.DefaultRateLimit == '':
					self.defaultaction == ''
					self.SelectRateLimitPopup(self.window)
				else:
					self.DefaultBandwidthPolicy.append(self.DefaultRateLimit)
		except:
			pass
		if self.defaultaction !='' and self.DefaultBandwidth !='' and self.DefaultRateLimit !='':
			for entry in self.DefaultBandwidthPolicy:
				UpdatePolicyQueue.put(entry)
			self.DefaultBandwidthTextBoxPolicy.delete('1.0', 'end')
			self.DefaultBandwidthTextBoxPolicy.configure(bg = 'dark blue', wrap='word', width=42, fg = 'white',font=("Verdana", 10,'bold'))
			self.DefaultBandwidthTextBoxPolicy.insert('end', 'Policy BW: ' +str(self.DefaultBandwidth)+ ' Mbps   Action: '+str(self.defaultaction)+'    '+str(int(int(self.DefaultRateLimit)*8/1000))+ ' kbps')
			self.DefaultBandwidthTextBoxPolicy.tag_add("centered", "1.0", 'end')
			self.DefaultBandwidthTextBoxPolicy.tag_configure("centered",justify='center')
			
		elif self.defaultaction !='' and self.DefaultBandwidth !='' and self.defaultaction !='rate-limit':
			for entry in self.DefaultBandwidthPolicy:
				UpdatePolicyQueue.put(entry)
			self.DefaultBandwidthTextBoxPolicy.delete('1.0', 'end')
			self.DefaultBandwidthTextBoxPolicy.configure(bg = 'dark blue', wrap='word', width=42, fg = 'white',font=("Verdana", 10,'bold'))
			self.DefaultBandwidthTextBoxPolicy.insert('end', 'Policy BW: ' +str(self.DefaultBandwidth)+ ' Mbps   Action: '+str(self.defaultaction))
			self.DefaultBandwidthTextBoxPolicy.tag_add("centered", "1.0", 'end')
			self.DefaultBandwidthTextBoxPolicy.tag_configure("centered",justify='center')

		self.ResetDefaultBandwidth()
		self.ResetDefaultAction()
		self.ResetDefaultRateLimit()
		
		
	def ClearDefaultSelection(self):
		self.ResetDefaultBandwidth()
		self.ResetDefaultAction()
		self.ResetDefaultRateLimit()
		
		
	def ClearDefaultPolicy(self):
		self.DefaultBandwidthPolicy = []
		self.DefaultBandwidthTextBoxPolicy.delete(1.0,'end')
		self.DefaultBandwidthTextBoxPolicy.configure(bg = 'white',width=42)
		self.DefaultBandwidthPolicy.append('DefaultBandwidth:')
		self.DefaultBandwidth = 0
		self.DefaultBandwidthPolicy.append(self.DefaultBandwidth)
		self.defaultaction =''
		self.DefaultBandwidthPolicy.append(self.defaultaction)
		self.DefaultRateLimit == ''
		self.DefaultBandwidthPolicy.append(self.DefaultRateLimit)
		for entry in self.DefaultBandwidthPolicy:
			UpdatePolicyQueue.put(entry)
	

	def ResetFlowPolicyAction(self):
		self.RedirectIPRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.RedirectVRFRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.RateLimitTrafficRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.DummyRad.select()
		self.action = ''
		
	
	def SetAction(self):
		self.action = ''
		if self.selected.get() == 1:
			self.RateLimitTrafficRadLabel.configure(font=("Verdana", 12),justify='left',fg='white',bg='dark green',relief='sunken')
			self.RedirectIPRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.RedirectVRFRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.action = 'rate-limit'
		elif self.selected.get() == 2:
			self.RedirectIPRadLabel.configure(font=("Verdana", 12),justify='left',fg='white',bg='dark green',relief='sunken')
			self.RateLimitTrafficRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.ResetRateLimit()
			self.RedirectVRFRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.action = 'redirect next-hop'
		elif self.selected.get() == 3:
			self.RedirectVRFRadLabel.configure(font=("Verdana", 12),justify='left',fg='white',bg='dark green',relief='sunken')
			self.RateLimitTrafficRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.ResetRateLimit()
			self.RedirectIPRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.action = 'redirect VRF'
		elif self.selected.get() == 5:
			self.action = ''
			self.ResetRateLimit()


	def GetFlowPolicyBandWidth(self, event):
		self.FlowPolicyBandwidth = self.BandwidthTextBox.get(1.0,'end')
		self.FlowPolicyBandwidth = self.FlowPolicyBandwidth.strip('\n')
		if self.FlowPolicyBandwidth != '':
			self.BandwidthTextBox.delete('1.0', 'end')
			self.BandwidthTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.BandwidthTextBox.insert('1.0','Flow Policy BW: ')
			self.BandwidthTextBox.insert('insert',self.FlowPolicyBandwidth+'  Mbps')
			self.BandwidthTextBox.tag_add("boldcentered", "1.0", 'end')
			self.BandwidthTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetFlowPolicyBandwidth()
			

	def SetBandwidthTextBoxUnFocus(self, event):
		if self.FlowPolicyBandwidth != '':
			self.BandwidthTextBox.delete('1.0', 'end')
			self.BandwidthTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.BandwidthTextBox.insert('1.0','Flow Policy BW: ')
			self.BandwidthTextBox.insert('insert',self.FlowPolicyBandwidth+'  Mbps')
			self.BandwidthTextBox.tag_add("boldcentered", "1.0", 'end')
			self.BandwidthTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetFlowPolicyBandwidth()

	def SetBandwidthTextBoxFocus(self, event):
		self.BandwidthTextBox.focus_set()
		self.BandwidthTextBox.delete('1.0','end')
		self.BandwidthTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.BandwidthTextBox.tag_add("boldcentered", "1.0", 'end')
		self.BandwidthTextBox.tag_configure("boldcentered",justify='center',background='white')

	def ResetFlowPolicyBandwidth(self):
		self.BandwidthTextBox.delete(1.0,'end')
		self.BandwidthTextBox.configure(bg = 'white')
		self.FlowPolicyBandwidth = ''
		self.BandwidthTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.BandwidthTextBox.insert('1.0','(Click <enter/return> to set policy bandwidth)')
		self.BandwidthTextBox.tag_add("boldcentered", "1.0", 'end')
		self.BandwidthTextBox.tag_configure("boldcentered",justify='center',background='white')
		
	def GetRateLimit(self, event):
		self.RateLimit = self.RateLimitTextBox.get(1.0,'end')
		self.RateLimit = int(int(self.RateLimit.strip('\n'))*1000/8)
		self.RateLimit = str(self.RateLimit)
		if self.RateLimit != '':
			self.RateLimitTextBox.delete('1.0', 'end')
			self.RateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.RateLimitTextBox.insert('1.0',str(int(int(self.RateLimit)*8/1000))+'  kbps')
			self.RateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
			self.RateLimitTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetRateLimit()
			
	def SetRateLimitTextBoxFocus(self, event):
		self.RateLimitTextBox.focus_set()
		self.RateLimitTextBox.delete('1.0','end')
		self.RateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.RateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.RateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')

	def InitialRateLimitTextBoxFocus(self):
		self.RateLimitTextBox.focus_set()
		self.RateLimitTextBox.delete('1.0','end')
		self.RateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.RateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.RateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.SetAction()
		
	def SetRateLimitTextBoxUnFocus(self, event):
		if self.RateLimit != '':
			self.RateLimitTextBox.delete('1.0', 'end')
			self.RateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.RateLimitTextBox.insert('1.0',self.RateLimit+'  kbps')
			self.RateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
			self.RateLimitTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetRateLimit()

	def ResetRateLimit(self):
		self.RateLimitTextBox.delete(1.0,'end')
		self.RateLimitTextBox.configure(bg = 'white')
		self.RateLimit = ''
		self.RateLimitTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.RateLimitTextBox.insert('1.0','<kbps>')
		self.RateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.RateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')

	def CurSourceSelet(self,evt):
		self.ListOfListOfBadSourcePorts = []
		values = [self.SourcePorts.get(idx) for idx in self.SourcePorts.curselection()]
		self.ListOfListOfBadSourcePorts.append(values)
		
	def CurDestinationSelet(self,evt):
		self.ListOfListOfBadDestinationPorts = []
		values = [self.DestinationPorts.get(idx) for idx in self.DestinationPorts.curselection()]
		self.ListOfListOfBadDestinationPorts.append(values)
	
	def GetBadSourcePorts(self):
		self.PortTextBox.delete('1.0', 'end')
		self.ListOfSelectedBadSourcePorts = copy.deepcopy(self.ListOfListOfBadSourcePorts[-1])
		self.ListOfListOfBadSourcePorts = []
		return self.ListOfSelectedBadSourcePorts
		  
	def GetBadDestinationPorts(self):
		self.ListOfSelectedBadDestinationPorts = copy.deepcopy(self.ListOfListOfBadDestinationPorts[-1])
		self.ListOfListOfBadDestinationPorts = []
		return self.ListOfSelectedBadDestinationPorts
	
	def AddToPolicy(self):
		self.ListOfSelectedBadSourcePorts = []
		self.ListOfSelectedBadDestinationPorts = []
		try:
			self.ListOfSelectedBadSourcePorts = self.GetBadSourcePorts()
			self.PortTextBox.configure(bg = 'dark green', fg='white')
			self.PortTextBox.insert('end', 'Source Ports To Add: \n')
			for x in self.ListOfSelectedBadSourcePorts:
				self.PortTextBox.insert('end', str(x) + ' ')

		except:
			pass
		try:
			self.ListOfSelectedBadDestinationPorts = self.GetBadDestinationPorts()
			self.PortTextBox.configure(bg = 'dark green',fg='white')
			self.PortTextBox.insert('end', '\n\nDestination Ports To Add: \n')
			for y in self.ListOfSelectedBadDestinationPorts:
				self.PortTextBox.insert('end', str(y) + ' ')
		except:
			pass
		self.ListOfSourcePortsToAdd = copy.deepcopy(self.ListOfSelectedBadSourcePorts)
		self.ListOfDestinationPortsToAdd = copy.deepcopy(self.ListOfSelectedBadDestinationPorts)
		self.SourcePorts.selection_clear(0, 'end')
		self.DestinationPorts.selection_clear(0, 'end')


	def RemoveFromPolicy(self):
		self.ListOfSelectedBadSourcePorts = []
		self.ListOfSelectedBadDestinationPorts = []
		try:
			self.ListOfSelectedBadSourcePorts = self.GetBadSourcePorts()
			self.PortTextBox.configure(bg = 'dark green', fg='white')
			self.PortTextBox.insert('end', 'Source Ports To Remove: \n')
			for x in self.ListOfSelectedBadSourcePorts:
				self.PortTextBox.insert('end', str(x) + ' ')
		except:
			pass
		try:
			self.ListOfSelectedBadDestinationPorts = self.GetBadDestinationPorts()
			self.PortTextBox.configure(bg = 'dark green',fg='white')
			self.PortTextBox.insert('end', '\n\nDestination Ports To Remove: \n')
			for y in self.ListOfSelectedBadDestinationPorts:
				self.PortTextBox.insert('end', str(y) + ' ')
		except:
			pass
		self.ListOfSourcePortsToRemove = copy.deepcopy(self.ListOfSelectedBadSourcePorts)
		self.ListOfDestinationPortsToRemove = copy.deepcopy(self.ListOfSelectedBadDestinationPorts)
		self.SourcePorts.selection_clear(0, 'end')
		self.DestinationPorts.selection_clear(0, 'end')


	def SelectActionPopup(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.popup.lift()
		self.popup.title("Missing A Policy Selection")
		self.TitleLabel=tk.Label(self.popup,text="\nYou Must select a flow policy!\n",font=("Verdana", 12,'bold'),justify='left')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.popup,text='OK!',command=self.popup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)
		

	def SelectBandwidthPopup(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.popup.lift()
		self.popup.title("Missing A Bandwidth Value")
		self.TitleLabel=tk.Label(self.popup,text="\nYou Didn't Enter a BW value!\n\n  You need to set a bandwidth value >0!!",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.popup,text='OK!',command=self.popup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)
		
		
	def SelectRateLimitPopup(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.popup.lift()
		self.popup.title("Missing A Rate-limit Value")
		self.TitleLabel=tk.Label(self.popup,text="\nYou Didn't Enter a rate-limit kbps value!\n\n  You need to set a rate-limit value >0!!",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.popup,text='OK!',command=self.popup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)


	def UpdateFlowspecPolicy(self):
		RateLimitPolicyList = []
		RedirectNHPolicyList = []
		RedirectVRFPolicyList = []

		try:
			if self.action == '':
				self.SelectActionPopup(self.window)
				pass
		except:
			self.action = ''
			self.SelectActionPopup(self.window)
			pass
		try:
			if self.action == 'rate-limit':
				try:
					if self.RateLimit == '':
						self.SelectRateLimitPopup(self.window)
						pass
					else:
						RateLimitPolicyList.append(self.action)
						self.action = ''
						try:
							self.ListOfRateLimitBadSourcePorts.extend(self.ListOfSourcePortsToAdd)
							self.ListOfRateLimitBadSourcePorts = self.remove_duplicates(self.ListOfRateLimitBadSourcePorts)
							self.ListOfRateLimitBadDestinationPorts.extend(self.ListOfDestinationPortsToAdd)
							self.ListOfRateLimitBadDestinationPorts = self.remove_duplicates(self.ListOfRateLimitBadDestinationPorts)
							self.ListOfSourcePortsToAdd = []
							self.ListOfDestinationPortsToAdd = []
						except:
							pass
						try:
							for entry in self.ListOfSourcePortsToRemove:
								self.ListOfRateLimitBadSourcePorts.remove(entry)
							for entry in self.ListOfDestinationPortsToRemove:
								self.ListOfRateLimitBadDestinationPorts.remove(entry)
							self.ListOfSourcePortsToRemove = []
							self.ListOfDestinationPortsToRemove = []
						except:
							pass
						try:
							if self.FlowPolicyBandwidth == '' and not self.RateLimitFlowPolicyBandwidth:
								self.RateLimitFlowPolicyBandwidth = 0
							elif self.RateLimitFlowPolicyBandwidth != 0 and not self.FlowPolicyBandwidth:
								self.FlowPolicyBandwidth = ''                      
							elif self.RateLimitFlowPolicyBandwidth != self.FlowPolicyBandwidth:
								self.RateLimitFlowPolicyBandwidth = self.FlowPolicyBandwidth
								self.FlowPolicyBandwidth = ''
						except:
							pass
						try:
							if self.RateLimitFlowPolicyBandwidth == 0:
								self.SelectBandwidthPopup(self.window)
								pass
							else:
								self.RateLimitPolicyTextBox.delete('1.0', 'end')
								self.RateLimitPolicyTextBox.configure(bg = 'dark blue', wrap='word', fg = 'white',font=("Verdana", 10,'bold'))
								RateLimitPolicyList.append(float(self.RateLimitFlowPolicyBandwidth))
								self.RateLimitPolicyTextBox.insert('end', 'Policy BW : '+str(self.RateLimitFlowPolicyBandwidth)+' Mbps\n')
								self.RateLimitPolicyTextBox.insert('end', 'Rate-Limit : '+str(int(int(self.RateLimit)*8/1000))+' kps\n')
								RateLimitPolicyList.append(self.ListOfRateLimitBadSourcePorts)
								RateLimitPolicyList.append(self.ListOfRateLimitBadDestinationPorts)
								RateLimitPolicyList.append(int(self.RateLimit))
								for entry in RateLimitPolicyList:
									UpdatePolicyQueue.put(entry)
								self.RateLimitPolicyTextBox.insert('end', '\nSource Ports:    ')
								for y in self.ListOfRateLimitBadSourcePorts:
									self.RateLimitPolicyTextBox.insert('end', str(y) + ', ')
								self.RateLimitPolicyTextBox.insert('end', '\n\nDestination Ports:    ')
								for y in self.ListOfRateLimitBadDestinationPorts:
									self.RateLimitPolicyTextBox.insert('end', str(y) + ', ')
						except:
							pass
				except:
					pass
					
			if self.action == 'redirect next-hop':
				RedirectNHPolicyList.append(self.action)
				self.action = ''
				try:
					self.ListOfRedirectNHBadSourcePorts.extend(self.ListOfSourcePortsToAdd)
					self.ListOfRedirectNHBadSourcePorts = self.remove_duplicates(self.ListOfRedirectNHBadSourcePorts)
					self.ListOfRedirectNHBadDestinationPorts.extend(self.ListOfDestinationPortsToAdd)
					self.ListOfRedirectNHBadDestinationPorts = self.remove_duplicates(self.ListOfRedirectNHBadDestinationPorts)
					self.ListOfSourcePortsToAdd = []
					self.ListOfDestinationPortsToAdd = []
				except:
					pass
				try:
					for entry in self.ListOfSourcePortsToRemove:
						self.ListOfRedirectNHBadSourcePorts.remove(entry)
					for entry in self.ListOfDestinationPortsToRemove:
						self.ListOfRedirectNHBadDestinationPorts.remove(entry)
					self.ListOfSourcePortsToRemove = []
					self.ListOfDestinationPortsToRemove = []
				except:
					pass
				try:
					if self.FlowPolicyBandwidth == '' and not self.RedirectNHFlowPolicyBandwidth:
						self.RedirectNHFlowPolicyBandwidth = 0
					elif self.RedirectNHFlowPolicyBandwidth != 0 and not self.FlowPolicyBandwidth:
						self.FlowPolicyBandwidth = ''    
					elif self.RedirectNHFlowPolicyBandwidth != self.FlowPolicyBandwidth:
						self.RedirectNHFlowPolicyBandwidth = self.FlowPolicyBandwidth
						self.FlowPolicyBandwidth = ''

				except:
					pass
				try:
					if self.RedirectNHFlowPolicyBandwidth == 0:
						self.SelectBandwidthPopup(self.window)
						pass
					else:
						self.RedirectNHPolicyTextBox.delete('1.0', 'end')
						self.RedirectNHPolicyTextBox.configure(bg = 'dark blue', wrap='word', fg = 'white',font=("Verdana", 10,'bold'))
						RedirectNHPolicyList.append(float(self.RedirectNHFlowPolicyBandwidth))
						self.RedirectNHPolicyTextBox.insert('end', 'Policy BW : '+str(self.RedirectNHFlowPolicyBandwidth)+' Mbps\n')
						RedirectNHPolicyList.append(self.ListOfRedirectNHBadSourcePorts)
						RedirectNHPolicyList.append(self.ListOfRedirectNHBadDestinationPorts)
						for entry in RedirectNHPolicyList:
							UpdatePolicyQueue.put(entry)
						self.RedirectNHPolicyTextBox.insert('end', '\nSource Ports:    ')
						for y in self.ListOfRedirectNHBadSourcePorts:
							self.RedirectNHPolicyTextBox.insert('end', str(y) + ', ')
						self.RedirectNHPolicyTextBox.insert('end', '\n\nDestination Ports:    ')
						for y in self.ListOfRedirectNHBadDestinationPorts:
							self.RedirectNHPolicyTextBox.insert('end', str(y) + ', ')
				except:
					pass
					
			if self.action == 'redirect VRF':
				RedirectVRFPolicyList.append(self.action)
				self.action = ''
				try:
					self.ListOfRedirectVRFBadSourcePorts.extend(self.ListOfSourcePortsToAdd)
					self.ListOfRedirectVRFBadSourcePorts = self.remove_duplicates(self.ListOfRedirectVRFBadSourcePorts)
					self.ListOfRedirectVRFBadDestinationPorts.extend(self.ListOfDestinationPortsToAdd)
					self.ListOfRedirectVRFBadDestinationPorts = self.remove_duplicates(self.ListOfRedirectVRFBadDestinationPorts)
					self.ListOfSourcePortsToAdd = []
					self.ListOfDestinationPortsToAdd = []
				except:
					pass
				try:
					for entry in self.ListOfSourcePortsToRemove:
						self.ListOfRedirectVRFBadSourcePorts.remove(entry)
					for entry in self.ListOfDestinationPortsToRemove:
						self.ListOfRedirectVRFBadDestinationPorts.remove(entry)
					self.ListOfSourcePortsToRemove = []
					self.ListOfDestinationPortsToRemove = []
				except:
					pass
				try:
					if self.FlowPolicyBandwidth == '' and not self.RedirectVRFFlowPolicyBandwidth:
					   self.RedirectVRFFlowPolicyBandwidth = 0
					elif self.RedirectVRFFlowPolicyBandwidth != 0 and not self.FlowPolicyBandwidth:
						self.FlowPolicyBandwidth = ''    
					elif self.RedirectVRFFlowPolicyBandwidth != self.FlowPolicyBandwidth:
						self.RedirectVRFFlowPolicyBandwidth = self.FlowPolicyBandwidth
						self.FlowPolicyBandwidth = ''
				except:
					pass
				try:
					if self.RedirectVRFFlowPolicyBandwidth == 0:
						self.SelectBandwidthPopup(self.window)
						pass
					else:	
						self.RedirectVRFPolicyTextBox.delete('1.0', 'end')
						self.RedirectVRFPolicyTextBox.configure(bg = 'dark blue', wrap='word', fg = 'white',font=("Verdana", 10,'bold'))
						RedirectVRFPolicyList.append(float(self.RedirectVRFFlowPolicyBandwidth))
						self.RedirectVRFPolicyTextBox.insert('end', 'Policy BW : '+str(self.RedirectVRFFlowPolicyBandwidth)+'\n')
						RedirectVRFPolicyList.append(self.ListOfRedirectVRFBadSourcePorts)
						RedirectVRFPolicyList.append(self.ListOfRedirectVRFBadDestinationPorts)
						for entry in RedirectVRFPolicyList:
							UpdatePolicyQueue.put(entry)
						self.RedirectVRFPolicyTextBox.insert('end', '\nSource Ports:    ')
						for y in self.ListOfRedirectVRFBadSourcePorts:
							self.RedirectVRFPolicyTextBox.insert('end', str(y) + ', ')
						self.RedirectVRFPolicyTextBox.insert('end', '\n\nDestination Ports:    ')
						for y in self.ListOfRedirectVRFBadDestinationPorts:
							self.RedirectVRFPolicyTextBox.insert('end', str(y) + ', ')
				except:
					pass
		except:
			pass
		self.PortTextBox.delete(1.0,'end')
		self.PortTextBox.configure(bg = 'white')
		self.ResetFlowPolicyBandwidth()
		self.ResetRateLimit()
		self.ResetFlowPolicyAction()	

	def ClearPolicySelection(self):
		self.PortTextBox.delete(1.0,'end')
		self.PortTextBox.configure(bg = 'white')
		self.ResetFlowPolicyBandwidth()
		self.ResetRateLimit()
		self.ResetFlowPolicyAction()
		
	def ClearRateLimitPolicy(self):
		self.RateLimitPolicyClear = ['rate-limit', 0, [], []]
		self.RateLimitPolicyTextBox.delete(1.0,'end')
		self.RateLimitPolicyTextBox.configure(bg = 'white')
		self.ListOfRateLimitBadSourcePorts = []
		self.ListOfRateLimitBadDestinationPorts = []
		self.RateLimitFlowPolicyBandwidth = ''
		for entry in self.RateLimitPolicyClear:
			UpdatePolicyQueue.put(entry)
	
	def ClearRedirectNHPolicy(self):
		self.RedirectNHPolicyClear = ['redirect next-hop', 0, [], []]
		self.RedirectNHPolicyTextBox.delete(1.0,'end')
		self.RedirectNHPolicyTextBox.configure(bg = 'white')
		self.ListOfRedirectNHBadSourcePorts = []
		self.ListOfRedirectNHBadDestinationPorts = []
		self.RedirectNHFlowPolicyBandwidth = ''
		for entry in self.RedirectNHPolicyClear:
			UpdatePolicyQueue.put(entry)
	
	def ClearRedirectVRFPolicy(self):
		self.RedirectVRFPolicyClear = ['redirect VRF', 0, [], []]
		self.RedirectVRFPolicyTextBox.delete(1.0,'end')
		self.RedirectVRFPolicyTextBox.configure(bg = 'white')
		self.ListOfRedirectVRFBadSourcePorts = []
		self.ListOfRedirectVRFBadDestinationPorts = []
		self.RedirectVRFFlowPolicyBandwidth = ''
		for entry in self.RedirectVRFPolicyClear:
			UpdatePolicyQueue.put(entry)
	
	def remove_duplicates(self,l):
		return list(set(l))

	def RestartPolicyManager(self):
		SignalResetQueue.put('RESET SIGNALED')
		self.ClearPolicySelection()
		self.ClearRedirectVRFPolicy()
		self.ClearRedirectNHPolicy()
		self.ClearRateLimitPolicy()
		self.ClearDefaultPolicy()
		for Router in topo_vars['EdgeRouters']:
			try:
				print (" \n\n Hard Clearing the Controller BGP peering Session")
				command = 'neighbor '+str(Router['RouterID'])+  ' teardown 2'
				r = requests.post(exabgpurl, data={'command': command})
				time.sleep(.2)
			except:
				command = 'restart'
				print ("\n\nProblem With ExaBgp Restarting ExaBgp ........\n\n\n")
		print ("\n\nProgramming Sflow Collector ........\n\n\n")
		while True:
			try:
				r=requests.put('http://%s:8008/flow/%s/json' % (sflowIP,'ipdest'),data=json.dumps(ipflow))
				False
				print ("\n\nDone! ........\n\n\n")
				print ("\n\nFlowspec Controller Running! ........\n\n\n")
				return
			except:
				pass

class ShowManualFlowspecRoutesPopup(object):
	def __init__(self,ManualRouteDisplayQueue,ParentWindow):
		global FlowPopUpRefreshInterval
		self.popup = tk.Toplevel(ParentWindow)
		self.popup.grid_columnconfigure(0, weight=1)
		self.popup.grid_rowconfigure(2, weight=1)
		width = ParentWindow.winfo_width()
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()))
		self.popup.lift()
		self.NumberOfFlowRoutes = 0
		self.popup.title("Active Manual Flowspec Rules Programmed on Edge Routers")
		self.TitleLabel=tk.Label(self.popup,text="### Active Manual Flowspec Rules Programmed on Edge Routers###\n",font=("Verdana", 16),justify='left')
		self.TitleLabel.grid(column=0, row=0,columnspan=3, sticky='n')
		self.FlowCount=tk.Label(self.popup,text='Number of Active Flow Routes '+str(self.NumberOfFlowRoutes)+'\n',font=("Verdana", 14),justify='center')
		self.FlowCount.grid(column=0, row=1,columnspan=3, sticky='new')
		self.text_wid = tk.Text(self.popup,relief = 'raised', height=20,width=130,borderwidth=3)
		self.text_wid.insert('end','Neighbor		Source			Destination			Protocol		Source Port		Destination Port		Active Action\n\n')
		self.scroll = tk.Scrollbar(self.popup, command=self.text_wid.yview)
		self.text_wid.grid(column=0, columnspan=3,row=2,sticky='nswe', padx=10, pady=5)
		self.scroll.grid(column=0, columnspan=3,row=2,sticky='nse',padx=10)
		self.popup.after(100,self.ManualRouteDisplayQueuePoll,ManualRouteDisplayQueue)
		self.close= tk.Button(self.popup,text='Close Window',command=self.cleanup,font=("Verdana",12,'bold'))
		self.close.grid(row=5,column=0,columnspan=3,pady=10)
		
	def ManualRouteDisplayQueuePoll(self,c_queue):
		try:
			ListOfManualRoutes = c_queue.get(0)
			self.text_wid.delete('1.0', 'end')
			self.text_wid.insert('end','Neighbor		Source			Destination			Protocol		Source Port		Destination Port		Active Action\n\n')
			self.NumberOfFlowRoutes = 0
			for line in ListOfManualRoutes:
				self.NumberOfFlowRoutes +=1
				for r in (('neighbor ',''),(' source-port ',''), (' destination-port ',''),(' source ','		'), (' destination ','			'), ('protocol ','			'),('[',''),(']','		')):
					line = line.replace(*r)
				self.text_wid.insert('end', line+'\n')
			self.FlowCount=tk.Label(self.popup,text='Number of Active Flow Routes '+str(self.NumberOfFlowRoutes)+'\n',font=("Verdana", 14),justify='center')
			self.FlowCount.grid(column=0, row=1,columnspan=3, sticky='new')
		except Empty:
			pass
		finally:
			self.text_wid.configure(bg ='dark blue',fg = 'white',font=("Verdana", 10, 'bold'))
			self.popup.after((FlowPopUpRefreshInterval*1000), self.ManualRouteDisplayQueuePoll, c_queue)
			
	def cleanup(self):
		self.popup.destroy()
		

class ProgramFlowSpecRuleClass(object):
	def __init__(self,ManualRouteQueue, ManualRouteDisplayQueue):
		BG0 = 'white' #White Canvas (interior)
		BG1 = '#4e88e5' #Blue scheme
		self.ManualFlowRoute = []
		self.ManualRouteRateLimit = ''
		self.SourcePrefix = ''
		self.SourcePort = ''
		self.DestinationPort = ''
		self.DestinationPrefix = ''
		self.selected = tk.IntVar()
		self.actionselected = tk.IntVar()
		self.manualroutewindow = tk.Toplevel()
		self.manualroutewindow.configure(background=BG0)
		self.ProtocolStringVariable = tk.StringVar()
		self.PeerIPAddressStringVariable = tk.StringVar()
		self.ProtocolList = []					# Example Format: ProtocolList = [{'TCP':6},{'UDP':17}]
		self.ListOfLERs = []
		try:
			for entry in topo_vars['IPProtocol']:
				self.ProtocolList.append(entry)
		except:
			pass
		try:
			for Router in topo_vars['EdgeRouters']:
				self.ListOfLERs.append(Router['RouterID'])
		except:
			pass
		self.ProtocolOptionsMenu = tk.OptionMenu(self.manualroutewindow, self.ProtocolStringVariable,*self.ProtocolList)
		self.PeerIPAddressOptionsMenu = tk.OptionMenu(self.manualroutewindow, self.PeerIPAddressStringVariable,*self.ListOfLERs)
		self.manualroutewindow.title("Program Manual BGP Flowspec Rule")
		self.announce = tk.Radiobutton(self.manualroutewindow,text='Announce Rule', value=1, variable=self.selected,font=("Verdana",12,'bold'),background=BG0)
		self.withdraw = tk.Radiobutton(self.manualroutewindow,text='Withdraw Rule', value=2, variable=self.selected,font=("Verdana",12,'bold'), background=BG0)
		self.announce.grid(column=0,row=0,sticky='w')
		self.withdraw.grid(column=0,row=1,sticky='w')
		self.ManualAnnounceWithdrawDummyRad = tk.Radiobutton(self.manualroutewindow, value=5, variable=self.selected)
		
		self.PeerIPAddressStringVariable.set("Select BGP FS Peer")
		self.PeerIPAddressOptionsMenu.grid(row=2,column=1,padx=5)
		self.PeerIPAddressOptionsMenu.config(width=25,justify='center', font=("Verdana",10))
	
		self.SourcePrefixTextBox = tk.Text(self.manualroutewindow, background=BG0, height = 1, width = 30, borderwidth=1, relief="ridge")
		self.SourcePrefixTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.SourcePrefixTextBox.insert('1.0','<Source Prefix/Mask>')
		self.SourcePrefixTextBox.tag_add("boldcentered", "1.0", 'end')
		self.SourcePrefixTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.SourcePrefixTextBox.bind("<Button-1>", self.SetSourcePrefixTextBoxFocus)
		self.SourcePrefixTextBox.bind("<Return>", self.GetSourcePrefix)
		self.SourcePrefixTextBox.bind("<FocusOut>", self.SetSourcePrefixTextBoxUnFocus)
		self.SourcePrefixTextBox.bind("<FocusIn>", self.SetSourcePrefixTextBoxFocus)
		self.SourcePrefixTextBox.grid(column=2, row=2, padx=5)
		
		self.DestinationPrefixTextBox = tk.Text(self.manualroutewindow, background=BG0, height = 1, width = 30, borderwidth=1, relief="ridge")
		self.DestinationPrefixTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.DestinationPrefixTextBox.insert('1.0','<Destination Prefix/Mask>')
		self.DestinationPrefixTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DestinationPrefixTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.DestinationPrefixTextBox.bind("<Button-1>", self.SetDestinationPrefixTextBoxFocus)
		self.DestinationPrefixTextBox.bind("<Return>", self.GetDestinationPrefix)
		self.DestinationPrefixTextBox.bind("<FocusOut>", self.SetDestinationPrefixTextBoxUnFocus)
		self.DestinationPrefixTextBox.bind("<FocusIn>", self.SetDestinationPrefixTextBoxFocus)
		self.DestinationPrefixTextBox.grid(column=3, row=2, padx=5)		
		
		self.ProtocolStringVariable.set("Select Protocol")
		self.ProtocolOptionsMenu.grid(row=2,column=4,padx=5)
		self.ProtocolOptionsMenu.config(width=15,justify='center', font=("Verdana",10) )
		
		self.SourcePortTextBox = tk.Text(self.manualroutewindow, background=BG0, height = 1, width = 30, borderwidth=1, relief="ridge")
		self.SourcePortTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.SourcePortTextBox.insert('1.0','<Source Port(s)> (a,b,d-f,>g,<h)')
		self.SourcePortTextBox.tag_add("boldcentered", "1.0", 'end')
		self.SourcePortTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.SourcePortTextBox.bind("<Button-1>", self.SetSourcePortTextBoxFocus)
		self.SourcePortTextBox.bind("<Return>", self.GetSourcePort)
		self.SourcePortTextBox.bind("<FocusOut>", self.SetSourcePortTextBoxUnFocus)
		self.SourcePortTextBox.bind("<FocusIn>", self.SetSourcePortTextBoxFocus)
		self.SourcePortTextBox.grid(column=5, row=2, padx=5)

		self.DestinationPortTextBox = tk.Text(self.manualroutewindow, background=BG0, height = 1, width = 35, borderwidth=1, relief="ridge")
		self.DestinationPortTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.DestinationPortTextBox.insert('1.0','<Destination Port(s)> (a,b,d-f,>g,<h)')
		self.DestinationPortTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DestinationPortTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.DestinationPortTextBox.bind("<Button-1>", self.SetDestinationPortTextBoxFocus)
		self.DestinationPortTextBox.bind("<Return>", self.GetDestinationPort)
		self.DestinationPortTextBox.bind("<FocusOut>", self.SetDestinationPortTextBoxUnFocus)
		self.DestinationPortTextBox.bind("<FocusIn>", self.SetDestinationPortTextBoxFocus)
		self.DestinationPortTextBox.grid(column=6, row=2, padx=5)

		self.ManualRouteRateLimitTrafficRad = tk.Radiobutton(self.manualroutewindow, background=BG0,value=1, variable=self.actionselected, command=self.InitialManualRouteRateLimitTextBoxFocus)
		self.ManualRouteRateLimitTrafficRadLabel = tk.Label(self.manualroutewindow,width=12,text='Rate-Limit',font=("Verdana",12),fg='black',background='grey95',relief='ridge')
		self.ManualRouteRedirectIPRad = tk.Radiobutton(self.manualroutewindow,background=BG0,value=2, variable=self.actionselected, command=self.SetManualRouteAction)
		self.ManualRouteRedirectIPRadLabel = tk.Label(self.manualroutewindow,width=20,text='Redirect To Next Hop',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.ManualRouteRedirectVRFRad = tk.Radiobutton(self.manualroutewindow,background=BG0,value=3, variable=self.actionselected, command=self.SetManualRouteAction)
		self.ManualRouteRedirectVRFRadLabel = tk.Label(self.manualroutewindow,width=20,text='Redirect To VRF',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.ManualRouteRateLimitTrafficRad.grid(column=1, row=3,sticky='w',padx=10)
		self.ManualRouteRedirectIPRad.grid(column=2, row=3, sticky='w',padx=10)
		self.ManualRouteRedirectVRFRad.grid(column=3, row=3,sticky='w',padx=10)
		self.ManualRouteRateLimitTrafficRadLabel.grid(column=1, row=3, sticky='w', padx=50)
		self.ManualRouteRedirectIPRadLabel.grid(column=2, row=3,sticky='w',padx=50)
		self.ManualRouteRedirectVRFRadLabel.grid(column=3, row=3,sticky='w',padx=50)
		self.ManualRouteDummyRad = tk.Radiobutton(self.manualroutewindow, value=5, variable=self.actionselected)
		
		self.SpacerLabel=tk.Label(self.manualroutewindow,text="\n",font=("Verdana", 12),justify='right',background=BG0)
		self.SpacerLabel.grid(column=3, columnspan=7,row=4,sticky='w')		
		
		self.ProgramRoute = tk.Button(self.manualroutewindow,text="Program Rule",command=self.callback,font=("Verdana",12,'bold'))
		self.ProgramRoute.grid(row=5,column=0,padx=10)
		
		self.close= tk.Button(self.manualroutewindow,text='Close Window',command=self.cleanup,font=("Verdana",12,'bold'))
		self.close.grid(row=6,column=0,padx=10,pady=5)

		ClearEntries=tk.Button(self.manualroutewindow, text="Clear Selection",width=25,command=self.ClearAllEntries,font=("Verdana", 12, 'italic bold'),fg='white',bg='dark grey')
		ClearEntries.grid(column=1,sticky='w',row=5,padx=10)

		DeleteManualFlowspecRoutes=tk.Button(self.manualroutewindow, text="Delete All Manual Routes",width=25,command=self.DeleteAllManualFlowSpecRoutes,font=("Verdana", 12, 'bold'),fg='white',bg='dark grey')
		DeleteManualFlowspecRoutes.grid(column=2,sticky='w',row=5,padx=10)

		FlowspecManualRoutes=tk.Button(self.manualroutewindow, text="Show Manual Flowspec Routes Click Here (Pop Up)",width=53,command=self.ShowFlowspecManualRoutesPopup,font=("Verdana", 12, 'bold'),fg='white',bg='dark grey')
		FlowspecManualRoutes.grid(column=1,columnspan=2,sticky='w',row=6,padx=10)
		
		self.ManualRouteRateLimitTextBox = tk.Text(self.manualroutewindow, background=BG0, height = 1, width = 8, borderwidth=1, relief="ridge")
		self.ManualRouteRateLimitTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.ManualRouteRateLimitTextBox.insert('1.0','<kbps>')
		self.ManualRouteRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.ManualRouteRateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.ManualRouteRateLimitTextBox.bind("<Button-1>", self.SetManualRouteRateLimitTextBoxFocus)
		self.ManualRouteRateLimitTextBox.bind("<Return>", self.GetManualRouteRateLimit)
		self.ManualRouteRateLimitTextBox.bind("<FocusOut>", self.SetManualRouteRateLimitTextBoxUnFocus)
		self.ManualRouteRateLimitTextBox.bind("<FocusIn>", self.SetManualRouteRateLimitTextBoxFocus)
		self.ManualRouteRateLimitTextBox.grid(column=1, row=3,sticky='e', padx=10)
		
	def ShowFlowspecManualRoutesPopup(self):
		popup = ShowManualFlowspecRoutesPopup(ManualRouteDisplayQueue,self.manualroutewindow)
		
	def SetManualRouteAction(self):
		self.ManualRouteaction = ''
		if self.actionselected.get() == 1:
			self.ManualRouteRateLimitTrafficRadLabel.configure(font=("Verdana", 12),justify='left',fg='white',bg='dark green',relief='sunken')
			self.ManualRouteRedirectIPRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.ManualRouteRedirectVRFRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.action = 'rate-limit'
		elif self.actionselected.get() == 2:
			self.ManualRouteRedirectIPRadLabel.configure(font=("Verdana", 12),justify='left',fg='white',bg='dark green',relief='sunken')
			self.ManualRouteRateLimitTrafficRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.ResetManualRouteRateLimit()
			self.ManualRouteRedirectVRFRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.action = 'redirect next-hop'
		elif self.actionselected.get() == 3:
			self.ManualRouteRedirectVRFRadLabel.configure(font=("Verdana", 12),justify='left',fg='white',bg='dark green',relief='sunken')
			self.ManualRouteRateLimitTrafficRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.ResetManualRouteRateLimit()
			self.ManualRouteRedirectIPRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
			self.action = 'redirect VRF'
		elif self.actionselected.get() == 5:
			self.action = ''
			self.ResetManualRouteRateLimit()
			


	def callback(self):
		self.AddRemove = self.selected.get()
		if self.AddRemove == 5:
			self.AnnounceOrWithdrawWindow(self.manualroutewindow)
			return
		elif self.AddRemove:
			pass
		else:
			self.AnnounceOrWithdrawWindow(self.manualroutewindow)
			return
		self.PeerIPAddressString = str(self.PeerIPAddressStringVariable.get())
		if self.PeerIPAddressString != "Select BGP FS Peer":
			self.PeerIPAddressString = self.PeerIPAddressString.strip('\n')
		else:
			self.PeerIPAddressStringVariable.set("Select BGP FS Peer")
			self.SelectPeerIPAddressWindow(self.manualroutewindow)
			return
		try:
			if self.return_network(self.DestinationPrefix).version == 4 and self.return_network(self.SourcePrefix).version == 4:
				pass
			elif self.return_network(self.DestinationPrefix).version == 6 and self.return_network(self.SourcePrefix).version == 6:
				pass
			else:
				self.MatchNetworksWindow(self.manualroutewindow)
				return
		except:
			self.MatchNetworksWindow(self.manualroutewindow)
			return
			
		self.ProtocolString = str(self.ProtocolStringVariable.get())
		if self.ProtocolString != "Select Protocol":
			self.ProtocolString = self.ProtocolString.split(': ')[1][:-1]
			self.ProtocolString = self.ProtocolString.strip('\n')
		else:
			self.ProtocolStringVariable.set("Select Protocol")
			self.SelectProtocolWindow(self.manualroutewindow)
			return
		
		if self.SourcePort:
			pass
		else:
			self.SourcePortWindow(self.manualroutewindow)
			return
		
		if self.DestinationPort:
			pass
		else:
			self.DestinationPortWindow(self.manualroutewindow)
			return

		try:
			if self.actionselected.get() == 1:
				try:
					self.action = 'rate-limit ' + str(int(int(self.ManualRouteRateLimit)*1000/8))
				except:
					self.SelectRateLimitWindow(self.manualroutewindow)
					return
			elif self.actionselected.get() == 2:
				self.action = 'redirect next-hop'
			elif self.actionselected.get() == 3:
				self.action = 'redirect VRF'
			self.ManualFlowRouteString = self.PeerIPAddressString +'@@@@@@' +str(self.SourcePrefix) +'@@@@@@'+str(self.DestinationPrefix )+'@@@@@@'+str(self.ProtocolString)+'@@@@@@'+str(self.SourcePortString)+'@@@@@@'+str(self.DestinationPortString)+'@@@@@@'+str(self.AddRemove)+'@@@@@@'+str(self.action)
			self.ManualFlowRoute = self.ManualFlowRouteString.split('@@@@@@')
			for entry in self.ManualFlowRoute:
				ManualRouteQueue.put(entry)
			self.progress = ttk.Progressbar(self.manualroutewindow, orient="horizontal",
									length=400, mode="determinate")
			self.progress.grid(row=4,column=1,columnspan=10,pady=10)
			self.bytes = 0
			self.maxbytes = 0
			self.start()
		except:
			self.ChooseAnActionWindow(self.manualroutewindow)
			return

	
	def start(self):
		self.progress["value"] = 0
		self.maxbytes = 5000
		self.progress["maximum"] = 5000
		self.read_bytes()
	
	def read_bytes(self):
		'''simulate reading 200 bytes; update progress bar'''
		self.bytes += 200
		self.progress["value"] = self.bytes
		if self.bytes < self.maxbytes:
			# read more bytes after 10 ms
			self.manualroutewindow.after(10, self.read_bytes)
		else:
			self.progress.destroy()
	
	def cleanup(self):
		self.manualroutewindow.destroy()
		
	
		
	######## Source Prefix Functions #######
		
	def GetSourcePrefix(self, event):
		self.SourcePrefix = self.SourcePrefixTextBox.get(1.0,'end')
		self.SourcePrefix = self.SourcePrefix.strip('\n')
		if self.SourcePrefix != '':
			if self.is_valid_network(self.SourcePrefix):
				self.SourcePrefix = self.return_network(self.SourcePrefix)
				self.SourcePrefixTextBox.delete('1.0', 'end')
				self.SourcePrefixTextBox.configure(font=("Verdana",10,'bold'),fg='white')
				self.SourcePrefixTextBox.insert('1.0',self.SourcePrefix)
				self.SourcePrefixTextBox.tag_add("boldcentered", "1.0", 'end')
				self.SourcePrefixTextBox.tag_configure("boldcentered", background='dark green',justify='center')
				self.SetDestinationPrefixTextBoxFocus(self)
				return 'break'
			else:
				self.ResetSourcePrefix()
				self.IncorrectPrefixWindow(self.manualroutewindow)
		else:
			self.ResetSourcePrefix()

	def SetSourcePrefixTextBoxFocus(self, event):
		self.SourcePrefixTextBox.focus_set()
		self.SourcePrefixTextBox.delete('1.0','end')
		self.SourcePrefixTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.SourcePrefixTextBox.tag_add("boldcentered", "1.0", 'end')
		self.SourcePrefixTextBox.tag_configure("boldcentered",justify='center',background='white')

		
	def SetSourcePrefixTextBoxUnFocus(self, event):
		if self.SourcePrefix != '':
			self.SourcePrefixTextBox.delete('1.0', 'end')
			self.SourcePrefixTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.SourcePrefixTextBox.insert('1.0',self.SourcePrefix)
			self.SourcePrefixTextBox.tag_add("boldcentered", "1.0", 'end')
			self.SourcePrefixTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetSourcePrefix()

	def ResetSourcePrefix(self):
		self.SourcePrefixTextBox.delete(1.0,'end')
		self.SourcePrefixTextBox.configure(bg = 'white')
		self.SourcePrefix = ''
		self.SourcePrefixTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.SourcePrefixTextBox.insert('1.0','<Source Prefix/Mask>')
		self.SourcePrefixTextBox.tag_add("boldcentered", "1.0", 'end')
		self.SourcePrefixTextBox.tag_configure("boldcentered",justify='center',background='white')

	######## End of Source Prefix Functions #######
	

	######## Destination Prefix Functions #######
		
	def GetDestinationPrefix(self, event):
		self.DestinationPrefix = self.DestinationPrefixTextBox.get(1.0,'end')
		self.DestinationPrefix = self.DestinationPrefix.strip('\n')
		if self.DestinationPrefix != '':
			if self.is_valid_network(self.DestinationPrefix):
				self.DestinationPrefix = self.return_network(self.DestinationPrefix)
				self.DestinationPrefixTextBox.delete('1.0', 'end')
				self.DestinationPrefixTextBox.configure(font=("Verdana",10,'bold'),fg='white')
				self.DestinationPrefixTextBox.insert('1.0',self.DestinationPrefix)
				self.DestinationPrefixTextBox.tag_add("boldcentered", "1.0", 'end')
				self.DestinationPrefixTextBox.tag_configure("boldcentered", background='dark green',justify='center')
				self.ProtocolOptionsMenu.focus_set()
				return 'break'
			else:
				self.ResetDestinationPrefix()
				self.IncorrectPrefixWindow(self.manualroutewindow)
		else:
			self.ResetDestinationPrefix()

	def SetDestinationPrefixTextBoxFocus(self, event):
		self.DestinationPrefixTextBox.focus_set()
		self.DestinationPrefixTextBox.delete('1.0','end')
		self.DestinationPrefixTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.DestinationPrefixTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DestinationPrefixTextBox.tag_configure("boldcentered",justify='center',background='white')

		
	def SetDestinationPrefixTextBoxUnFocus(self, event):
		if self.DestinationPrefix != '':
			self.DestinationPrefixTextBox.delete('1.0', 'end')
			self.DestinationPrefixTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.DestinationPrefixTextBox.insert('1.0',self.DestinationPrefix)
			self.DestinationPrefixTextBox.tag_add("boldcentered", "1.0", 'end')
			self.DestinationPrefixTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetDestinationPrefix()

	def ResetDestinationPrefix(self):
		self.DestinationPrefixTextBox.delete(1.0,'end')
		self.DestinationPrefixTextBox.configure(bg = 'white')
		self.DestinationPrefix = ''
		self.DestinationPrefixTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.DestinationPrefixTextBox.insert('1.0','<Destination Prefix/Mask>')
		self.DestinationPrefixTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DestinationPrefixTextBox.tag_configure("boldcentered",justify='center',background='white')

	######## End of Destination Prefix Functions #######
	

	######## Source Port Functions #######
	
	def GetSourcePort(self, event):
		self.SourcePort = self.SourcePortTextBox.get(1.0,'end')
		self.SourcePort = self.SourcePort.strip('\n')
		if self.SourcePort != '':
			try:
				self.SourcePortList2 = []
				self.SourcePortList3 = []
				self.SourcePortList4 = []
				self.SourcePortList2 = re.split(',',self.SourcePort)
				for entry in self.SourcePortList2:
					entry1 = entry.replace('-','&<')
					self.SourcePortList3.append(entry1)
				for entry in self.SourcePortList3:
					if '&<' in entry:
						entry = '>'+entry
						self.SourcePortList4.append(entry)
					elif '>' in entry:
						self.SourcePortList4.append(entry)
					elif '<' in entry:
						self.SourcePortList4.append(entry)
					elif entry.isnumeric():
						entry = '='+entry
						self.SourcePortList4.append(entry)
					else:
						self.ResetSourcePort()
						self.SourcePortWindow(self.manualroutewindow)
			except:
				self.ResetSourcePort()
				self.IncorrectPeerWindow(self.manualroutewindow)
			self.SourcePortString = ' '.join(self.SourcePortList4)
			self.SourcePortTextBox.delete('1.0', 'end')
			self.SourcePortTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.SourcePortTextBox.insert('1.0',self.SourcePort)
			self.SourcePortTextBox.tag_add("boldcentered", "1.0", 'end')
			self.SourcePortTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			self.SetDestinationPortTextBoxFocus(self)
			return 'break'
		else:
			self.ResetSourcePort()
			self.SourcePortWindow(self.manualroutewindow)

	def SetSourcePortTextBoxFocus(self, event):
		self.SourcePortTextBox.focus_set()
		self.SourcePortTextBox.delete('1.0','end')
		self.SourcePortTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.SourcePortTextBox.tag_add("boldcentered", "1.0", 'end')
		self.SourcePortTextBox.tag_configure("boldcentered",justify='center',background='white')

		
	def SetSourcePortTextBoxUnFocus(self, event):
		if self.SourcePort != '':
			self.SourcePortTextBox.delete('1.0', 'end')
			self.SourcePortTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.SourcePortTextBox.insert('1.0',self.SourcePort)
			self.SourcePortTextBox.tag_add("boldcentered", "1.0", 'end')
			self.SourcePortTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetSourcePort()

	def ResetSourcePort(self):
		self.SourcePortTextBox.delete(1.0,'end')
		self.SourcePortTextBox.configure(bg = 'white')
		self.SourcePort = ''
		self.SourcePortTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.SourcePortTextBox.insert('1.0','<Source Port(s)> (a,b,d-f,>g,<h)')
		self.SourcePortTextBox.tag_add("boldcentered", "1.0", 'end')
		self.SourcePortTextBox.tag_configure("boldcentered",justify='center',background='white')
		
	######## End of Source Port Functions #######	

	######## Destination Port Functions #######
	
	def GetDestinationPort(self, event):
		self.DestinationPort = self.DestinationPortTextBox.get(1.0,'end')
		self.DestinationPort = self.DestinationPort.strip('\n')
		if self.DestinationPort != '':
			try:
				self.DestinationPortList2 = []
				self.DestinationPortList3 = []
				self.DestinationPortList4 = []
				self.DestinationPortList2 = re.split(',',self.DestinationPort)
				for entry in self.DestinationPortList2:
					entry1 = entry.replace('-','&<')
					self.DestinationPortList3.append(entry1)
				for entry in self.DestinationPortList3:
					if '&<' in entry:
						entry = '>'+entry
						self.DestinationPortList4.append(entry)
					elif '>' in entry:
						self.DestinationPortList4.append(entry)
					elif '<' in entry:
						self.DestinationPortList4.append(entry)
					elif entry.isnumeric():
						entry = '='+entry
						self.DestinationPortList4.append(entry)
					else:
						self.ResetDestinationPort()
						self.DestinationPortWindow(self.manualroutewindow)
			except:
				self.ResetDestinationPort()
				self.IncorrectPeerWindow(self.manualroutewindow)
			self.DestinationPortString = ' '.join(self.DestinationPortList4)
			self.DestinationPortTextBox.delete('1.0', 'end')
			self.DestinationPortTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.DestinationPortTextBox.insert('1.0',self.DestinationPort)
			self.DestinationPortTextBox.tag_add("boldcentered", "1.0", 'end')
			self.DestinationPortTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			self.ManualRouteRateLimitTrafficRad.focus_set()
			return 'break'
		else:
			self.ResetDestinationPort()
			self.DestinationPortWindow(self.manualroutewindow)

	def SetDestinationPortTextBoxFocus(self, event):
		self.DestinationPortTextBox.focus_set()
		self.DestinationPortTextBox.delete('1.0','end')
		self.DestinationPortTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.DestinationPortTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DestinationPortTextBox.tag_configure("boldcentered",justify='center',background='white')

		
	def SetDestinationPortTextBoxUnFocus(self, event):
		if self.DestinationPort != '':
			self.DestinationPortTextBox.delete('1.0', 'end')
			self.DestinationPortTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.DestinationPortTextBox.insert('1.0',self.DestinationPort)
			self.DestinationPortTextBox.tag_add("boldcentered", "1.0", 'end')
			self.DestinationPortTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetDestinationPort()

	def ResetDestinationPort(self):
		self.DestinationPortTextBox.delete(1.0,'end')
		self.DestinationPortTextBox.configure(bg = 'white')
		self.DestinationPort = ''
		self.DestinationPortTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.DestinationPortTextBox.insert('1.0','<Destination Port(s)> (a,b,d-f,>g,<h)')
		self.DestinationPortTextBox.tag_add("boldcentered", "1.0", 'end')
		self.DestinationPortTextBox.tag_configure("boldcentered",justify='center',background='white')
		
	######## End of Destination Port Functions #######		
		
	######## Rate-Limit Functions #######
		
	def GetManualRouteRateLimit(self, event):
		self.ManualRouteRateLimit = self.ManualRouteRateLimitTextBox.get(1.0,'end')
		self.ManualRouteRateLimit = self.ManualRouteRateLimit.strip('\n')
		if self.ManualRouteRateLimit != '':
			self.ManualRouteRateLimitTextBox.delete('1.0', 'end')
			self.ManualRouteRateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.ManualRouteRateLimitTextBox.insert('1.0',self.ManualRouteRateLimit+'  kbps')
			self.ManualRouteRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
			self.ManualRouteRateLimitTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			self.ProgramRoute.focus_set()
			return 'break'
		else:
			self.ResetManualRouteRateLimit()

	def SetManualRouteRateLimitTextBoxFocus(self, event):
		self.ManualRouteRateLimitTextBox.focus_set()
		self.ManualRouteRateLimitTextBox.delete('1.0','end')
		self.ManualRouteRateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.ManualRouteRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.ManualRouteRateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')

	def InitialManualRouteRateLimitTextBoxFocus(self):
		self.ManualRouteRateLimitTextBox.focus_set()
		self.ManualRouteRateLimitTextBox.delete('1.0','end')
		self.ManualRouteRateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='black')
		self.ManualRouteRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.ManualRouteRateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')
		self.SetManualRouteAction()
		
	def SetManualRouteRateLimitTextBoxUnFocus(self, event):
		if self.ManualRouteRateLimit != '':
			self.ManualRouteRateLimitTextBox.delete('1.0', 'end')
			self.ManualRouteRateLimitTextBox.configure(font=("Verdana",10,'bold'),fg='white')
			self.ManualRouteRateLimitTextBox.insert('1.0',self.ManualRouteRateLimit+'  kbps')
			self.ManualRouteRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
			self.ManualRouteRateLimitTextBox.tag_configure("boldcentered", background='dark green',justify='center')
			return 'break'
		else:
			self.ResetManualRouteRateLimit()

	def ResetManualRouteRateLimit(self):
		self.ManualRouteRateLimitTextBox.delete(1.0,'end')
		self.ManualRouteRateLimitTextBox.configure(bg = 'white')
		self.ManualRouteRateLimit = ''
		self.ManualRouteRateLimitTextBox.configure(font=("Verdana",10,'italic'),fg='dark grey')
		self.ManualRouteRateLimitTextBox.insert('1.0','<kbps>')
		self.ManualRouteRateLimitTextBox.tag_add("boldcentered", "1.0", 'end')
		self.ManualRouteRateLimitTextBox.tag_configure("boldcentered",justify='center',background='white')
		
	######## End of Rate-Limit Functions #######
	
	######## Pop Up Window Functions #######	

	def SelectRateLimitWindow(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		self.SelectRateLimitPopup = self.popup
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.SelectRateLimitPopup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.SelectRateLimitPopup.lift()
		self.SelectRateLimitPopup.title("Missing A Rate-limit Value")
		self.TitleLabel=tk.Label(self.SelectRateLimitPopup,text="\nYou Didn't Enter a rate-limit kbps value!\n\n  You need to set a rate-limit value >0!!",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.SelectRateLimitPopup,text='OK!',command=self.SelectRateLimitPopup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)

	def IncorrectPrefixWindow(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		self.IncorrectPrefixPopup = self.popup
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.IncorrectPrefixPopup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.IncorrectPrefixPopup.lift()
		self.IncorrectPrefixPopup.title("Wrong Prefix Format")
		self.TitleLabel=tk.Label(self.IncorrectPrefixPopup,text="\nEnter prefix in format <ip prefix>/<mask>\n",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.IncorrectPrefixPopup,text='OK!',command=self.IncorrectPrefixPopup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)
		
	
	def SelectPeerIPAddressWindow(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		self.SelectPeerIPAddressPopup = self.popup
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.SelectPeerIPAddressPopup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.SelectPeerIPAddressPopup.lift()
		self.SelectPeerIPAddressPopup.title("Select a Peer")
		self.TitleLabel=tk.Label(self.SelectPeerIPAddressPopup,text="\nMake Sure you select a Peer!\n",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.SelectPeerIPAddressPopup,text='OK!',command=self.SelectPeerIPAddressPopup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)

	def SelectProtocolWindow(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		self.SelectProtocolPopup = self.popup
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.SelectProtocolPopup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.SelectProtocolPopup.lift()
		self.SelectProtocolPopup.title("Select a Protocol")
		self.TitleLabel=tk.Label(self.SelectProtocolPopup,text="\nMake Sure you select a protocol\n",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.SelectProtocolPopup,text='OK!',command=self.SelectProtocolPopup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)
		
		
	def SourcePortWindow(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		self.SourcePortPopup = self.popup
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.SourcePortPopup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.SourcePortPopup.lift()
		self.SourcePortPopup.title("Configure Some Ports")
		self.TitleLabel=tk.Label(self.SourcePortPopup,text="\nMake Sure you enter some source ports\nin the format a,b,d-f,>g,<h",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.SourcePortPopup,text='OK!',command=self.SourcePortPopup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)
		
	def DestinationPortWindow(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		self.DestinationPortPopup = self.popup
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.DestinationPortPopup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.DestinationPortPopup.lift()
		self.DestinationPortPopup.title("Configure Some Ports")
		self.TitleLabel=tk.Label(self.DestinationPortPopup,text="\nMake Sure you enter some destination ports\nin the format a,b,d-f,>g,<h",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.DestinationPortPopup,text='OK!',command=self.DestinationPortPopup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)
		

	def MatchNetworksWindow(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		self.MatchNetworksWindowPopup = self.popup
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.MatchNetworksWindowPopup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.MatchNetworksWindowPopup.lift()
		self.MatchNetworksWindowPopup.title("Configure The Same Network Types")
		self.TitleLabel=tk.Label(self.MatchNetworksWindowPopup,text="\nMake Sure both Source AND Destination Prefixes are eith both IPv4 or IPv6",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.MatchNetworksWindowPopup,text='OK!',command=self.MatchNetworksWindowPopup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)
		
	def AnnounceOrWithdrawWindow(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		self.AnnounceOrWithdrawWindowPopup = self.popup
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.AnnounceOrWithdrawWindowPopup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.AnnounceOrWithdrawWindowPopup.lift()
		self.AnnounceOrWithdrawWindowPopup.title("Choose Announce or Withdraw")
		self.TitleLabel=tk.Label(self.AnnounceOrWithdrawWindowPopup,text="\nChoose Either to Announce or Withdraw The Route",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.AnnounceOrWithdrawWindowPopup,text='OK!',command=self.AnnounceOrWithdrawWindowPopup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)
		
	def ChooseAnActionWindow(self,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		self.ChooseAnActionWindowPopup = self.popup
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.ChooseAnActionWindowPopup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.ChooseAnActionWindowPopup.lift()
		self.ChooseAnActionWindowPopup.title("Choose An Action")
		self.TitleLabel=tk.Label(self.ChooseAnActionWindowPopup,text="\nChoose An Action!",font=("Verdana", 12,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close= tk.Button(self.ChooseAnActionWindowPopup,text='OK!',command=self.ChooseAnActionWindowPopup.destroy,font=("Verdana",10,'bold'))
		self.close.grid(row=2,column=0,columnspan=3,pady=10)

	######## End Of Pop Up Window Functions #######		
	
	def is_valid_network(self,sourceaddress):
		try:
			my_net = ipaddress.ip_network(sourceaddress, strict=False)
		except (ValueError):
			return False
		return True, my_net

	def return_network(self,sourceaddress):
		try:
			my_net = ipaddress.ip_network(sourceaddress, strict=False)
		except (ValueError):
			return False
		return my_net
			
	def is_valid_ipv4_address(self,sourceaddress):
		try:
			socket.inet_pton(socket.AF_INET, sourceaddress)
		except AttributeError:  # no inet_pton here, sorry
			try:
				socket.inet_aton(sourceaddress)
			except socket.error:
				return False
			return sourceaddress.count('.') == 3
		except socket.error:  # not a valid address
			return False
		return True

	def ClearAllEntries(self):
		self.ResetManualRouteRateLimit()
		self.ResetDestinationPort()
		self.ResetSourcePort()
		self.ResetDestinationPrefix()
		self.ResetSourcePrefix()
		self.PeerIPAddressStringVariable.set("Select BGP FS Peer")
		self.ProtocolStringVariable.set("Select Protocol")
		self.ManualRouteRedirectIPRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.ManualRouteRedirectVRFRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.ManualRouteRateLimitTrafficRadLabel.configure(font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.ManualRouteDummyRad.select()
		self.ManualAnnounceWithdrawDummyRad.select()
		self.AddRemove = ''


	def DeleteAllManualFlowSpecRoutes(self):
		ManualRouteQueue.put('DELETEALLMANUALROUTES')
				
class VerticalScrollFrame(ttk.Frame):

	def __init__(self, parent, *args, **options):
		"""
		WIDGET-SPECIFIC OPTIONS:
		   style, pri_background, sec_background, arrowcolor,
		   mainborderwidth, interiorborderwidth, mainrelief, interiorrelief 
		"""
		# Extract key and value from **options using "pop" function:
		#   pop(key[, default])
		style          = options.pop('style',ttk.Style())
		pri_background = options.pop('pri_background','light grey')
		sec_background = options.pop('sec_background','grey70')
		arrowcolor     = options.pop('arrowcolor','black')
		mainborderwidth     = options.pop('mainborderwidth', 0)
		interiorborderwidth = options.pop('interiorborderwidth', 0)
		mainrelief          = options.pop('mainrelief', 'flat')
		interiorrelief      = options.pop('interiorrelief', 'flat')
	
		ttk.Frame.__init__(self, parent, style='main.TFrame',
						   borderwidth=mainborderwidth, relief=mainrelief)
	
		self.__setStyle(style, pri_background, sec_background, arrowcolor)
	
		self.__createWidgets(mainborderwidth, interiorborderwidth,
							 mainrelief, interiorrelief,
							 pri_background,sec_background)
		self.__setBindings()
	
	
	def __setStyle(self, style, pri_background, sec_background, arrowcolor):
		'''Setup stylenames of outer frame, interior frame and verticle
		   scrollbar'''        
		style.configure('main.TFrame', background=pri_background)
		style.configure('interior.TFrame', background=sec_background)
		style.configure('canvas.Vertical.TScrollbar', background=pri_background,
						troughcolor=sec_background, arrowcolor=arrowcolor)
		style.map('canvas.Horizontal.TScrollbar',
			background=[('active',pri_background),('!active',pri_background)],
			arrowcolor=[('active',arrowcolor),('!active',arrowcolor)])
	


	def __createWidgets(self, mainborderwidth, interiorborderwidth,
						mainrelief, interiorrelief, pri_background, sec_background):
		'''Create widgets of the scroll frame.'''
		self.hscrollbar = ttk.Scrollbar(self, orient='horizontal')
		self.sizegrip = ttk.Sizegrip(self)
		self.sizegrip.pack(in_ = self.hscrollbar, side ='bottom', anchor = "se")
		self.hscrollbar.pack(side='bottom', fill='x', expand='false')
		self.vscrollbar = ttk.Scrollbar(self, orient='vertical',
										style='canvas.Vertical.TScrollbar')
		self.vscrollbar.pack(side='right', fill='y', expand='false')
	
		self.canvas = tk.Canvas(self,
								bd=0, #no border
								highlightthickness=0, #no focus highlight
								yscrollcommand=self.vscrollbar.set,#use self.vscrollbar
								xscrollcommand=self.hscrollbar.set,#use self.vscrollbar
								background=pri_background #improves resizing appearance
								)
	
	
		self.vscrollbar.config(command=self.canvas.yview)
		self.hscrollbar.config(command=self.canvas.xview)
		self.canvas.pack(side='left', fill='both', expand='true')
	
		# reset the view
		self.canvas.xview_moveto(0)
		self.canvas.yview_moveto(0)
	
		# create a frame inside the canvas which will be scrolled with it
		self.interior = ttk.Frame(self.canvas,
								  style='interior.TFrame',
								  borderwidth=interiorborderwidth,
								  relief=interiorrelief)
		self.interior_id = self.canvas.create_window(0, 0,
													 window=self.interior,
													 anchor='nw')

	def pack(self, **kwargs):
		'''
		  Pack the scrollbar and canvas correctly in order to recreate the same look as MFC's windows. 
		'''
		self.hscrollbar.pack(side=tk.BOTTOM, fill=tk.X, expand=tk.FALSE)
		self.vscrollbar.pack(side=tk.RIGHT, fill=tk.Y,  expand=tk.FALSE)
		self.sizegrip.pack(in_ = self.hscrollbar, side = tk.BOTTOM, anchor = "se")
		self.canvas.pack(side=tk.LEFT, padx=5, pady=5,fill=tk.BOTH, expand=tk.TRUE)
		
		ttk.Frame.pack(self, **kwargs)
		

	def __setBindings(self):
		'''Activate binding to configure scroll frame widgets.'''
		self.canvas.bind('<Configure>',self.__configure_canvas_interiorframe)
		self.canvas.bind_all("<MouseWheel>", self.__on_mousewheel)
		
		
	def __on_mousewheel(self, event):
		shift = (event.state & 0x1) != 0
		scroll = -1 if event.delta > 0 else 1
		if shift:
			self.canvas.xview_scroll(scroll, "units")
		else:
			self.canvas.yview_scroll(scroll, "units")
			
	def __configure_canvas_interiorframe(self, event):
		'''Configure the interior frame size and the canvas scrollregion'''
		#Force the update of .winfo_width() and winfo_height()
		self.canvas.update_idletasks() 
	
		#Internal parameters 
		interiorReqHeight= self.interior.winfo_reqheight()
		canvasWidth    = self.canvas.winfo_width()
		canvasHeight   = self.canvas.winfo_height()
	
		#Set interior frame width to canvas current width
		self.canvas.itemconfigure(self.interior_id, width=canvasWidth)
		
		# Set interior frame height and canvas scrollregion
		if canvasHeight > interiorReqHeight:
			###--('canvasHeight > interiorReqHeight')
			self.canvas.itemconfigure(self.interior_id,  height=canvasHeight)
			self.canvas.config(scrollregion="0 0 {0} {1}".
							   format(canvasWidth, canvasHeight))
		else:
			###--('canvasHeight <= interiorReqHeight')
			self.canvas.itemconfigure(self.interior_id, height=interiorReqHeight)
			self.canvas.config(scrollregion="0 0 {0} {1}".
							   format(canvasWidth, interiorReqHeight))


class ShowFlowspecRoutesPopup(object):
	def __init__(self,FlowRouteQueue,ParentWindow):
		global FlowPopUpRefreshInterval
		self.popup = tk.Toplevel(ParentWindow)
		self.popup.grid_columnconfigure(0, weight=1)
		self.popup.grid_rowconfigure(2, weight=1)
		width = ParentWindow.winfo_width()
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()))
		self.popup.lift()
		self.NumberOfFlowRoutes = 0
		self.popup.title("Active Flowspec Rules Programmed on Edge Routers")
		self.TitleLabel=tk.Label(self.popup,text="### Active Flowspec Rules Programmed on Edge Routers###\n",font=("Verdana", 16),justify='left')
		self.TitleLabel.grid(column=0, row=0,columnspan=3, sticky='n')
		self.FlowCount=tk.Label(self.popup,text='Number of Active Flow Routes '+str(self.NumberOfFlowRoutes)+'\n',font=("Verdana", 14),justify='center')
		self.FlowCount.grid(column=0, row=1,columnspan=3, sticky='new')
		self.text_wid = tk.Text(self.popup,relief = 'raised', height=20,width=130,borderwidth=3)
		self.text_wid.insert('end','Neighbor		Source			Destination			Protocol		Source Port		Destination Port		Active Action\n\n')
		self.scroll = tk.Scrollbar(self.popup, command=self.text_wid.yview)
		self.text_wid.grid(column=0, columnspan=3,row=2,sticky='nswe', padx=10, pady=5)
		self.scroll.grid(column=0, columnspan=3,row=2,sticky='nse',padx=10)
		self.popup.after(100,self.FlowRouteQueuePoll,FlowRouteQueue)
		self.close= tk.Button(self.popup,text='Close Window',command=self.cleanup,font=("Verdana",12,'bold'))
		self.close.grid(row=5,column=0,columnspan=3,pady=10)
		
	def FlowRouteQueuePoll(self,c_queue):
		try:
			ListOfRoutes = c_queue.get(0)
			self.text_wid.delete('1.0', 'end')
			self.text_wid.insert('end','Neighbor		Source			Destination			Protocol		Source Port		Destination Port		Active Action\n\n')
			self.NumberOfFlowRoutes = 0
			for line in ListOfRoutes:
				self.NumberOfFlowRoutes +=1
				for r in (('neighbor ',''),(' source-port ',''), (' destination-port ',''),(' source ','		'), (' destination ','			'), ('protocol ','			'),('[',''),(']','		')):
					line = line.replace(*r)
				self.text_wid.insert('end', line+'\n')
			self.FlowCount=tk.Label(self.popup,text='Number of Active Flow Routes '+str(self.NumberOfFlowRoutes)+'\n',font=("Verdana", 14),justify='center')
			self.FlowCount.grid(column=0, row=1,columnspan=3, sticky='new')
		except Empty:
			pass
		finally:
			self.text_wid.configure(bg ='dark blue',fg = 'white',font=("Verdana", 10, 'bold'))
			self.popup.after((FlowPopUpRefreshInterval*1000), self.FlowRouteQueuePoll, c_queue)
			
	def cleanup(self):
		self.popup.destroy()
		


class ShowSflowPopup(object):
	def __init__(self,SflowQueue,ParentWindow):
		global FlowPopUpRefreshInterval
		self.popup = tk.Toplevel(ParentWindow)
		height = ParentWindow.winfo_height()/2
		width = ParentWindow.winfo_width()
		self.popup.grid_columnconfigure(0, weight=1)
		self.popup.grid_rowconfigure(2, weight=1)
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.popup.lift()
		self.NumberOfFlows = 0
		self.popup.title("Active Inspected sFlow Records From Edge Routers")
		self.TitleLabel=tk.Label(self.popup,text="### Active Inspected sFlow Records From Edge Routers###\n",font=("Verdana", 16),justify='center')
		self.TitleLabel.grid(column=0, row=0,columnspan=3, sticky='n')
		self.FlowCount=tk.Label(self.popup,text='Number of Active Flows '+str(self.NumberOfFlows)+'\n',font=("Verdana", 14),justify='center')
		self.FlowCount.grid(column=0, row=1,columnspan=3, sticky='new')
		self.text_wid = tk.Text(self.popup,relief = 'raised', height=20,width=130,borderwidth=3)
		self.text_wid.insert('end', 'Router		Protocol		Source-IP		SourcePort		Source Intf-ID		Destination-IP		DestinationPort		Bandwidth\n\n')
		self.scroll = tk.Scrollbar(self.popup, command=self.text_wid.yview)
		self.text_wid.grid(column=0, columnspan=3,row=2,sticky='nswe',padx=10, pady=5)
		self.scroll.grid(column=0, columnspan=3,row=2,sticky='nse',padx=10)
		self.popup.after(100,self.SflowQueuePoll,SflowQueue)
		self.close= tk.Button(self.popup,text='Close Window',command=self.cleanup,font=("Verdana",12,'bold'))
		self.close.grid(row=5,column=0,columnspan=3,pady=10)
		
	def SflowQueuePoll(self,c_queue):
		try:
			self.ListOfFlows = c_queue.get(0)
			self.text_wid.delete('1.0', 'end')
			self.text_wid.insert('end', 'Router		Protocol		Source-IP		SourcePort		Source Intf-ID		Destination-IP		DestinationPort		Bandwidth\n\n')
			self.NumberOfFlows = 0
			for line in self.ListOfFlows:
				self.NumberOfFlows += 1
				line = '		'.join(line)
				self.text_wid.insert('end', str(line) + '\n')
			self.FlowCount=tk.Label(self.popup,text='Number of Active Flows '+str(self.NumberOfFlows)+'\n',font=("Verdana", 14),justify='center')
			self.FlowCount.grid(column=0, row=1,columnspan=3, sticky='ew')			
		except Empty:
			pass
		finally:
			self.text_wid.configure(bg = 'dark blue',fg = 'white',font=("Verdana", 10,'bold'))
			self.popup.after((FlowPopUpRefreshInterval*1000), self.SflowQueuePoll, c_queue)
				
	def cleanup(self):
		self.popup.destroy()		



def SendFlowsToExabgp(queue):
	while True:
		UpdateRoutes = []
		while not queue.empty():
			try:
				command = queue.get_nowait()         # Read from the queue
				r = requests.post(exabgpurl, data={'command':command})
			except:
				False

		




if __name__ == '__main__':


	ProgramSflowrt()
	
	# Queue which will be used for storing Datalines (Flow data from sflow-rt)
	
	SflowQueue = JoinableQueue(maxsize=0)  
	SflowQueue.cancel_join_thread()
	ExaBGPQueue = JoinableQueue(maxsize=0)
	ExaBGPQueue.cancel_join_thread()
	SignalResetQueue = JoinableQueue(maxsize=0)  
	SignalResetQueue.cancel_join_thread()
	FlowRouteQueueForQuit = JoinableQueue(maxsize=0)  
	FlowRouteQueueForQuit.cancel_join_thread()
	FlowRouteQueue = JoinableQueue(maxsize=0)  
	FlowRouteQueue.cancel_join_thread()
	ManualRouteDisplayQueue = JoinableQueue(maxsize=0)  
	ManualRouteDisplayQueue.cancel_join_thread()
	ManualRouteQueue = JoinableQueue(maxsize=0)  
	ManualRouteQueue.cancel_join_thread()
	UpdatePolicyQueue = JoinableQueue(maxsize=0)  
	UpdatePolicyQueue.cancel_join_thread()


	root = tk.Tk()
	root.maxsize(width = 1800, height = 1500)
	gui = FlowspecGUI(root, SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,UpdatePolicyQueue,SignalResetQueue)
	gui.grid(row=0, column=0, sticky='nsew')
	SendFlowsToExabgpProcess = Process(target=SendFlowsToExabgp,args=(ExaBGPQueue,))
	FindAndProgramDdosFlowsProcess = Process(target=FindAndProgramDdosFlows,args=(SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,ManualRouteQueue,ManualRouteDisplayQueue,UpdatePolicyQueue,SignalResetQueue,ExaBGPQueue))
	SendFlowsToExabgpProcess.start()
	FindAndProgramDdosFlowsProcess.start()
	root.rowconfigure(0, weight=1)
	root.columnconfigure(0, weight=1)
	while True:
		try:
			root.mainloop()
			break
		except UnicodeDecodeError:
			pass

	SendFlowsToExabgpProcess.join()
	FindAndProgramDdosFlowsProcess.join()

