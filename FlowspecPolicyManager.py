#!/usr/bin/env python


import os
import re
import json
import requests
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
from pprint import pprint as pp


## Initial Open TopologyVariable.yaml To populate Variables

script_dir = os.path.dirname(__file__)
rel_path = "TopologyVariables.yaml"
abs_file_path = os.path.join(script_dir, rel_path)
file=open(abs_file_path)
topo_vars = yaml.load(file.read())
topo_vars['home_directory'] = os.path.dirname(os.path.realpath(__file__))
file.close()


## Derived Policy Manager Variables 


sflowIP=str(topo_vars['sflow_rt_ip'])
ExabgpIP=str(topo_vars['exabgp_ip'])
SflowPollTime=int(topo_vars['sflowpolltime'])
MaxSflowEntries=str(topo_vars['maxsflowentries'])

sflowrt_url = 'http://'+sflowIP+':'+str(topo_vars['sflow_rt_port'])
exabgpurl= 'http://'+ExabgpIP+':'+str(topo_vars['exabgp_port'])


ProtocolList = []					# Example Format: ProtocolList = [{'TCP':6},{'UDP':17}]
for entry in topo_vars['IPProtocol']:
	ProtocolList.append(entry)


NHVRFDict = {}
NHIPDict = {}

try:
	for Router in topo_vars['EdgeRouters']:
		NHIPDict[Router['RouterID']]=Router['IPNH']
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

ipflow = {'keys':'agent,ipprotocol,ipsource,or:tcpsourceport:udpsourceport:icmptype,inputifindex,ipdestination,or:tcpdestinationport:udpdestinationport:icmpcode', 'value':'bytes'}




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


def FindAndProgramDdosFlows(SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,ManualRouteQueue,UpdatePolicyQueue,SignalResetQueue,ExaBGPQueue):
	ExabgpAndQueueCalls = FindAndProgramDdosFlowsHelperClass()
	ListOfFlows = []
	FlowBandwidthDict = {}
	FlowActionDict = {}
	DefaultBandwidth = 0
	DiscardPolicyUpdate = ['discard', 0, [], []]
	RedirectNHPolicyUpdate = ['redirect next-hop', 0, [], []]
	RedirectVRFPolicyUpdate = ['redirect VRF', 0, [], []]
	_cached_stamp = 0
	TopologyVariables = abs_file_path
	sflowcount = 0
	
	while True:
		try:
			ResetSignalled = ExabgpAndQueueCalls.SignalResetQueuePoll(SignalResetQueue)
			if ResetSignalled[0] == 'RESET SIGNALED':
				ListOfFlows = []
				ExabgpAndQueueCalls.ResetActiveFlowspecRoutes()
				FlowBandwidthDict = {}
				FlowActionDict = {}
				DefaultBandwidth = 0
				DiscardPolicyUpdate = ['discard', 0, [], []]
				RedirectNHPolicyUpdate = ['redirect next-hop', 0, [], []]
				RedirectVRFPolicyUpdate = ['redirect VRF', 0, [], []]
			else:
				pass
		except:
			pass
		try:
			ManualRoute = ExabgpAndQueueCalls.ManualRouteQueuePoll(ManualRouteQueue)
			if str(ManualRoute[7]) == 'redirect next-hop':
				Action = 'redirect '+str(NHIPDict[str(ManualRoute[0])])
			elif str(ManualRoute[7]) == 'redirect VRF':
				Action = 'redirect '+str(NHVRFDict[str(ManualRoute[0])])
			elif str(ManualRoute[7]) == 'discard':
				Action = 'discard'

			if ManualRoute == None:
				pass
			else:
				if ManualRoute[6] == str(1):
					try:
						ExabgpAndQueueCalls.ExaBgpAnnounce(str(ManualRoute[0]),str(ManualRoute[3]),str(ManualRoute[1]),str(ManualRoute[4]),str(ManualRoute[2]),str(ManualRoute[5]),Action)
					except:
						pass
				if ManualRoute[6] == str(2):
					try:
						ExabgpAndQueueCalls.ExaBgpWithdraw(str(ManualRoute[0]),str(ManualRoute[3]),str(ManualRoute[1]),str(ManualRoute[4]),str(ManualRoute[2]),str(ManualRoute[5]),Action)
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
			if NewPolicyUpdate[0] == 'discard':
				DiscardPolicyUpdate = copy.deepcopy(NewPolicyUpdate)
			if NewPolicyUpdate[0] == 'redirect next-hop':
				RedirectNHPolicyUpdate = copy.deepcopy(NewPolicyUpdate)
			if NewPolicyUpdate[0] == 'redirect VRF':
				RedirectVRFPolicyUpdate = copy.deepcopy(NewPolicyUpdate)
		except:
			pass
		
		ListOfPolicyUpdates = [RedirectNHPolicyUpdate,RedirectVRFPolicyUpdate,DiscardPolicyUpdate]
		SortedListOfPolicyUpdates = copy.deepcopy(Sort(ListOfPolicyUpdates))
		SortedListOfPolicyUpdates = [item for item in SortedListOfPolicyUpdates if item[1] != 0]
		
		try:
			MinValue = int(SortedListOfPolicyUpdates[0][1])*1000000
			print(MinValue)
		except:
			pass
		if sflowcount == 0 or sflowcount == SflowPollTime:
			print("running sflow")
			try:
				session = requests.Session()
				retry = Retry(connect=3, backoff_factor=0.5)
				adapter = HTTPAdapter(max_retries=retry)
				session.mount('http://', adapter)
				session.mount('https://', adapter)
				try:
					r = session.get(str(sflowrt_url)+'/activeflows/ALL/ipdest/json?maxFlows='+str(MaxSflowEntries)+'&minValue=1')
				except:
					r = session.get(str(sflowrt_url)+'/activeflows/ALL/ipdest/json?maxFlows=4000&minValue=1')
			except requests.exceptions.ConnectionError:
				r.status_code = "Connection refused"	
			rawflows = r.json()
			sflowcount = 0
		
		try:
			for i in rawflows:
				Data = str(i["key"])
				DataList = Data.split(",")
				bw = int(i["value"]*8/1000/1000)
				FlowBandwidthDict[str(DataList)]=str('('+str(bw)+' Mbps)')
				if SortedListOfPolicyUpdates != []:
					for entry in SortedListOfPolicyUpdates:
						if entry[0] == 'discard':
							CurrentAction = entry[0]
						elif entry[0] == 'redirect next-hop':
							try:
								CurrentAction = 'redirect '+str(NHIPDict.get(str(DataList[0])))
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
								print("Flow Passed the Check (returned true) and is about to be Programmed")
								ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction,ExaBGPQueue)
								break
							else:
								try: ## Try adding with default policy values (pass if none)
									if DefaultAction == 'discard':
										CurrentAction = DefaultAction
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
										ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction,ExaBGPQueue)
										print ("Checked all Policies For Flow, Doesn't exist yet, so add it using Default Policy")
										break
								except:
									pass
						except:
							pass

							# This means the Source Port or Destination port is not in this policy (or we got a Fasle)
							
						try:
							if not CheckPolicy(DataList,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList,CurrentAction,PolicyBandwidth,bw) and str(DataList) in FlowActionDict.keys() and SortedListOfPolicyUpdates.index(entry) == int(len(SortedListOfPolicyUpdates)-1):
								print ("Returned False  - No Source or Destination Port in the source or destination portlist - removing the flow")
								ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue)
								FlowActionDict.pop(str(DataList),None)
								ListOfFlows.remove(DataList)
								break
						except:
							pass
						
						try:

							if bw < DefaultBandwidth:
								ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue)
								FlowActionDict.pop(str(DataList),None)
								ListOfFlows.remove(DataList)
								print ("No flow policy but default BW > flow bw - have to remove flows.")
						except:
							pass

		# No Flow Policy Set.Just use default BW Policy
		
				if SortedListOfPolicyUpdates == [] and DefaultBandwidth != 0:
					print ("Hit the default")
					try:
						if DefaultAction == 'discard':
							CurrentAction = DefaultAction
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
						PolicyBandwidth = DefaultBandwidth
						if bw > DefaultBandwidth:
							if 'None' not in CurrentAction:
								ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction,ExaBGPQueue)
								print ("BW > default, and there is an action.  So program the flow (using local function ProgramFlowPolicies")
						
						if DataList in ListOfFlows and 'None' in CurrentAction:
							ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue)
							FlowActionDict.pop(str(DataList),None)
							ListOfFlows.remove(DataList)
							print ("Theres a None I have to remove - Use ExabgpWithdraw so the activeflowlist is updated")
							
						if DataList in ListOfFlows and bw < DefaultBandwidth:
							ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue)
							FlowActionDict.pop(str(DataList),None)
							ListOfFlows.remove(DataList)
							print ("No flow policy but default BW > flow bw - have to remove flows. Use ExabgpWithdraw so the activeflowlist is updated")
					except:
						pass
				else:
					pass
		except:
			pass
			
		# Else withdraw all the flows.
		
		if SortedListOfPolicyUpdates == [] and DefaultBandwidth == 0 and len(ListOfFlows) != 0:
			print ("Withdrawing all routes - No Policies at all matching.   All active routes will be withdrawn one by one")
			for DataList in ListOfFlows:
				ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue)
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
		sflowcount += 1
		time.sleep(1)
		
		
def RenderTopologyVariables():
	# Updating for the main Program
	global NHVRFDict
	global NHIPDict
	global SflowPollTime
	script_dir = os.path.dirname(__file__)
	rel_path = "TopologyVariables.yaml"
	abs_file_path = os.path.join(script_dir, rel_path)
	file=open(abs_file_path)
	topo_vars = yaml.load(file.read())
	topo_vars['home_directory'] = os.path.dirname(os.path.realpath(__file__))
	file.close()
	try:
		SflowPollTime=int(topo_vars['sflowpolltime'])
		MaxSflowEntries=str(topo_vars['maxsflowentries'])
	except:
		pass
	try:
		for Router in topo_vars['EdgeRouters']:
			NHVRFDict[Router['RouterID']]=Router['VRF']
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
			print ("Theres a NONE as an action so returning false")
			return False
		elif SourcePortProtocol in CurrentConfiguredSourceProtocolPortList and DestinationPortProtocol in CurrentConfiguredDestinationProtocolPortList and PolicyBandwidth > bw:
			print ("The bandwidth of this flow is too low - returning False")
			return False
		elif SourcePortProtocol in CurrentConfiguredSourceProtocolPortList and DestinationPortProtocol in CurrentConfiguredDestinationProtocolPortList and bw >= PolicyBandwidth:
			print ("Caught the Rule with an Exact Match on Source and Destination Port")
			return True
		elif SourcePortProtocol in CurrentConfiguredSourceProtocolPortList and str(DataList[1]) == '1' and bw >= PolicyBandwidth:
			print ("Processed ICMP Flow (don't check destination - That specific match  S & D can be caught by above rule)")
			return True
		elif DestinationPortProtocol in CurrentConfiguredDestinationProtocolPortList and bw >= PolicyBandwidth and CurrentConfiguredSourceProtocolPortList != []:
			for entry in CurrentConfiguredSourceProtocolPortList:
				if '>' in entry:
					if DataList[1] == entry.split('>')[0] and DataList[3] > entry.split('>')[1]:
						print ("Specific Destination Port Match and Source is explicitly > 1024 (well known ports)")
						return True
				elif '<' in entry:
					if DataList[1] == entry.split('<')[0] and DataList[3] < entry.split('<')[1]:
						print ("Specific Destination Port Match and Source is explicitly < 1024 (well known ports)")
						return True
				else:
					print ("Specific Destination Port (don't check Source Port - That specific match S & D can be caught by above rule)")
					return True
			
		elif SourcePortProtocol in CurrentConfiguredSourceProtocolPortList and bw >= PolicyBandwidth and CurrentConfiguredDestinationProtocolPortList != []:
			for entry in CurrentConfiguredDestinationProtocolPortList:
				if '>' in entry:
					if DataList[1] == entry.split('>')[0] and DataList[6] > entry.split('>')[1]:
						print ("Specific Source Port Match and Destination is explicitly > 1024 (well known ports)")
						return True	
				elif '<' in entry:
					if DataList[1] == entry.split('<')[0] and DataList[6] < entry.split('<')[1]:
						print ("Specific Source Port Match and Destination is explicitly < 1024 (well known ports)")
						return True
				else:
					print ("Specific Source Port  (don't check Destination Port - That specific match S & D can be caught by above rule)")
					return True
				
		elif DestinationPortProtocol in CurrentConfiguredDestinationProtocolPortList and bw >= PolicyBandwidth:
			print ("Specific Destination Port (No Source Port List at all - That specific match S & D can be caught by above rule)")
			return True
		elif SourcePortProtocol in CurrentConfiguredSourceProtocolPortList and bw >= PolicyBandwidth:
			print ("Specific Source Port  (No Destination Port List at all - That specific match S & D can be caught by above rule)")
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
								print ("Source < 1024 and Destination is < 1024 (well known ports)")
								return True
						except:
							pass
						try:
							if int(DataList[6]) > int(DestinationGreaterThanDict.get(DataList[1])):
								print ("Source < 1024 and Destination is > 1024 (well known ports)")
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
								print ("Source > 1024 and Destination is < 1024 (well known ports)")
								return  True
						except:
							pass
						try:
							if int(DataList[6]) > int(DestinationGreaterThanDict.get(DataList[1])):
								print ("Source > 1024 and Destination is > 1024 (well known ports)")
								return True
						except:
							pass
				else:
					print ("Source port or Destination Port is not in any configured Policy -> Returning False")
					return False
			except:
				pass
	except:
		pass
	


def ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction,ExaBGPQueue):
	try:

		if len(ListOfFlows) == 0:
			ListOfFlows.append(DataList)
			FlowActionDict[str(DataList)]=CurrentAction
			ExabgpAndQueueCalls.ExaBgpAnnounce(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),CurrentAction,ExaBGPQueue)
			print ("Length List of flows 0 , added the flow and Dict Entry")
		elif FlowActionDict.get(str(DataList)) != None and FlowActionDict.get(str(DataList)) != CurrentAction:
			ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue)
			FlowActionDict.pop(str(DataList),None)
			ListOfFlows.remove(DataList)
			print ("Popped the dict entry and List")
			ListOfFlows.append(DataList)
			FlowActionDict[str(DataList)]=CurrentAction
			ExabgpAndQueueCalls.ExaBgpAnnounce(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),CurrentAction,ExaBGPQueue)
			print ("Added flow and Dict entry and list")
		elif DataList not in ListOfFlows:
			ListOfFlows.append(DataList)
			FlowActionDict[str(DataList)]=CurrentAction
			ExabgpAndQueueCalls.ExaBgpAnnounce(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)),ExaBGPQueue)
			print ("Hit the else, added the flow and Dict Entry")
		else:
			if DataList in ListOfFlows:
				print ("Hit the pass rule")
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

	def ExaBgpAnnounce(self, ler,protocol,sourceprefix,sourceport,destinationprefix,destinationport,action,ExaBGPQueue):
		if protocol == '1':
			command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
			#Put in the queue for Programming
			ExaBGPQueue.put(command)
			command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
			self.ActiveFlowspecRoutes.append(command)
		else:
			command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' + action
			#Put in the queue for Programming
			ExaBGPQueue.put(command)
			command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' + action
			self.ActiveFlowspecRoutes.append(command)
	
	def ExaBgpWithdraw(self,ler,protocol,sourceprefix,sourceport,destinationprefix,destinationport,action,ExaBGPQueue):
		if protocol == '1':
			command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
			#Put in the queue for Programming
			ExaBGPQueue.put(command)
			command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
			self.ActiveFlowspecRoutes.remove(command)			
		else:
			command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'  + ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' +  action
			#Put in the queue for Programming
			ExaBGPQueue.put(command)
			command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'  + ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' +  action
			self.ActiveFlowspecRoutes.remove(command)


	
	def ReturnActiveFlowspecRoutes(self):
		return self.ActiveFlowspecRoutes

	def ResetActiveFlowspecRoutes(self):
		self.ActiveFlowspecRoutes = []

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



class ShowFlowspecRoutesPopup(object):
	def __init__(self,FlowRouteQueue,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		self.popup.grid_columnconfigure(0, weight=1)
		self.popup.grid_rowconfigure(2, weight=1)
		width = ParentWindow.winfo_width()
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()))
		self.popup.lift()
		self.popup.title("Active Flowspec Rules Programmed on Edge Routers")
		self.TitleLabel=tk.Label(self.popup,text="### Active Flowspec Rules Programmed on Edge Routers###\n",font=("Verdana", 20),justify='left')
		self.TitleLabel.grid(column=0, row=0,columnspan=3, sticky='n')		
		self.text_wid = tk.Text(self.popup,relief = 'raised', height=20,width=140,borderwidth=3)
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
			for line in ListOfRoutes:
				for r in (('neighbor ',''),(' source-port ',''), (' destination-port ',''),(' source ','		'), (' destination ','			'), ('protocol ','			'),('[',''),(']','		')):
					line = line.replace(*r)
				self.text_wid.insert('end', line+'\n')
		except Empty:
			pass
		finally:
			self.text_wid.configure(bg ='dark blue',fg = 'white',font=("Verdana", 12, 'bold'))
			self.popup.after(500, self.FlowRouteQueuePoll, c_queue)
			
	def cleanup(self):
		self.popup.destroy()



class ShowSflowPopup(object):
	def __init__(self,SflowQueue,ParentWindow):
		self.popup = tk.Toplevel(ParentWindow)
		height = ParentWindow.winfo_height()/2
		width = ParentWindow.winfo_width()
		self.popup.grid_columnconfigure(0, weight=1)
		self.popup.grid_rowconfigure(2, weight=1)
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.popup.lift()
		self.popup.title("Active Inspected sFlow Records From Edge Routers")
		self.TitleLabel=tk.Label(self.popup,text="### Active Inspected sFlow Records From Edge Routers###\n",font=("Verdana", 20),justify='center')
		self.TitleLabel.grid(column=0, row=0,columnspan=3, sticky='n')
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
			for line in self.ListOfFlows:
				line = '		'.join(line)
				self.text_wid.insert('end', str(line) + '\n')
		except Empty:
			pass
		finally:
			self.text_wid.configure(bg = 'dark blue',fg = 'white',font=("Verdana", 12,'bold'))
			self.popup.after(500, self.SflowQueuePoll, c_queue)
				
	def cleanup(self):
		self.popup.destroy()		

	

class ProgramFlowSpecRule(object):
	def __init__(self,ManualRouteQueue):
		self.ManualFlowRoute = []
		self.selected = tk.IntVar()
		self.actionselected = tk.IntVar()
		self.popup = tk.Toplevel()
		self.popup.title("Program Manual BGP Flowspec Rule")
		self.announce = tk.Radiobutton(self.popup,text='Announce Rule', value=1, variable=self.selected,font=("Verdana",12))
		self.withdraw = tk.Radiobutton(self.popup,text='Withdraw Rule', value=2, variable=self.selected,font=("Verdana",12))
		self.announce.grid(column=0,row=0,sticky='w')
		self.withdraw.grid(column=0,row=1,sticky='w')
		self.Peer = tk.Entry(self.popup,width=30, justify='center',font=("Verdana",10,'italic'))
		self.Peer.insert('end', '<Peer IP Address>')
		self.Peer.grid(row=2,column=1,padx=5)
		self.Peer.focus_set()
		self.SourcePrefix = tk.Entry(self.popup,width=30, justify='center',font=("Verdana",10,'italic'))
		self.SourcePrefix.insert('end', '<Source Prefix/Mask>')
		self.SourcePrefix.grid(row=2,column=2,padx=5)
		self.DestinationPrefix = tk.Entry(self.popup,width=30, justify='center',font=("Verdana",10,'italic'))
		self.DestinationPrefix.insert('end', '<Destination Prefix/mask>')
		self.DestinationPrefix.grid(row=2,column=3,padx=5)
		self.Protocol = tk.Entry(self.popup,width=30, justify='center',font=("Verdana",10,'italic'))
		self.Protocol.insert('end', '<Protocol>')
		self.Protocol.grid(row=2,column=4,padx=5)
		self.SourcePort = tk.Entry(self.popup,width=30, justify='center',font=("Verdana",10,'italic'))
		self.SourcePort.insert('end', '<Source Port>')
		self.SourcePort.grid(row=2,column=5,padx=5)
		self.DestinationPort = tk.Entry(self.popup,width=30, justify='center',font=("Verdana",10,'italic'))
		self.DestinationPort.insert('end', '<Destination Port>')
		self.DestinationPort.grid(row=2,column=6,padx=5)
		self.DiscardRadioButton = tk.Radiobutton(self.popup,text='Block Traffic', value=1, variable=self.actionselected,font=("Verdana",12))
		self.RedirectNHRadioButton = tk.Radiobutton(self.popup,text='Redirect To Next Hop', value=2, variable=self.actionselected,font=("Verdana",12))
		self.RedirectVRFRadioButton = tk.Radiobutton(self.popup,text='Redirect To VRF', value=3, variable=self.actionselected,font=("Verdana",12))
		self.DiscardRadioButton.grid(column=1,row=3, sticky='we')
		self.RedirectNHRadioButton.grid(column=2,row=3,sticky='we')
		self.RedirectVRFRadioButton.grid(column=3,row=3,sticky='we')
		self.button = tk.Button(self.popup,text="Program Rule",command=self.callback,font=("Verdana",12,'bold'))
		self.button.grid(row=4,column=0,padx=10)  
		self.close= tk.Button(self.popup,text='Close Window',command=self.cleanup,font=("Verdana",12,'bold'))
		self.close.grid(row=5,column=0,padx=10,pady=5)


	def callback(self):
		self.AddRemove = self.selected.get()
		self.PeerString = str(self.Peer.get())
		self.PeerString = self.PeerString.strip('\n')
		self.SourcePrefixString = str(self.SourcePrefix.get())
		self.SourcePrefixString = self.SourcePrefixString.strip('\n')
		self.DestinationPrefixString = str(self.DestinationPrefix.get())
		self.DestinationPrefixString = self.DestinationPrefixString.strip('\n')
		self.ProtocolString = str(self.Protocol.get())
		self.ProtocolString = self.ProtocolString.strip('\n')
		self.SourcePortString = str(self.SourcePort.get())
		self.SourcePortString = self.SourcePortString.strip('\n')
		self.DestinationPortString = str(self.DestinationPort.get())
		self.DestinationPortString = self.DestinationPortString.strip('\n')
		self.action = ''
		if self.actionselected.get() == 1:
			self.action = 'discard'
		if self.actionselected.get() == 2:
			self.action = 'redirect next-hop'
		if self.actionselected.get() == 3:
			self.action = 'redirect VRF'
		self.ManualFlowRouteString = self.PeerString +'@@@@@@' +self.SourcePrefixString+'@@@@@@'+str(self.DestinationPrefixString)+'@@@@@@'+str(self.ProtocolString)+'@@@@@@'+str(self.SourcePortString)+'@@@@@@'+str(self.DestinationPortString)+'@@@@@@'+str(self.AddRemove)+'@@@@@@'+str(self.action)
		self.ManualFlowRoute = self.ManualFlowRouteString.split('@@@@@@')
		for entry in self.ManualFlowRoute:
			ManualRouteQueue.put(entry)
		self.progress = ttk.Progressbar(self.popup, orient="horizontal",
								length=400, mode="determinate")
		self.progress.grid(row=4,column=1,columnspan=10,pady=10)
		self.bytes = 0
		self.maxbytes = 0
		self.start()

	
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
			self.popup.after(10, self.read_bytes)
		else:
			self.progress.destroy()
	
	def cleanup(self):
		self.popup.destroy()
			



### Tkinter GUI Classes


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
			#print('canvasHeight > interiorReqHeight')
			self.canvas.itemconfigure(self.interior_id,  height=canvasHeight)
			self.canvas.config(scrollregion="0 0 {0} {1}".
							   format(canvasWidth, canvasHeight))
		else:
			#print('canvasHeight <= interiorReqHeight')
			self.canvas.itemconfigure(self.interior_id, height=interiorReqHeight)
			self.canvas.config(scrollregion="0 0 {0} {1}".
							   format(canvasWidth, interiorReqHeight))




class FlowspecGUI(ttk.Frame):
	def __init__(self, parent,SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,UpdatePolicyQueue,SignalResetQueue):
		
		# Use These Global File Variable to Ensure tracking right file. Change the GUI if TopologyVariables.yaml changes
		global abs_file_path
		global ListOfFlows
		
		# Set time Stamp.  Compared in UpdateGUI() within this class
		self._cached_stamp = 0
		self.TopologyVariables = abs_file_path
	

		self.ListOfDiscardBadSourcePorts = []
		self.ListOfDiscardBadDestinationPorts = []
		self.ListOfRedirectNHBadSourcePorts = []
		self.ListOfRedirectNHBadDestinationPorts = []
		self.ListOfRedirectVRFBadSourcePorts = []
		self.ListOfRedirectVRFBadDestinationPorts = []
		self.FlowPolicyBandwidth = ''
		self.DiscardFlowPolicyBandwidth = ''
		self.RedirectNHFlowPolicyBandwidth = ''
		self.RedirectVRFFlowPolicyBandwidth = ''
		self.DefaultBandwidth = ''
		self.defaultaction = ''
		
		
		BG0 = 'white' #White Canvas (interior)
		BG1 = '#4e88e5' #Blue scheme

		
		ttk.Frame.__init__(self, parent=None, style='FlowspecGUI.TFrame', borderwidth=0,relief='raised')
		self.mainwindow = parent
		self.mainwindow.title('BGP Flowspec Policy Manager')
		self.mainwindow.geometry('950x900')

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
		
		TitleLabel=tk.Label(self.window,font=("Verdana", 16),background='light grey', relief='ridge',text="DDoS Flow Policy Management Using BGP Flowspec")
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
				
		self.DefaultBlockTrafficRad = tk.Radiobutton(self.window, background=BG0,value=1, variable=self.selecteddefaultaction, command=self.SetDefaultAction)
		self.DefaultBlockTrafficRadLabel = tk.Label(self.window,width=20,text='Block Traffic',font=("Verdana",12),fg='black',background='grey95',relief='ridge')
		self.DefaultRedirectIPRad = tk.Radiobutton(self.window,background=BG0,value=2, variable=self.selecteddefaultaction, command=self.SetDefaultAction)
		self.DefaultRedirectIPRadLabel = tk.Label(self.window,width=20,text='Redirect To Next Hop',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.DefaultRedirectVRFRad = tk.Radiobutton(self.window,background=BG0,value=3, variable=self.selecteddefaultaction, command=self.SetDefaultAction)
		self.DefaultRedirectVRFRadLabel = tk.Label(self.window,width=20,text='Redirect To VRF',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.DefaultBlockTrafficRad.grid(column=1, row=3,sticky='w',padx=10)
		self.DefaultRedirectIPRad.grid(column=2, row=3, sticky='w',padx=10)
		self.DefaultRedirectVRFRad.grid(column=3, row=3,sticky='w',padx=10)
		self.DefaultBlockTrafficRadLabel.grid(column=1, row=3, sticky='w', padx=50)
		self.DefaultRedirectIPRadLabel.grid(column=2, row=3,sticky='w',padx=50)
		self.DefaultRedirectVRFRadLabel.grid(column=3, row=3,sticky='w',padx=50)
		self.DefaultDummyRad = tk.Radiobutton(self.window, value=5, variable=self.selecteddefaultaction)
		
		# ---------------- ROW-4 ---------------#
		
		DefaultFlowPolicyBwLabel=tk.Label(self.window, background=BG0, text="Default Policy Inspection Bandwidth (Mbps): ",font=("Verdana", 10),justify='right')
		DefaultFlowPolicyBwLabel.grid(column=1,row=4,sticky='e',pady=10)
		
		self.DefaultBandwidthTextBox = tk.Text(self.window, background=BG0, height = 1, width = 40, borderwidth=1, relief="ridge",font=("Verdana",10,'italic'),fg='grey70')
		self.DefaultBandwidthTextBox.insert('1.0','  (Click <enter/return> to set policy bandwidth)')
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
		ClearDefaultSelection.grid(column=3, row=5,sticky='w')
		
		# ---------------- ROW-6 ---------------#
		
		SpacerLabel=tk.Label(self.window,background=BG0,text="\n",font=("Verdana", 12),justify='right')
		SpacerLabel.grid(column=3, columnspan=3,row=6,sticky='w')		
		
		# ---------------- ROW-7 ---------------#
		
		SectionLabel=tk.Label(self.window,background=BG0,text="Active Default Policy:",font=("Verdana", 12,'bold'),justify='left',fg='dark blue')
		SectionLabel.grid(column=1, row=7,sticky='e',padx=10)
		
		self.DefaultBandwidthTextBoxPolicy = tk.Text(self.window,background=BG0,height = 1, width = 40, borderwidth=2, relief="raised",font=("Verdana",12))
		self.DefaultBandwidthTextBoxPolicy.grid(column=2, columnspan=2,row=7,sticky='w',padx=10)
		
		ClearDefaultPolicy=tk.Button(self.window, background=BG0, text="Clear Default Policy",command=self.ClearDefaultPolicy,font=("Verdana", 10))
		ClearDefaultPolicy.grid(column=3, row=7,sticky='w',padx=60)
		
		# ---------------- ROW-8 ---------------#
		
		PolicyTitleLabel=tk.Label(self.window,background=BG0, text='\n############ Configure Flow Inspection Policy Bandwidth, Action & Ports #############',font=("Verdana", 10),justify='left',fg='dark blue')
		PolicyTitleLabel.grid(column=1, row=8,columnspan=3, sticky='we')
		
		
		# ---------------- ROW-9 ---------------#
		
		self.selected = tk.IntVar()
		ActionRuleLabel=tk.Label(self.window, background=BG0, text="Select the Flow Policy (Required)",font=("Verdana", 10),justify='right',anchor='nw',)
		ActionRuleLabel.pack()
		ActionRuleLabel.grid(column=1, row=9,columnspan=3,sticky='nw')
		
		# ---------------- ROW-10 ---------------#
		
		self.BlockTrafficRad = tk.Radiobutton(self.window, background=BG0, value=1, variable=self.selected, command=self.SetAction)
		self.BlockTrafficRadLabel = tk.Label(self.window,width=20,text='Block Traffic',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.RedirectIPRad = tk.Radiobutton(self.window, background=BG0,value=2, variable=self.selected, command=self.SetAction)
		self.RedirectIPRadLabel = tk.Label(self.window,width=20,text='Redirect To Next Hop',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.RedirectVRFRad = tk.Radiobutton(self.window, background=BG0,value=3, variable=self.selected, command=self.SetAction)
		self.RedirectVRFRadLabel = tk.Label(self.window,width=20,text='Redirect To VRF',font=("Verdana",12),fg='black',bg='grey95',relief='ridge')
		self.BlockTrafficRad.grid(column=1, row=10, sticky='w',padx=10)
		self.RedirectIPRad.grid(column=2, row=10, sticky='w',padx=10)
		self.RedirectVRFRad.grid(column=3, row=10,sticky='w',padx=10)
		self.BlockTrafficRadLabel.grid(column=1, row=10, sticky='w',padx=50)
		self.RedirectIPRadLabel.grid(column=2, row=10,sticky='w',padx=50)
		self.RedirectVRFRadLabel.grid(column=3, row=10,sticky='w',padx=50)
		self.DummyRad = tk.Radiobutton(self.window, value=5, variable=self.selected,command=self.SetAction)
		
		
		# ---------------- ROW-11 ---------------#
		
		
		FlowPolicyBwLabel=tk.Label(self.window, background=BG0, text="Flow Policy Inspection Bandwidth (Mbps): ",font=("Verdana", 10),justify='right')
		FlowPolicyBwLabel.grid(column=1,row=11,sticky='e',pady=10)
		
		self.BandwidthTextBox = tk.Text(self.window, background=BG0, height = 1, width = 40, borderwidth=1, relief="ridge",font=("Verdana",10,'italic'),fg='grey70')
		self.BandwidthTextBox.insert('1.0','  (Click <enter/return> to set policy bandwidth)')
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
		
		SelectPortButton = tk.Button(self.window, background=BG0,  text=" Add ", width=12, command=self.AddToPolicy,font=("Verdana",10))
		SelectPortButton.grid(column=3, row=16,padx=10,sticky='w')
		
		RemovePortButton = tk.Button(self.window, background=BG0, text=" Remove ", width=12, command=self.RemoveFromPolicy,font=("Verdana",10))
		RemovePortButton.grid(column=3, row=16,padx=30,sticky='e')
		
		
		self.DiscardPolicyTextBox = ScrolledText(self.window, background=BG0, height = 5, borderwidth=3,width=30, relief="sunken")
		self.DiscardPolicyTextBox.configure(bg = 'grey95', wrap='word', fg = 'white',font=("Verdana", 10))
		self.DiscardPolicyTextBox.grid(column=1, row=25,sticky='nswe',padx=10)
		
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
		ProgramFlowPolicyButton=tk.Button(self.window, text="Click Here", command=self.UpdateFlowspecPolicy,font=("Verdana", 12),fg='white',bg='dark grey')
		ProgramFlowPolicyButton.grid(column=2, row=22,sticky='e')
		ClearPolicySelection=tk.Button(self.window, background=BG0, text="Clear Selections", command=self.ClearPolicySelection,font=("Verdana", 12,'italic'))
		ClearPolicySelection.grid(column=3, row=22,sticky='w',padx=10)
		
		
		# ---------------- ROW-23 ---------------#
		
		ProgrammedPolicyLabel=tk.Label(self.window, background=BG0, text="\n",font=("Verdana", 12),justify='right',anchor='nw')
		ProgrammedPolicyLabel.pack()
		ProgrammedPolicyLabel.grid(column=1, columnspan=3,row=23,sticky='w')
		
		# ---------------- ROW-24 ---------------#
		
		DiscardPolicyLabel=tk.Label(self.window, background=BG0, text="Active Discard Policy",font=("Verdana", 12,'bold'),fg='dark blue')
		DiscardPolicyLabel.grid(column=1, row=24)
		
		RedirectNHPolicyLabel=tk.Label(self.window, background=BG0, text="Active Redirect NH Policy: ",font=("Verdana", 12,'bold'),fg='dark blue')
		RedirectNHPolicyLabel.grid(column=2, row=24)
		
		RedirectVRFPolicyLabel=tk.Label(self.window, background=BG0, text="Active Redirect VRF Policy: ",font=("Verdana", 12,'bold'),fg='dark blue')
		RedirectVRFPolicyLabel.grid(column=3, row=24)
		
		
		# ---------------- ROW-25 ---------------#
		
		self.DiscardPolicyTextBox = ScrolledText(self.window, background=BG0, height = 5, borderwidth=3,width=20, relief="raised")
		self.DiscardPolicyTextBox.configure(bg = 'white', wrap='word', fg = 'white',font=("Verdana", 10,'bold'))
		self.DiscardPolicyTextBox.grid(column=1, row=25,sticky='nswe',padx=10)
		
		self.RedirectNHPolicyTextBox = ScrolledText(self.window, background=BG0, height = 5, borderwidth=3,width=20, relief="raised")
		self.RedirectNHPolicyTextBox.configure(bg = 'white', wrap='word', fg = 'white',font=("Verdana", 10,'bold'))
		self.RedirectNHPolicyTextBox.grid(column=2,sticky='nswe', row=25)
		
		self.RedirectVRFPolicyTextBox = ScrolledText(self.window, background=BG0, height = 5, borderwidth=3,width=20, relief="raised")
		self.RedirectVRFPolicyTextBox.configure(bg = 'white', wrap='word', fg = 'white',font=("Verdana", 10,'bold'))
		self.RedirectVRFPolicyTextBox.grid(column=3,sticky='nswe', row=25,padx=10)
		
		
		# ---------------- ROW-29 ---------------#
		
		ClearDiscardPolicy=tk.Button(self.window, background=BG0,  text="Clear Discard Policy", command=self.ClearDiscardPolicy,font=("Verdana", 10,'bold'))
		ClearDiscardPolicy.grid(column=1, row=29,sticky='we',padx=10)
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
		topo_vars = yaml.load(file.read())
		topo_vars['home_directory'] = os.path.dirname(os.path.realpath(__file__))
		file.close()
		# Update the Values in the GUI and for the route programming
		try:
			for Router in topo_vars['EdgeRouters']:
				NHIPDict[Router['RouterID']]=Router['IPNH']
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
		print ("Withdrawing all routes")
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
			print(command)
			r = requests.post(exabgpurl, data={'command':command})	
		
	def HardExit(self):
		print ("Withdrawing all routes")
		for Router in topo_vars['EdgeRouters']:
			command = 'neighbor '+str(Router['RouterID'])+  ' teardown 2'
			print (command)
			r = requests.post(exabgpurl, data={'command': command})
			time.sleep(.2)
		print (" \n\n Hard Clearing the Controller BGP peering Session")
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
		popup = ProgramFlowSpecRule(ManualRouteQueue)
	
	def ShowFlowspecRoutesPopup(self):
		popup = ShowFlowspecRoutesPopup(FlowRouteQueue,self.window)
	
	def ShowSflowPopup(self):
		popup = ShowSflowPopup(SflowQueue,self.window)

	def ResetDefaultAction(self):
		self.DefaultRedirectIPRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
		self.DefaultRedirectVRFRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
		self.DefaultBlockTrafficRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
		self.DefaultDummyRad.select()
		self.defaultaction = ''
	
	def SetDefaultAction(self):
		self.defaultaction = ''
		if self.selecteddefaultaction.get() == 1:
			self.DefaultBlockTrafficRadLabel.configure(font=("Verdana", 10,'bold'),justify='left',fg='white',bg='dark green',relief='sunken')
			self.DefaultRedirectIPRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.DefaultRedirectVRFRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.defaultaction = 'discard'
		elif self.selecteddefaultaction.get() == 2:
			self.DefaultRedirectIPRadLabel.configure(font=("Verdana", 10,'bold'),justify='left',fg='white',bg='dark green',relief='sunken')
			self.DefaultBlockTrafficRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.DefaultRedirectVRFRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.defaultaction = 'redirect next-hop'
		elif self.selecteddefaultaction.get() == 3:
			self.DefaultRedirectVRFRadLabel.configure(font=("Verdana", 10,'bold'),justify='left',fg='white',bg='dark green',relief='sunken')
			self.DefaultBlockTrafficRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.DefaultRedirectIPRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.defaultaction = 'redirect VRF'
		elif self.selecteddefaultaction.get() == 5:
			self.defaultaction = ''

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
			
		if self.defaultaction !='' and self.DefaultBandwidth !='':
			for entry in self.DefaultBandwidthPolicy:
				UpdatePolicyQueue.put(entry)
			self.DefaultBandwidthTextBoxPolicy.delete('1.0', 'end')
			self.DefaultBandwidthTextBoxPolicy.configure(bg = 'dark blue', wrap='word', fg = 'white',font=("Verdana", 10,'bold'))
			self.DefaultBandwidthTextBoxPolicy.insert('end', 'Policy BW: ' +str(self.DefaultBandwidth)+ ' Mbps   Action: '+str(self.defaultaction))
			self.DefaultBandwidthTextBoxPolicy.tag_add("centered", "1.0", 'end')
			self.DefaultBandwidthTextBoxPolicy.tag_configure("centered",justify='center')

		self.ResetDefaultBandwidth()
		self.ResetDefaultAction()
		
		
	def ClearDefaultSelection(self):
		self.ResetDefaultBandwidth()
		self.ResetDefaultAction()
		
		
	def ClearDefaultPolicy(self):
		self.DefaultBandwidthPolicy = []
		self.DefaultBandwidthTextBoxPolicy.delete(1.0,'end')
		self.DefaultBandwidthTextBoxPolicy.configure(bg = 'white')
		self.DefaultBandwidthPolicy.append('DefaultBandwidth:')
		self.DefaultBandwidth = 0
		self.DefaultBandwidthPolicy.append(self.DefaultBandwidth)
		self.defaultaction =''
		self.DefaultBandwidthPolicy.append(self.defaultaction)
		for entry in self.DefaultBandwidthPolicy:
			UpdatePolicyQueue.put(entry)
	

	def ResetFlowPolicyAction(self):
		self.RedirectIPRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
		self.RedirectVRFRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
		self.BlockTrafficRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
		self.DummyRad.select()
		self.action = ''
		
	
	def SetAction(self):
		self.action = ''
		if self.selected.get() == 1:
			self.BlockTrafficRadLabel.configure(font=("Verdana", 10,'bold'),justify='left',fg='white',bg='dark green',relief='sunken')
			self.RedirectIPRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.RedirectVRFRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.action = 'discard'
		elif self.selected.get() == 2:
			self.RedirectIPRadLabel.configure(font=("Verdana", 10,'bold'),justify='left',fg='white',bg='dark green',relief='sunken')
			self.BlockTrafficRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.RedirectVRFRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.action = 'redirect next-hop'
		elif self.selected.get() == 3:
			self.RedirectVRFRadLabel.configure(font=("Verdana", 10,'bold'),justify='left',fg='white',bg='dark green',relief='sunken')
			self.BlockTrafficRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.RedirectIPRadLabel.configure(font=("Verdana",10),fg='black',bg='grey95',relief='ridge')
			self.action = 'redirect VRF'
		elif self.selected.get() == 5:
			self.action = ''

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
		self.BandwidthTextBox.insert('1.0','(Hit <enter/return> to set policy bandwidth)')
		self.BandwidthTextBox.tag_add("boldcentered", "1.0", 'end')
		self.BandwidthTextBox.tag_configure("boldcentered",justify='center',background='white')

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


	def UpdateFlowspecPolicy(self):
		DiscardPolicyList = []
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
			if self.action == 'discard':
				DiscardPolicyList.append(self.action)
				self.action = ''
				try:
					self.ListOfDiscardBadSourcePorts.extend(self.ListOfSourcePortsToAdd)
					self.ListOfDiscardBadSourcePorts = self.remove_duplicates(self.ListOfDiscardBadSourcePorts)
					self.ListOfDiscardBadDestinationPorts.extend(self.ListOfDestinationPortsToAdd)
					self.ListOfDiscardBadDestinationPorts = self.remove_duplicates(self.ListOfDiscardBadDestinationPorts)
					self.ListOfSourcePortsToAdd = []
					self.ListOfDestinationPortsToAdd = []
				except:
					pass
				try:
					for entry in self.ListOfSourcePortsToRemove:
						self.ListOfDiscardBadSourcePorts.remove(entry)
					for entry in self.ListOfDestinationPortsToRemove:
						self.ListOfDiscardBadDestinationPorts.remove(entry)
					self.ListOfSourcePortsToRemove = []
					self.ListOfDestinationPortsToRemove = []
				except:
					pass
				try:
					if self.FlowPolicyBandwidth == '' and not self.DiscardFlowPolicyBandwidth:
						self.DiscardFlowPolicyBandwidth = 0
					elif self.DiscardFlowPolicyBandwidth != 0 and not self.FlowPolicyBandwidth:
						self.FlowPolicyBandwidth = ''                      
					elif self.DiscardFlowPolicyBandwidth != self.FlowPolicyBandwidth:
						self.DiscardFlowPolicyBandwidth = self.FlowPolicyBandwidth
						self.FlowPolicyBandwidth = ''
				except:
					pass
				try:
					if self.DiscardFlowPolicyBandwidth == 0:
						self.SelectBandwidthPopup(self.window)
						pass
					else:
						self.DiscardPolicyTextBox.delete('1.0', 'end')
						self.DiscardPolicyTextBox.configure(bg = 'dark blue', wrap='word', fg = 'white',font=("Verdana", 10,'bold'))
						DiscardPolicyList.append(float(self.DiscardFlowPolicyBandwidth))
						self.DiscardPolicyTextBox.insert('end', 'Policy BW : '+str(self.DiscardFlowPolicyBandwidth)+' Mbps\n')
						DiscardPolicyList.append(self.ListOfDiscardBadSourcePorts)
						DiscardPolicyList.append(self.ListOfDiscardBadDestinationPorts)
						for entry in DiscardPolicyList:
							UpdatePolicyQueue.put(entry)
						self.DiscardPolicyTextBox.insert('end', '\nSource Ports:    ')
						for y in self.ListOfDiscardBadSourcePorts:
							self.DiscardPolicyTextBox.insert('end', str(y) + ', ')
						self.DiscardPolicyTextBox.insert('end', '\n\nDestination Ports:    ')
						for y in self.ListOfDiscardBadDestinationPorts:
							self.DiscardPolicyTextBox.insert('end', str(y) + ', ')
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
		self.ResetFlowPolicyAction()	

	def ClearPolicySelection(self):
		self.PortTextBox.delete(1.0,'end')
		self.PortTextBox.configure(bg = 'white')
		self.ResetFlowPolicyBandwidth()
		self.ResetFlowPolicyAction()
		
	def ClearDiscardPolicy(self):
		self.DiscardPolicyClear = ['discard', 0, [], []]
		self.DiscardPolicyTextBox.delete(1.0,'end')
		self.DiscardPolicyTextBox.configure(bg = 'white')
		self.ListOfDiscardBadSourcePorts = []
		self.ListOfDiscardBadDestinationPorts = []
		self.DiscardFlowPolicyBandwidth = ''
		for entry in self.DiscardPolicyClear:
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
		self.ClearDiscardPolicy()
		self.ClearDefaultPolicy()
		for Router in topo_vars['EdgeRouters']:
			command = 'neighbor '+str(Router['RouterID'])+  ' teardown 2'
			print (command)
			r = requests.post(exabgpurl, data={'command': command})
			time.sleep(.2)
		print (" \n\n Hard Clearing the Controller BGP peering Session")
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


def SendFlowsToExabgp(queue):
	while True:
		UpdateRoutes = []
		while not queue.empty():
			try:
				msg = queue.get()         # Read from the queue
				UpdateRoutes.append(msg)
				r = requests.post(exabgpurl, data={'command':msg})
				pp(msg)
				queue.task_done()
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
	ManualRouteQueue = JoinableQueue(maxsize=0)  
	ManualRouteQueue.cancel_join_thread()
	UpdatePolicyQueue = JoinableQueue(maxsize=0)  
	UpdatePolicyQueue.cancel_join_thread()


	root = tk.Tk()
	root.maxsize(width = 1800, height = 1500)
	gui = FlowspecGUI(root, SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,UpdatePolicyQueue,SignalResetQueue)
	gui.grid(row=0, column=0, sticky='nsew')
	SendFlowsToExabgpProcess = Process(target=SendFlowsToExabgp,args=(ExaBGPQueue,))
	FindAndProgramDdosFlowsProcess = Process(target=FindAndProgramDdosFlows,args=(SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,ManualRouteQueue,UpdatePolicyQueue,SignalResetQueue,ExaBGPQueue))
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

