#!/usr/bin/env python


import os
import re
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import threading
import yaml
import Tkinter as tk
from ScrolledText import ScrolledText
from Tkinter import *
import ttk
from multiprocessing import Process
from multiprocessing import Queue
from Queue import Empty, Full
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
intflow = {'keys':'agent,outputifindex,mplslabels','value':'bytes','t':'4','log':True}



# Start the server python processes afresh (used with Program switch or script)



def ProgramSflowrt():
	# program sFlow-RT to monitor LER uplinks
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

def FindAndProgramDdosFlows(SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,ManualRouteQueue,UpdatePolicyQueue,SignalResetQueue):
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
	
	while True:
		try:
			ResetSignalled = ExabgpAndQueueCalls.SignalResetQueuePoll(SignalResetQueue)
			if ResetSignalled[0] == 'RESET SIGNALLED':
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
			session = requests.Session()
			retry = Retry(connect=3, backoff_factor=0.5)
			adapter = HTTPAdapter(max_retries=retry)
			session.mount('http://', adapter)
			session.mount('https://', adapter)
			r = session.get(str(sflowrt_url)+'/activeflows/ALL/ipdest/json')
		except requests.exceptions.ConnectionError:
			r.status_code = "Connection refused"	
		rawflows = r.json()
	
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
								ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction)
								print("Flow Passed the Check (returned true) and was to be Programmed")
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
										ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction)
										print ("Checked all Policies For Flow, Doesn't exist yet, so add it using Default Policy")
										break
								except:
									pass
						except:
							pass

							# This means the Source Port or Destination port is not in this policy (or we got a Fasle)
							
						try:
							if not CheckPolicy(DataList,CurrentConfiguredSourceProtocolPortList,CurrentConfiguredDestinationProtocolPortList,CurrentAction,PolicyBandwidth,bw) and str(DataList) in FlowActionDict.keys() and SortedListOfPolicyUpdates.index(entry) == int(len(SortedListOfPolicyUpdates)-1):
								ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)))
								FlowActionDict.pop(str(DataList),None)
								ListOfFlows.remove(DataList)
								print ("Returned False  - No Source or Destination Port in the source or destination portlist - removing the flow")
								break
						except:
							pass
						
						#  Try the Default Policy (if Set)
						
						try:

							if bw < DefaultBandwidth:
								ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)))
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
								ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction)
								print ("BW > default, and there is an action.  So program the flow (using local function ProgramFlowPolicies")
						
						if DataList in ListOfFlows and 'None' in CurrentAction:
							ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)))
							FlowActionDict.pop(str(DataList),None)
							ListOfFlows.remove(DataList)
							print ("Theres a None I have to remove - Use ExabgpWithdraw fo the activeflowlist is updated")
							
						if DataList in ListOfFlows and bw < DefaultBandwidth:
							ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)))
							FlowActionDict.pop(str(DataList),None)
							ListOfFlows.remove(DataList)
							print ("No flow policy but default BW > flow bw - have to remove flows. Use ExabgpWithdraw fo the activeflowlist is updated")
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
				ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)))
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
		time.sleep(1)
		
		
def RenderTopologyVariables():
	# Updating for the main Program
	global NHVRFDict
	global NHIPDict
	script_dir = os.path.dirname(__file__)
	rel_path = "TopologyVariables.yaml"
	abs_file_path = os.path.join(script_dir, rel_path)
	file=open(abs_file_path)
	topo_vars = yaml.load(file.read())
	topo_vars['home_directory'] = os.path.dirname(os.path.realpath(__file__))
	file.close()

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
	


def ProgramFlowPolicies(DataList,ListOfFlows,FlowActionDict,ExabgpAndQueueCalls,CurrentAction):
	try:
		if len(ListOfFlows) == 0:
			ListOfFlows.append(DataList)
			FlowActionDict[str(DataList)]=CurrentAction
			ExabgpAndQueueCalls.ExaBgpAnnounce(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),CurrentAction)
			print ("Len List of flows 0 , added the flow and Dict Entry")
		elif FlowActionDict.get(str(DataList)) != None and FlowActionDict.get(str(DataList)) != CurrentAction:
			ExabgpAndQueueCalls.ExaBgpWithdraw(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),FlowActionDict.get(str(DataList)))
			FlowActionDict.pop(str(DataList),None)
			ListOfFlows.remove(DataList)
			print ("Popped the dict entry and List")
			ListOfFlows.append(DataList)
			FlowActionDict[str(DataList)]=CurrentAction
			ExabgpAndQueueCalls.ExaBgpAnnounce(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),CurrentAction)
			print ("Added flow and Dict entry and list")
		elif DataList not in ListOfFlows:
			ListOfFlows.append((DataList))
			FlowActionDict[str(DataList)]=CurrentAction
			ExabgpAndQueueCalls.ExaBgpAnnounce(str(DataList[0]),str(DataList[1]),str(DataList[2]),str(DataList[3]),str(DataList[5]),str(DataList[6]),CurrentAction)
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

	def ExaBgpAnnounce(self, ler,protocol,sourceprefix,sourceport,destinationprefix,destinationport,action):
		
		if protocol == '1':
			command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
			r = requests.post(exabgpurl, data={'command':command})
			command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
			self.ActiveFlowspecRoutes.append(command)
		else:
			command = 'neighbor ' + ler + ' announce flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' + action
			r = requests.post(exabgpurl, data={'command':command})
			command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' + action
			self.ActiveFlowspecRoutes.append(command)
	
	def ExaBgpWithdraw(self,ler,protocol,sourceprefix,sourceport,destinationprefix,destinationport,action):
		if protocol == '1':
			command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
			r = requests.post(exabgpurl, data={'command':command})
			command = 'neighbor ' + ler + ' source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'+ ' protocol ' '['+ protocol +']' ' icmp-type [=' + sourceport + ']' ' icmp-type [=' + destinationport + '] '  + action
			self.ActiveFlowspecRoutes.remove(command)			
		else:
			command = 'neighbor ' + ler + ' withdraw flow route ' 'source '+ sourceprefix + '/32 ' 'destination ' + destinationprefix + '/32'  + ' protocol ' '['+ protocol +']' ' source-port [=' + sourceport + ']' ' destination-port [=' + destinationport + '] ' +  action
			r = requests.post(exabgpurl, data={'command':command})
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
		self.popup = Toplevel(ParentWindow)
		self.popup.grid_columnconfigure(0, weight=1)
		self.popup.grid_rowconfigure(2, weight=1)
		width = ParentWindow.winfo_width()
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()))
		self.popup.lift()
		self.popup.title("Active Flowspec Rules Programmed on Edge Routers")
		self.TitleLabel=tk.Label(self.popup,text="### Active Flowspec Rules Programmed on Edge Routers###\n",font=("Rouge", 20),justify=LEFT)
		self.TitleLabel.grid(column=0, row=0,columnspan=3, sticky='n')		
		self.text_wid = tk.Text(self.popup,relief = 'raised', height=20,width=140,borderwidth=3)
		self.scroll = Scrollbar(self.popup, command=self.text_wid.yview)
		self.text_wid.grid(column=0, columnspan=3,row=2,sticky='nswe', padx=10, pady=5)
		self.scroll.grid(column=0, columnspan=3,row=2,sticky='nse',padx=10)
		self.popup.after(100,self.FlowRouteQueuePoll,FlowRouteQueue)
		self.close=Button(self.popup,text='Close Window',command=self.cleanup,font=("Rouge",12,'bold'))
		self.close.grid(row=5,column=0,columnspan=3,pady=10)
		
	def FlowRouteQueuePoll(self,c_queue):
		try:
			ListOfRoutes = c_queue.get(0)
			self.text_wid.delete('1.0', END)
			self.text_wid.insert('end','Neighbor		Source			Destination			Protocol		Source Port		Destination Port		Active Action\n\n')
			for line in ListOfRoutes:
				for r in (('neighbor ',''),(' source-port ',''), (' destination-port ',''),(' source ','		'), (' destination ','			'), ('protocol ','			'),('[',''),(']','		')):
					line = line.replace(*r)
				self.text_wid.insert('end', line+'\n')
		except Empty:
			pass
		finally:
			self.text_wid.configure(bg = 'blue',fg = 'white',font=("Rouge", 12, 'bold'))
			self.popup.after(500, self.FlowRouteQueuePoll, c_queue)
			
	def cleanup(self):
		self.popup.destroy()



class ShowSflowPopup(object):
	def __init__(self,SflowQueue,ParentWindow):
		self.popup = Toplevel(ParentWindow)
		height = ParentWindow.winfo_height()/2
		width = ParentWindow.winfo_width()
		self.popup.grid_columnconfigure(0, weight=1)
		self.popup.grid_rowconfigure(2, weight=1)
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.popup.lift()
		self.popup.title("Active Inspected sFlow Records From Edge Routers")
		self.TitleLabel=tk.Label(self.popup,text="### Active Inspected sFlow Records From Edge Routers###\n",font=("Rouge", 20),justify='center')
		self.TitleLabel.grid(column=0, row=0,columnspan=3, sticky='n')
		self.text_wid = tk.Text(self.popup,relief = 'raised', height=20,width=130,borderwidth=3)
		self.scroll = Scrollbar(self.popup, command=self.text_wid.yview)
		self.text_wid.grid(column=0, columnspan=3,row=2,sticky='nswe',padx=10, pady=5)
		self.scroll.grid(column=0, columnspan=3,row=2,sticky='nse',padx=10)
		self.popup.after(100,self.SflowQueuePoll,SflowQueue)
		self.close=Button(self.popup,text='Close Window',command=self.cleanup,font=("Rouge",12,'bold'))
		self.close.grid(row=5,column=0,columnspan=3,pady=10)
		
	def SflowQueuePoll(self,c_queue):
		try:
			self.ListOfFlows = c_queue.get(0)
			self.text_wid.delete('1.0', END)
			self.text_wid.insert('end', 'Router		Protocol		Source-IP		SourcePort		Source Intf-ID		Destination-IP		DestinationPort		Bandwidth\n')
			for line in self.ListOfFlows:
				line = '		'.join(line)
				self.text_wid.insert('end', str(line) + '\n')
		except Empty:
			pass
		finally:
			self.text_wid.configure(bg = 'blue',fg = 'white',font=("Rouge", 12,'bold'))
			self.popup.after(500, self.SflowQueuePoll, c_queue)
				
	def cleanup(self):
		self.popup.destroy()		

	

class ProgramFlowSpecRule(object):
	def __init__(self,ManualRouteQueue):
		self.ManualFlowRoute = []
		self.selected = tk.IntVar()
		self.actionselected = tk.IntVar()
		self.popup = Toplevel()
		self.popup.title("Program Manual BGP Flowspec Rule")
		self.announce = Radiobutton(self.popup,text='Announce Rule', value=1, variable=self.selected,font=("Rouge",12))
		self.withdraw = Radiobutton(self.popup,text='Withdraw Rule', value=2, variable=self.selected,font=("Rouge",12))
		self.announce.grid(column=0,row=0,sticky='w')
		self.withdraw.grid(column=0,row=1,sticky='w')
		self.Peer = Entry(self.popup,width=30, justify='center',font=("Rouge",10,'italic'))
		self.Peer.insert(END, '<Peer IP Address>')
		self.Peer.grid(row=2,column=1,padx=5)
		self.Peer.focus_set()
		self.SourcePrefix = Entry(self.popup,width=30, justify='center',font=("Rouge",10,'italic'))
		self.SourcePrefix.insert(END, '<Source Prefix/Mask>')
		self.SourcePrefix.grid(row=2,column=2,padx=5)
		self.DestinationPrefix = Entry(self.popup,width=30, justify='center',font=("Rouge",10,'italic'))
		self.DestinationPrefix.insert(END, '<Destination Prefix/mask>')
		self.DestinationPrefix.grid(row=2,column=3,padx=5)
		self.Protocol = Entry(self.popup,width=30, justify='center',font=("Rouge",10,'italic'))
		self.Protocol.insert(END, '<Protocol>')
		self.Protocol.grid(row=2,column=4,padx=5)
		self.SourcePort = Entry(self.popup,width=30, justify='center',font=("Rouge",10,'italic'))
		self.SourcePort.insert(END, '<Source Port>')
		self.SourcePort.grid(row=2,column=5,padx=5)
		self.DestinationPort = Entry(self.popup,width=30, justify='center',font=("Rouge",10,'italic'))
		self.DestinationPort.insert(END, '<Destination Port>')
		self.DestinationPort.grid(row=2,column=6,padx=5)
		self.DiscardRadioButton = Radiobutton(self.popup,text='Block Traffic', value=1, variable=self.actionselected,font=("Rouge",12))
		self.RedirectNHRadioButton = Radiobutton(self.popup,text='Redirect To Next Hop', value=2, variable=self.actionselected,font=("Rouge",12))
		self.RedirectVRFRadioButton = Radiobutton(self.popup,text='Redirect To VRF', value=3, variable=self.actionselected,font=("Rouge",12))
		self.DiscardRadioButton.grid(column=1,row=3, sticky='we')
		self.RedirectNHRadioButton.grid(column=2,row=3,sticky='we')
		self.RedirectVRFRadioButton.grid(column=3,row=3,sticky='we')
		self.button = Button(self.popup,text="Program Rule",command=self.callback,font=("Rouge",12,'bold'))
		self.button.grid(row=4,column=0,padx=10)  
		self.close=Button(self.popup,text='Close Window',command=self.cleanup,font=("Rouge",12,'bold'))
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
			


### Tkinter GUI Class

   
class FlowspecGUI(object):
	def __init__(self,SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,UpdatePolicyQueue,SignalResetQueue):
		
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
		self.window = tk.Tk()
		self.window.grid_columnconfigure(0, weight=1)
		self.window.grid_columnconfigure(1, weight=1)
		self.window.grid_columnconfigure(2, weight=1)
		self.window.grid_rowconfigure(17, weight=2)
		self.window.grid_rowconfigure(25, weight=1)
		self.window.title("BGP Flowspec Policy Manager")
		
		# ---------------- ROW-0 ---------------#
		
		TitleLabel=tk.Label(text="### DDoS Flow Policy Management Using BGP Flowspec ###\n",font=("Rouge", 22,'bold'),justify=LEFT,fg='dark blue')
		TitleLabel.grid(column=0, row=0,columnspan=3, sticky='we')
		
		# ---------------- ROW-1 ---------------#
		
		PolicyTitleLabel=tk.Label(text='########## Default Flow Inspection Policy Bandwidth & Action Policy ###########',font=("Rouge", 16,'bold'),justify=LEFT,fg='dark blue')
		PolicyTitleLabel.grid(column=0, row=1,columnspan=4, sticky='we')
		
		# ---------------- ROW-2 ---------------#
		
		DefaultActionRuleLabel=tk.Label(text="Select the Default Flow Policy ",font=("Rouge", 14),justify=RIGHT,anchor=NW,)
		DefaultActionRuleLabel.grid(column=0, row=2,columnspan=3,sticky=N+W)
		
		# ---------------- ROW-3 ---------------#
		
		self.selecteddefaultaction = tk.IntVar()
				
		self.DefaultBlockTrafficRad = Radiobutton(self.window, value=1, variable=self.selecteddefaultaction, command=self.SetDefaultAction)
		self.DefaultBlockTrafficRadLabel = Label(self.window,width=20,text='Block Traffic',font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.DefaultRedirectIPRad = Radiobutton(self.window,value=2, variable=self.selecteddefaultaction, command=self.SetDefaultAction)
		self.DefaultRedirectIPRadLabel = Label(self.window,width=20,text='Redirect To Next Hop',font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.DefaultRedirectVRFRad = Radiobutton(self.window,value=3, variable=self.selecteddefaultaction, command=self.SetDefaultAction)
		self.DefaultRedirectVRFRadLabel = Label(self.window,width=20,text='Redirect To VRF',font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.DefaultBlockTrafficRad.grid(column=0, row=3,sticky='w',padx=10)
		self.DefaultRedirectIPRad.grid(column=1, row=3, sticky='w',padx=10)
		self.DefaultRedirectVRFRad.grid(column=2, row=3,sticky='w',padx=10)
		self.DefaultBlockTrafficRadLabel.grid(column=0, row=3, sticky='w', padx=50)
		self.DefaultRedirectIPRadLabel.grid(column=1, row=3,sticky='w',padx=50)
		self.DefaultRedirectVRFRadLabel.grid(column=2, row=3,sticky='w',padx=50)
		self.DefaultDummyRad = Radiobutton(self.window, value=5, variable=self.selecteddefaultaction,command=self.SetDefaultAction)
		
		# ---------------- ROW-4 ---------------#
		
		DefaultFlowPolicyBwLabel=tk.Label(text="Default Policy Inspection Bandwidth (Mbps): ",font=("Rouge", 14),justify=RIGHT)
		DefaultFlowPolicyBwLabel.grid(column=0,row=4,sticky='e',pady=10)
		
		self.DefaultBandwidthTextBox = tk.Text(self.window,height = 1, width = 40, borderwidth=3, relief="raised",font=("Rouge",12,'bold italic'),fg='dark grey')
		self.DefaultBandwidthTextBox.insert('1.0','  (Click <enter/return> to set policy bandwidth)')
		self.DefaultBandwidthTextBox.bind("<Button-1>", self.SetDefaultBandwidthTextBoxFocus)
		self.DefaultBandwidthTextBox.bind("<Return>", self.GetDefaultFlowPolicyBandWidth)
		self.DefaultBandwidthTextBox.bind("<FocusOut>", self.SetDefaultBandwidthTextBoxUnFocus)
		self.DefaultBandwidthTextBox.bind("<FocusIn>", self.SetDefaultBandwidthTextBoxFocus)
		self.DefaultBandwidthTextBox.grid(column=1, columnspan=2, row=4,sticky='w',padx=30)
		
		# ---------------- ROW-5 ---------------#

		SectionLabel=tk.Label(text="Program Default Policy >>>",font=("Rouge", 14,'bold'),justify=LEFT)
		SectionLabel.grid(column=0, columnspan=2,row=5,sticky='e',padx=120)
		push_button0=tk.Button(self.window, text="Click Here", command=self.ProgramDefaultPolicy,font=("Rouge", 14, 'bold'),fg='white',bg='dark grey')
		push_button0.grid(column=1, row=5,sticky='e')
		ClearDefaultSelection=tk.Button(self.window, text="Clear Selections", command=self.ClearDefaultSelection,font=("Rouge", 14,'bold italic'))
		ClearDefaultSelection.grid(column=2, row=5,sticky='w',padx=10)

		# ---------------- ROW-6 ---------------#

		SpacerLabel=tk.Label(text="\n",font=("Rouge", 12),justify=RIGHT,anchor=NW)
		SpacerLabel.grid(column=0, columnspan=3,row=6,sticky=W)		
	
		# ---------------- ROW-7 ---------------#

		SectionLabel=tk.Label(text="Active Default Policy:",font=("Rouge", 14,'bold'),justify=LEFT,fg='dark blue')
		SectionLabel.grid(column=0, row=7,sticky='e',padx=10)
		
		self.DefaultBandwidthTextBoxPolicy = tk.Text(self.window,height = 1, width = 40, borderwidth=3, relief="raised",font=("Rouge",12,'bold'))
		self.DefaultBandwidthTextBoxPolicy.grid(column=1, columnspan=2,row=7,sticky='w',padx=10)

		ClearDefaultPolicy=tk.Button(self.window, text="Clear Default Policy",command=self.ClearDefaultPolicy,font=("Rouge", 12,'bold'))
		ClearDefaultPolicy.grid(column=2, row=7,sticky='w',padx=80)

		# ---------------- ROW-8 ---------------#
		
		PolicyTitleLabel=tk.Label(text='\n############ Configure Flow Inspection Policy Bandwidth, Action & Ports #############',font=("Rouge", 14,'bold'),justify=LEFT,fg='dark blue')
		PolicyTitleLabel.grid(column=0, row=8,columnspan=4, sticky='we')

		
		# ---------------- ROW-9 ---------------#
		
		self.selected = tk.IntVar()
		ActionRuleLabel=tk.Label(text="Select the Flow Policy (Required)",font=("Rouge", 14),justify=RIGHT,anchor=NW,)
		ActionRuleLabel.pack()
		ActionRuleLabel.grid(column=0, row=9,columnspan=3,sticky=N+W)
		
		# ---------------- ROW-10 ---------------#
		
		self.BlockTrafficRad = Radiobutton(self.window, value=1, variable=self.selected, command=self.SetAction)
		self.BlockTrafficRadLabel = Label(self.window,width=20,text='Block Traffic',font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.RedirectIPRad = Radiobutton(self.window,value=2, variable=self.selected, command=self.SetAction)
		self.RedirectIPRadLabel = Label(self.window,width=20,text='Redirect To Next Hop',font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.RedirectVRFRad = Radiobutton(self.window,value=3, variable=self.selected, command=self.SetAction)
		self.RedirectVRFRadLabel = Label(self.window,width=20,text='Redirect To VRF',font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.BlockTrafficRad.grid(column=0, row=10, sticky='w',padx=10)
		self.RedirectIPRad.grid(column=1, row=10, sticky='w',padx=10)
		self.RedirectVRFRad.grid(column=2, row=10,sticky='w',padx=10)
		self.BlockTrafficRadLabel.grid(column=0, row=10, sticky='w',padx=50)
		self.RedirectIPRadLabel.grid(column=1, row=10,sticky='w',padx=50)
		self.RedirectVRFRadLabel.grid(column=2, row=10,sticky='w',padx=50)
		self.DummyRad = Radiobutton(self.window, value=5, variable=self.selected,command=self.SetAction)


		# ---------------- ROW-11 ---------------#
		
		
		FlowPolicyBwLabel=tk.Label(text="Flow Policy Inspection Bandwidth (Mbps): ",font=("Rouge", 14),justify=RIGHT)
		FlowPolicyBwLabel.grid(column=0,row=11,sticky='e',pady=10)
		
		self.BandwidthTextBox = tk.Text(self.window,height = 1, width = 40, borderwidth=3, relief="raised",font=("Rouge",12,'bold italic'),fg='dark grey')
		self.BandwidthTextBox.insert('1.0','    (Click <enter/return> to set policy bandwidth)')
		self.BandwidthTextBox.bind("<Button-1>", self.SetBandwidthTextBoxFocus)
		self.BandwidthTextBox.bind("<Return>", self.GetFlowPolicyBandWidth)
		self.BandwidthTextBox.bind("<FocusOut>", self.SetBandwidthTextBoxUnFocus)
		self.BandwidthTextBox.bind("<FocusIn>", self.SetBandwidthTextBoxFocus)
		self.BandwidthTextBox.grid(column=1, columnspan=2, row=11,sticky='w',padx=30)
	

		# ---------------- ROW-15 ---------------#
		
		PortListLabel=tk.Label(text="Select the port(s):protocols to add/remove from the list below: ",font=("Rouge", 14),justify=RIGHT,anchor=NW)
		PortListLabel.pack()
		PortListLabel.grid(column=0, columnspan=3,row=15,sticky=W,pady=10)
		
		
		# ---------------- ROW-16 ---------------#
		
		SourcePortLabel=tk.Label(text="Select Source Ports/Protocols: ",font=("Rouge", 12,'bold'),anchor=N)
		SourcePortLabel.pack()
		SourcePortLabel.grid(column=0, row=16)
		
		DestinationPortLabel=tk.Label(text="Select Destination Ports/Protocols: ",font=("Rouge", 12,'bold'),anchor=N)
		DestinationPortLabel.pack()
		DestinationPortLabel.grid(column=1, row=16)

		SelectPortButton = tk.Button(self.window, text=" Add ", width=12, command=self.AddToPolicy,font=("Rouge",12,'bold'))
		SelectPortButton.grid(column=2, row=16,padx=10,sticky='w')
		
		RemovePortButton = tk.Button(self.window,text=" Remove ", width=12, command=self.RemoveFromPolicy,font=("Rouge",12,'bold'))
		RemovePortButton.grid(column=2, row=16,padx=30,sticky='e')


		self.DiscardPolicyTextBox = ScrolledText(self.window,height = 5, borderwidth=3,width=30, relief="raised")
		self.DiscardPolicyTextBox.configure(bg = 'white', wrap=WORD, fg = 'white',font=("Rouge", 12,'bold'))
		self.DiscardPolicyTextBox.grid(column=0, row=25,sticky='nswe',padx=10)
		
		# ---------------- ROW-17 ---------------#
		
		scrollbar = Scrollbar(self.window, orient="vertical")
		scrollbar.grid(column=0, row=17,sticky='nse')
		self.SourcePorts = Listbox(self.window, exportselection=0, relief = 'raised', height = 5, yscrollcommand=scrollbar.set, font=("Helvetica", 12,'bold'),selectmode=MULTIPLE)
		self.SourcePorts.grid(column=0, row=17,sticky='nswe',padx=15)
		scrollbar.config(command=self.SourcePorts.yview)
		
		for x in PortList:
			self.SourcePorts.insert(END, x)
			
		self.SourcePorts.bind('<<ListboxSelect>>',self.CurSourceSelet)
		
		scrollbar1 = Scrollbar(self.window, orient="vertical")
		scrollbar1.grid(column=1, row=17,sticky='nse')
		self.DestinationPorts = Listbox(self.window, exportselection=0, relief = 'raised', width=30, height = 5, yscrollcommand=scrollbar1.set, font=("Helvetica", 12,'bold'),selectmode=MULTIPLE)
		self.DestinationPorts.place(relx = 0.5, rely = 0.5, anchor="center")
		self.DestinationPorts.grid(column=1, row=17,sticky='nswe',padx=15)
		scrollbar1.config(command=self.DestinationPorts.yview)
		
		for x in PortList:
			self.DestinationPorts.insert(END, x)
			
		self.DestinationPorts.bind('<<ListboxSelect>>',self.CurDestinationSelet)
		
		self.PortTextBox = ScrolledText(self.window,width=30,height = 5, borderwidth=3, relief="raised",font=("Rouge",12,'bold'))
		self.PortTextBox.grid(column=2, row=17,sticky='nswe',padx=10)
		
		# ---------------- ROW-22 ---------------#

		ProgramFlowPolicyLabel=tk.Label(text="Program Flow Policy >>>",font=("Rouge", 14,'bold'),justify=LEFT)
		ProgramFlowPolicyLabel.grid(column=0, columnspan=2,row=22,sticky='e',padx=120)
		ProgramFlowPolicyButton=tk.Button(self.window, text="Click Here", command=self.UpdateFlowspecPolicy,font=("Rouge", 14,'bold'),fg='white',bg='dark grey')
		ProgramFlowPolicyButton.grid(column=1, row=22,sticky='e')
		ClearPolicySelection=tk.Button(self.window, text="Clear Selections", command=self.ClearPolicySelection,font=("Rouge", 14,'bold italic'))
		ClearPolicySelection.grid(column=2, row=22,sticky='w',padx=10)

		
		# ---------------- ROW-23 ---------------#
		
		ProgrammedPolicyLabel=tk.Label(text="\n",font=("Rouge", 12),justify=RIGHT,anchor=NW)
		ProgrammedPolicyLabel.pack()
		ProgrammedPolicyLabel.grid(column=0, columnspan=3,row=23,sticky=W)
		
		# ---------------- ROW-24 ---------------#
		
		DiscardPolicyLabel=tk.Label(text="Active Discard Policy",font=("Rouge", 14,'bold'),fg='dark blue')
		DiscardPolicyLabel.pack()
		DiscardPolicyLabel.grid(column=0, row=24)
		
		RedirectNHPolicyLabel=tk.Label(text="Active Redirect NH Policy: ",font=("Rouge", 14,'bold'),fg='dark blue')
		RedirectNHPolicyLabel.pack()
		RedirectNHPolicyLabel.grid(column=1, row=24)
		
		RedirectVRFPolicyLabel=tk.Label(text="Active Redirect VRF Policy: ",font=("Rouge", 14,'bold'),fg='dark blue')
		RedirectVRFPolicyLabel.pack()
		RedirectVRFPolicyLabel.grid(column=2, row=24)
		
		
		# ---------------- ROW-25 ---------------#

		self.DiscardPolicyTextBox = ScrolledText(self.window,height = 5, borderwidth=3,width=30, relief="raised")
		self.DiscardPolicyTextBox.configure(bg = 'white', wrap=WORD, fg = 'white',font=("Rouge", 12,'bold'))
		self.DiscardPolicyTextBox.grid(column=0, row=25,sticky='nswe',padx=10)
		
		self.RedirectNHPolicyTextBox = ScrolledText(self.window,height = 5, borderwidth=3,width=30, relief="raised")
		self.RedirectNHPolicyTextBox.configure(bg = 'white', wrap=WORD, fg = 'white',font=("Rouge", 12,'bold'))
		self.RedirectNHPolicyTextBox.grid(column=1,sticky='nswe', row=25)
		
		self.RedirectVRFPolicyTextBox = ScrolledText(self.window,height = 5, borderwidth=3,width=30, relief="raised")
		self.RedirectVRFPolicyTextBox.configure(bg = 'white', wrap=WORD, fg = 'white',font=("Rouge", 12,'bold'))
		self.RedirectVRFPolicyTextBox.grid(column=2,sticky='nswe', row=25,padx=10)
		
		
		# ---------------- ROW-29 ---------------#
		
		ClearDiscardPolicy=tk.Button(self.window, text="Clear Discard Policy", command=self.ClearDiscardPolicy,font=("Rouge", 12,'bold'))
		ClearDiscardPolicy.grid(column=0, row=29,sticky='we',padx=10)
		ClearRedirectNHPolicy=tk.Button(self.window, text="Clear Redirect NH Policy", command=self.ClearRedirectNHPolicy,font=("Rouge", 12,'bold'))
		ClearRedirectNHPolicy.grid(column=1, row=29,sticky='we',padx=10)
		ClearRedirectVRFPolicy=tk.Button(self.window, text="Clear Redirect VRF Policy", command=self.ClearRedirectVRFPolicy,font=("Rouge", 12,'bold'))
		ClearRedirectVRFPolicy.grid(column=2, row=29,sticky='we',padx=10)
		
		# ---------------- ROW-31 ---------------#
		
		SectionLabel=tk.Label(text="\n###################### View Live Flow Information ###########################",font=("Rouge", 14,'bold'),justify=LEFT,fg='dark blue')
		SectionLabel.grid(column=0, row=31,columnspan=3,sticky='we')
		
		# ---------------- ROW-32 ---------------#
		
		FlowspecRoutes=tk.Button(self.window, text="Show Flowspec Routes Click Here (Pop Up)",width=37,command=self.ShowFlowspecRoutesPopup,font=("Rouge", 14,'bold'),fg='white',bg='dark grey')
		FlowspecRoutes.grid(column=0,columnspan=2,sticky='w',row=32,padx=10)
		
		ActiveSflow=tk.Button(self.window, text="Show Active sFlow Click Here (Pop Up)", width=37,command=self.ShowSflowPopup,font=("Rouge", 14,'bold'),fg='white',bg='dark grey')
		ActiveSflow.grid(column=1,columnspan=2,sticky='e',row=32,padx=10)
		
		# ---------------- ROW-33 ---------------#
		
		PolicyTitleLabel=tk.Label(text="\n######################## Manual Flowspec Rule Push ########################",font=("Rouge", 14,'bold'),justify=LEFT,fg='dark blue')
		PolicyTitleLabel.grid(column=0, row=33,columnspan=3, sticky='we')
		
		# ---------------- ROW-35 ---------------#
		
		SectionLabel=tk.Label(text="Program Manual Flowspec Rule >>>",font=("Rouge", 14, 'bold'),justify=LEFT)
		SectionLabel.grid(column=0, columnspan=2, row=35,sticky='e')
		push_button0=tk.Button(self.window, text="Click Here (Pop up)", command=self.ProgramFlowSpecRule, borderwidth=3, height = 1,font=("Rouge", 14,'bold'),fg='white',bg='dark grey')
		push_button0.grid(column=2, row=35,sticky='w')
		
		#---------------- ROW-36 ---------------#
		
		FooterLabel=tk.Label(text="\n##################################################################################",font=("Rouge", 14,'bold'),justify=LEFT,fg='dark blue')
		FooterLabel.grid(column=0, row=36,columnspan=3,sticky='we')
		
		
		#---------------- ROW-37 ---------------#
		
		QuitButton=tk.Button(self.window, text="QUIT", command=self.Quit,font=("Rouge", 18,'bold'), borderwidth=3, height = 1, fg = 'white', bg = 'red')
		QuitButton.grid(column=1,row=37,sticky='we',pady=10)

		QuitButton=tk.Button(self.window, text="RESET POLICY MANAGER", command=self.RestartPolicyManager,font=("Rouge", 14,'bold'), borderwidth=3, height = 1, fg = 'white', bg = 'dark blue')
		QuitButton.grid(column=0,row=37,sticky='w',pady=10,padx=10)
		
		# Refresh Window with after call to Update the GUI for any TopologyVariables.yaml changes
		self.window.after(1000, self.UpdateGUI)




	# All the methods related to this class are below
	

	def UpdateGUI(self):
		stamp = os.stat(self.TopologyVariables).st_mtime
		if stamp != self._cached_stamp: 			# Well the TopologyVariables File Changed
			self._cached_stamp = stamp
			self.RenderTopologyVariables()
			self.SourcePorts.delete(0, END)
			self.DestinationPorts.delete(0, END)
			for x in self.PortList:
				self.SourcePorts.insert(END, x)
			self.SourcePorts.bind('<<ListboxSelect>>',self.CurSourceSelet)
			for x in self.PortList:
			    self.DestinationPorts.insert(END, x)
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
		self.popup = Toplevel(ParentWindow)
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.popup.lift()
		self.popup.title("Exiting Application")
		self.TitleLabel=tk.Label(self.popup,text="\nYou're Exiting the App!\n\nSelect What you want to do with the BGP Peers and Flow Routes?",font=("Rouge", 14,'bold'),justify='center')
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.OneByOne=Button(self.popup,text='Withdraw One By One',command=self.WithdrawRoutesOneByOne,font=("Rouge",12,'bold'),width=20,fg='black',bg='light grey')
		self.ResetAll=Button(self.popup,text='Reset BGP Peers',command=self.HardExit,font=("Rouge",12,'bold'),width=20,fg='black',bg='light grey')
		self.LeaveActive=Button(self.popup,text='Leave Routes Active',command=self.SoftExit,font=("Rouge",12,'bold'),width=20,fg='black',bg='light grey')
		self.close=Button(self.popup,text='Cancel',command=self.popup.destroy,font=("Rouge",12,'bold'),width=20,fg='black',bg='light grey')
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
		self.RemovingLabel=tk.Label(self.popup,text="\nRemoving Routes....",font=("Rouge", 12,'bold'),justify='center')
		self.RemovingLabel.grid(column=0, row=4,sticky='wn',pady=20,padx=20)
		if self.bytes <= self.maxbytes:
			# read more bytes after 200 ms
			self.popup.after(200, self.read_bytes)
		else:
			self.RemovingLabel.destroy
			self.DoneLabel=tk.Label(self.popup,text="\nDone!!!",font=("Rouge", 12,'bold'),justify='center')
			self.DoneLabel.grid(column=0, row=4,sticky='en',pady=20,padx=20)
			self.popup.after(2000,self.terminate)
			
	def terminate(self):
			t1.terminate()
			self.window.destroy()

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
		self.DoneLabel=tk.Label(self.popup,text="\nDone!!!",font=("Rouge", 14,'bold'),justify='center')
		self.DoneLabel.grid(column=1, row=4,sticky='n',pady=20,padx=20)
		self.popup.after(1000,self.terminate)
		
	def SoftExit(self):
		self.DoneLabel=tk.Label(self.popup,text="\nClosing GUI Only!!!",font=("Rouge", 14,'bold'),justify='center')
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
		self.DefaultRedirectIPRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.DefaultRedirectVRFRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.DefaultBlockTrafficRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.DefaultDummyRad.select()
		self.defaultaction = ''
	
	def SetDefaultAction(self):
		self.defaultaction = ''
		if self.selecteddefaultaction.get() == 1:
			self.DefaultBlockTrafficRadLabel.configure(font=("Rouge", 12,'bold'),justify=LEFT,fg='black',bg='green',relief='raised',borderwidth=3)
			self.DefaultRedirectIPRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.DefaultRedirectVRFRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.defaultaction = 'discard'
		elif self.selecteddefaultaction.get() == 2:
			self.DefaultRedirectIPRadLabel.configure(font=("Rouge", 12,'bold'),justify=LEFT,fg='black',bg='green',relief='raised',borderwidth=3)
			self.DefaultBlockTrafficRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.DefaultRedirectVRFRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.defaultaction = 'redirect next-hop'
		elif self.selecteddefaultaction.get() == 3:
			self.DefaultRedirectVRFRadLabel.configure(font=("Rouge", 12,'bold'),justify=LEFT,fg='black',bg='green',relief='raised',borderwidth=3)
			self.DefaultBlockTrafficRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.DefaultRedirectIPRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.defaultaction = 'redirect VRF'
		elif self.selecteddefaultaction.get() == 5:
			self.defaultaction = ''

	def GetDefaultFlowPolicyBandWidth(self, event):
		self.DefaultBandwidth = self.DefaultBandwidthTextBox.get(1.0,END)
		self.DefaultBandwidth = self.DefaultBandwidth.strip('\n')
		if self.DefaultBandwidth != '':
			self.DefaultBandwidthTextBox.delete('1.0', END)
			self.DefaultBandwidthTextBox.configure(font=("Rouge",12,'bold'),fg='black')
			self.DefaultBandwidthTextBox.insert('1.0','Default Flow Policy BW: ')
			self.DefaultBandwidthTextBox.insert(INSERT,self.DefaultBandwidth+'  Mbps')
			self.DefaultBandwidthTextBox.tag_add("boldcentered", "1.0", END)
			self.DefaultBandwidthTextBox.tag_configure("boldcentered", background='green',justify='center')
			return 'break'
		else:
			self.ResetDefaultBandwidth()

	def SetDefaultBandwidthTextBoxUnFocus(self, event):
		if self.DefaultBandwidth == 0:
			self.ResetDefaultBandwidth()
		elif self.DefaultBandwidth != '':
			self.DefaultBandwidthTextBox.delete('1.0', END)
			self.DefaultBandwidthTextBox.configure(font=("Rouge",12,'bold'),fg='black')
			self.DefaultBandwidthTextBox.insert('1.0','Flow Policy BW: ')
			self.DefaultBandwidthTextBox.insert(INSERT,str(self.DefaultBandwidth)+'  Mbps')
			self.DefaultBandwidthTextBox.tag_add("boldcentered", "1.0", END)
			self.DefaultBandwidthTextBox.tag_configure("boldcentered", background='green',justify='center')
			return 'break'
		else:
			self.ResetDefaultBandwidth()

	def SetDefaultBandwidthTextBoxFocus(self, event):
		self.DefaultBandwidthTextBox.focus_set()
		self.DefaultBandwidthTextBox.delete('1.0',END)
		self.DefaultBandwidthTextBox.configure(font=("Rouge",12,'bold'),fg='black')
		self.DefaultBandwidthTextBox.tag_add("boldcentered", "1.0", END)
		self.DefaultBandwidthTextBox.tag_configure("boldcentered",justify='center',background='white')

	def ResetDefaultBandwidth(self):
		self.DefaultBandwidthTextBox.delete(1.0,END)
		self.DefaultBandwidthTextBox.configure(bg = 'white')
		self.DefaultBandwidth = ''
		self.DefaultBandwidthTextBox.configure(font=("Rouge",12,'bold italic'),fg='dark grey')
		self.DefaultBandwidthTextBox.insert('1.0','(Click <enter/return> to set policy bandwidth)')
		self.DefaultBandwidthTextBox.tag_add("boldcentered", "1.0", END)
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
			self.DefaultBandwidthPolicy.append(self.DefaultBandwidth)
		except:
			self.DefaultBandwidth = 0
			self.DefaultBandwidthPolicy.append(self.DefaultBandwidth)
		try:
			self.DefaultBandwidthPolicy.append(self.defaultaction)
		except:
			self.defaultaction =''
			self.DefaultBandwidthPolicy.append(self.defaultaction)
			
		if self.defaultaction !='' and self.DefaultBandwidth !='':
			for entry in self.DefaultBandwidthPolicy:
				UpdatePolicyQueue.put(entry)
			self.DefaultBandwidthTextBoxPolicy.delete('1.0', END)
			self.DefaultBandwidthTextBoxPolicy.configure(bg = 'blue', wrap=WORD, fg = 'white',font=("Rouge", 12,'bold'))
			self.DefaultBandwidthTextBoxPolicy.insert(END, 'Policy BW: ' +str(self.DefaultBandwidth)+ ' Mbps   Action: '+str(self.defaultaction))
			self.DefaultBandwidthTextBoxPolicy.tag_add("centered", "1.0", END)
			self.DefaultBandwidthTextBoxPolicy.tag_configure("centered",justify='center')

		self.ResetDefaultBandwidth()
		self.ResetDefaultAction()
		
		
	def ClearDefaultSelection(self):
		self.ResetDefaultBandwidth()
		self.ResetDefaultAction()
		
		
	def ClearDefaultPolicy(self):
		self.DefaultBandwidthPolicy = []
		self.DefaultBandwidthTextBoxPolicy.delete(1.0,END)
		self.DefaultBandwidthTextBoxPolicy.configure(bg = 'white')
		self.DefaultBandwidthPolicy.append('DefaultBandwidth:')
		self.DefaultBandwidth = 0
		self.DefaultBandwidthPolicy.append(self.DefaultBandwidth)
		self.defaultaction =''
		self.DefaultBandwidthPolicy.append(self.defaultaction)
		for entry in self.DefaultBandwidthPolicy:
			UpdatePolicyQueue.put(entry)
	

	def ResetFlowPolicyAction(self):
		self.RedirectIPRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.RedirectVRFRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.BlockTrafficRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
		self.DummyRad.select()
		self.action = ''
		
	
	def SetAction(self):
		self.action = ''
		if self.selected.get() == 1:
			self.BlockTrafficRadLabel.configure(font=("Rouge", 12,'bold'),justify=LEFT,fg='black',bg='green',relief='raised',borderwidth=3)
			self.RedirectIPRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.RedirectVRFRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.action = 'discard'
		elif self.selected.get() == 2:
			self.RedirectIPRadLabel.configure(font=("Rouge", 12,'bold'),justify=LEFT,fg='black',bg='green',relief='raised',borderwidth=3)
			self.BlockTrafficRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.RedirectVRFRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.action = 'redirect next-hop'
		elif self.selected.get() == 3:
			self.RedirectVRFRadLabel.configure(font=("Rouge", 12,'bold'),justify=LEFT,fg='black',bg='green',relief='raised',borderwidth=3)
			self.BlockTrafficRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.RedirectIPRadLabel.configure(font=("Rouge",12,'bold'),fg='black',bg='light grey',relief='ridge',borderwidth=3)
			self.action = 'redirect VRF'
		elif self.selected.get() == 5:
			self.action = ''

	def GetFlowPolicyBandWidth(self, event):
		self.FlowPolicyBandwidth = self.BandwidthTextBox.get(1.0,END)
		self.FlowPolicyBandwidth = self.FlowPolicyBandwidth.strip('\n')
		if self.FlowPolicyBandwidth != '':
			self.BandwidthTextBox.delete('1.0', END)
			self.BandwidthTextBox.configure(font=("Rouge",12,'bold'),fg='black')
			self.BandwidthTextBox.insert('1.0','Flow Policy BW: ')
			self.BandwidthTextBox.insert(INSERT,self.FlowPolicyBandwidth+'  Mbps')
			self.BandwidthTextBox.tag_add("boldcentered", "1.0", END)
			self.BandwidthTextBox.tag_configure("boldcentered", background='green',justify='center')
			return 'break'
		else:
			self.ResetFlowPolicyBandwidth()

	def SetBandwidthTextBoxUnFocus(self, event):
		if self.FlowPolicyBandwidth != '':
			self.BandwidthTextBox.delete('1.0', END)
			self.BandwidthTextBox.configure(font=("Rouge",12,'bold'),fg='black')
			self.BandwidthTextBox.insert('1.0','Flow Policy BW: ')
			self.BandwidthTextBox.insert(INSERT,self.FlowPolicyBandwidth+'  Mbps')
			self.BandwidthTextBox.tag_add("boldcentered", "1.0", END)
			self.BandwidthTextBox.tag_configure("boldcentered", background='green',justify='center')
			return 'break'
		else:
			self.ResetFlowPolicyBandwidth()

	def SetBandwidthTextBoxFocus(self, event):
		self.BandwidthTextBox.focus_set()
		self.BandwidthTextBox.delete('1.0',END)
		self.BandwidthTextBox.configure(font=("Rouge",12,'bold'),fg='black')
		self.BandwidthTextBox.tag_add("boldcentered", "1.0", END)
		self.BandwidthTextBox.tag_configure("boldcentered",justify='center',background='white')

	def ResetFlowPolicyBandwidth(self):
		self.BandwidthTextBox.delete(1.0,END)
		self.BandwidthTextBox.configure(bg = 'white')
		self.FlowPolicyBandwidth = ''
		self.BandwidthTextBox.configure(font=("Rouge",12,'bold italic'),fg='dark grey')
		self.BandwidthTextBox.insert('1.0','(Hit <enter/return> to set policy bandwidth)')
		self.BandwidthTextBox.tag_add("boldcentered", "1.0", END)
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
		self.PortTextBox.delete('1.0', END)
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
			self.PortTextBox.configure(bg = 'green')
			self.PortTextBox.insert(END, 'Source Ports To Add: \n')
			for x in self.ListOfSelectedBadSourcePorts:
				self.PortTextBox.insert(END, str(x) + ' ')

		except:
			pass
		try:
			self.ListOfSelectedBadDestinationPorts = self.GetBadDestinationPorts()
			self.PortTextBox.configure(bg = 'green')
			self.PortTextBox.insert(END, '\n\nDestination Ports To Add: \n')
			for y in self.ListOfSelectedBadDestinationPorts:
				self.PortTextBox.insert(END, str(y) + ' ')
		except:
			pass
		self.ListOfSourcePortsToAdd = copy.deepcopy(self.ListOfSelectedBadSourcePorts)
		self.ListOfDestinationPortsToAdd = copy.deepcopy(self.ListOfSelectedBadDestinationPorts)
		self.SourcePorts.selection_clear(0, END)
		self.DestinationPorts.selection_clear(0, END)


	def RemoveFromPolicy(self):
		self.ListOfSelectedBadSourcePorts = []
		self.ListOfSelectedBadDestinationPorts = []
		try:
			self.ListOfSelectedBadSourcePorts = self.GetBadSourcePorts()
			self.PortTextBox.configure(bg = 'green')
			self.PortTextBox.insert(END, 'Source Ports To Remove: \n')
			for x in self.ListOfSelectedBadSourcePorts:
				self.PortTextBox.insert(END, str(x) + ' ')
		except:
			pass
		try:
			self.ListOfSelectedBadDestinationPorts = self.GetBadDestinationPorts()
			self.PortTextBox.configure(bg = 'green')
			self.PortTextBox.insert(END, '\n\nDestination Ports To Remove: \n')
			for y in self.ListOfSelectedBadDestinationPorts:
				self.PortTextBox.insert(END, str(y) + ' ')
		except:
			pass
		self.ListOfSourcePortsToRemove = copy.deepcopy(self.ListOfSelectedBadSourcePorts)
		self.ListOfDestinationPortsToRemove = copy.deepcopy(self.ListOfSelectedBadDestinationPorts)
		self.SourcePorts.selection_clear(0, END)
		self.DestinationPorts.selection_clear(0, END)


	def SelectActionPopup(self,ParentWindow):
		self.popup = Toplevel(ParentWindow)
		height = ParentWindow.winfo_height()/3
		width = ParentWindow.winfo_width()/3
		self.popup.geometry("+%d+%d" % (ParentWindow.winfo_rootx()+width,ParentWindow.winfo_rooty()+height))
		self.popup.lift()
		self.popup.title("Missing A Policy Selection")
		self.TitleLabel=tk.Label(self.popup,text="\nYou Must select a flow policy!\n",font=("Rouge", 14,'bold'),justify=LEFT)
		self.TitleLabel.grid(column=0, row=1,columnspan=3, padx=30,pady=30)		
		self.close=Button(self.popup,text='OK!',command=self.popup.destroy,font=("Rouge",12,'bold'))
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
				self.DiscardPolicyTextBox.delete('1.0', END)
				self.DiscardPolicyTextBox.configure(bg = 'blue', wrap=WORD, fg = 'white',font=("Rouge", 12,'bold'))
				try:
					if self.FlowPolicyBandwidth == '' and not self.DiscardFlowPolicyBandwidth:
						self.DiscardFlowPolicyBandwidth = 0
					elif self.DiscardFlowPolicyBandwidth != 0 and not self.FlowPolicyBandwidth:
						self.FlowPolicyBandwidth = ''                      
					elif self.DiscardFlowPolicyBandwidth != self.FlowPolicyBandwidth:
						self.DiscardFlowPolicyBandwidth = self.FlowPolicyBandwidth
						self.FlowPolicyBandwidth = ''
					DiscardPolicyList.append(float(self.DiscardFlowPolicyBandwidth))
					self.DiscardPolicyTextBox.insert(END, 'Policy BW : '+str(self.DiscardFlowPolicyBandwidth)+' Mbps\n')
				except:
					pass

				DiscardPolicyList.append(self.ListOfDiscardBadSourcePorts)
				DiscardPolicyList.append(self.ListOfDiscardBadDestinationPorts)
				for entry in DiscardPolicyList:
					UpdatePolicyQueue.put(entry)
				self.DiscardPolicyTextBox.insert(END, '\nSource Ports:    ')
				for y in self.ListOfDiscardBadSourcePorts:
					self.DiscardPolicyTextBox.insert(END, str(y) + ', ')
				self.DiscardPolicyTextBox.insert(END, '\n\nDestination Ports:    ')
				for y in self.ListOfDiscardBadDestinationPorts:
					self.DiscardPolicyTextBox.insert(END, str(y) + ', ')
					
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
				self.RedirectNHPolicyTextBox.delete('1.0', END)
				self.RedirectNHPolicyTextBox.configure(bg = 'blue', wrap=WORD, fg = 'white',font=("Rouge", 12,'bold'))
				try:
					if self.FlowPolicyBandwidth == '' and not self.RedirectNHFlowPolicyBandwidth:
						self.RedirectNHFlowPolicyBandwidth = 0
					elif self.RedirectNHFlowPolicyBandwidth != 0 and not self.FlowPolicyBandwidth:
						self.FlowPolicyBandwidth = ''    
					elif self.RedirectNHFlowPolicyBandwidth != self.FlowPolicyBandwidth:
						self.RedirectNHFlowPolicyBandwidth = self.FlowPolicyBandwidth
						self.FlowPolicyBandwidth = ''
					RedirectNHPolicyList.append(float(self.RedirectNHFlowPolicyBandwidth))
					self.RedirectNHPolicyTextBox.insert(END, 'Policy BW : '+str(self.RedirectNHFlowPolicyBandwidth)+' Mbps\n')
				except:
					pass
				RedirectNHPolicyList.append(self.ListOfRedirectNHBadSourcePorts)
				RedirectNHPolicyList.append(self.ListOfRedirectNHBadDestinationPorts)
				for entry in RedirectNHPolicyList:
					UpdatePolicyQueue.put(entry)
				self.RedirectNHPolicyTextBox.insert(END, '\nSource Ports:    ')
				for y in self.ListOfRedirectNHBadSourcePorts:
					self.RedirectNHPolicyTextBox.insert(END, str(y) + ', ')
				self.RedirectNHPolicyTextBox.insert(END, '\n\nDestination Ports:    ')
				for y in self.ListOfRedirectNHBadDestinationPorts:
					self.RedirectNHPolicyTextBox.insert(END, str(y) + ', ')
					
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
				self.RedirectVRFPolicyTextBox.delete('1.0', END)
				self.RedirectVRFPolicyTextBox.configure(bg = 'blue', wrap=WORD, fg = 'white',font=("Rouge", 12,'bold'))
				try:
					if self.FlowPolicyBandwidth == '' and not self.RedirectVRFFlowPolicyBandwidth:
					   self.RedirectVRFFlowPolicyBandwidth = 0
					elif self.RedirectVRFFlowPolicyBandwidth != 0 and not self.FlowPolicyBandwidth:
						self.FlowPolicyBandwidth = ''    
					elif self.RedirectVRFFlowPolicyBandwidth != self.FlowPolicyBandwidth:
						self.RedirectVRFFlowPolicyBandwidth = self.FlowPolicyBandwidth
						self.FlowPolicyBandwidth = ''
					RedirectVRFPolicyList.append(float(self.RedirectVRFFlowPolicyBandwidth))
					self.RedirectVRFPolicyTextBox.insert(END, 'Policy BW : '+str(self.RedirectVRFFlowPolicyBandwidth)+'\n')
				except:
					pass
				RedirectVRFPolicyList.append(self.ListOfRedirectVRFBadSourcePorts)
				RedirectVRFPolicyList.append(self.ListOfRedirectVRFBadDestinationPorts)
				for entry in RedirectVRFPolicyList:
					UpdatePolicyQueue.put(entry)
				self.RedirectVRFPolicyTextBox.insert(END, '\nSource Ports:    ')
				for y in self.ListOfRedirectVRFBadSourcePorts:
					self.RedirectVRFPolicyTextBox.insert(END, str(y) + ', ')
				self.RedirectVRFPolicyTextBox.insert(END, '\n\nDestination Ports:    ')
				for y in self.ListOfRedirectVRFBadDestinationPorts:
					self.RedirectVRFPolicyTextBox.insert(END, str(y) + ', ')     
		except:
			pass
		self.PortTextBox.delete(1.0,END)
		self.PortTextBox.configure(bg = 'white')
		self.ResetFlowPolicyBandwidth()
		self.ResetFlowPolicyAction()	

	def ClearPolicySelection(self):
		self.PortTextBox.delete(1.0,END)
		self.PortTextBox.configure(bg = 'white')
		self.ResetFlowPolicyBandwidth()
		self.ResetFlowPolicyAction()
		
	def ClearDiscardPolicy(self):
		self.DiscardPolicyClear = ['discard', 0, [], []]
		self.DiscardPolicyTextBox.delete(1.0,END)
		self.DiscardPolicyTextBox.configure(bg = 'white')
		self.ListOfDiscardBadSourcePorts = []
		self.ListOfDiscardBadDestinationPorts = []
		self.DiscardFlowPolicyBandwidth = ''
		for entry in self.DiscardPolicyClear:
			UpdatePolicyQueue.put(entry)
	
	def ClearRedirectNHPolicy(self):
		self.RedirectNHPolicyClear = ['redirect next-hop', 0, [], []]
		self.RedirectNHPolicyTextBox.delete(1.0,END)
		self.RedirectNHPolicyTextBox.configure(bg = 'white')
		self.ListOfRedirectNHBadSourcePorts = []
		self.ListOfRedirectNHBadDestinationPorts = []
		self.RedirectNHFlowPolicyBandwidth = ''
		for entry in self.RedirectNHPolicyClear:
			UpdatePolicyQueue.put(entry)
	
	def ClearRedirectVRFPolicy(self):
		self.RedirectVRFPolicyClear = ['redirect VRF', 0, [], []]
		self.RedirectVRFPolicyTextBox.delete(1.0,END)
		self.RedirectVRFPolicyTextBox.configure(bg = 'white')
		self.ListOfRedirectVRFBadSourcePorts = []
		self.ListOfRedirectVRFBadDestinationPorts = []
		self.RedirectVRFFlowPolicyBandwidth = ''
		for entry in self.RedirectVRFPolicyClear:
			UpdatePolicyQueue.put(entry)
	
	def remove_duplicates(self,l):
		return list(set(l))

	def RestartPolicyManager(self):
		SignalResetQueue.put('RESET SIGNALLED')
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
				r=requests.put('http://%s:8008/flow/%s/json' % (sflowIP,'interface'),data=json.dumps(intflow))
				r=requests.put('http://%s:8008/flow/%s/json' % (sflowIP,'ipdest'),data=json.dumps(ipflow))
				False
				print ("\n\nDone! ........\n\n\n")
				print ("\n\nFlowspec Controller Running! ........\n\n\n")
				return
			except:
				pass



if __name__ == '__main__':
	

	ProgramSflowrt()
	
	
	# Queue which will be used for storing Datalines (Flow data from sflow-rt)
	
	SflowQueue = JoinableQueue(maxsize=0)  
	SflowQueue.cancel_join_thread()
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
	gui = FlowspecGUI(SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,UpdatePolicyQueue,SignalResetQueue)
	t1 = Process(target=FindAndProgramDdosFlows,args=(SflowQueue,FlowRouteQueueForQuit,FlowRouteQueue,ManualRouteQueue,UpdatePolicyQueue,SignalResetQueue))
	t1.start()
	gui.window.mainloop()
	t1.join()
