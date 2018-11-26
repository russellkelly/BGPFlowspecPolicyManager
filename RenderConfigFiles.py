#!/usr/bin/env python

import os
import signal
from requests import get
import json
import sys
import traceback
import yaml
from jinja2 import Template
from sys import stdout


def exit_gracefully(signum, frame):
	# restore the original signal handler as otherwise evil things will happen
	# in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
	signal.signal(signal.SIGINT, original_sigint)
	main()
	# restore the exit gracefully handler here    
	signal.signal(signal.SIGINT, exit_gracefully)
	
	

def FlowspecManagerPublicIP():
	ip = get('https://api.ipify.org').text
	return ip


def RenderRouterConfiguration():
	script_dir = os.path.dirname(__file__)
	rel_path = "TopologyVariables.yaml"
	abs_file_path = os.path.join(script_dir, rel_path)
	file=open(abs_file_path)
	EdgeRouterVars = yaml.load(file.read())
	EdgeRouterVars['home_directory'] = os.path.dirname(os.path.realpath(__file__))
	EdgeRouterVars['FlowspecManagerPublicIP'] = FlowspecManagerPublicIP()
	file.close()
	template_open = open("JinjaTemplates/EdgeRouterConfigs.j2")
	ingress_template = Template(template_open.read())
	template_output = ingress_template.render(EdgeRouterVars)
	script_dir = os.path.dirname(__file__)
	rel_path = "ConfigFiles/EdgeRouterConfigs.cfg"
	abs_file_path = os.path.join(script_dir, rel_path)
	with open(abs_file_path, "wb") as f:
		f.write(template_output)
	f.close()
	template_open = open("JinjaTemplates/ExabgpFlowConf.j2")
	ingress_template = Template(template_open.read())
	template_output = ingress_template.render(EdgeRouterVars)
	script_dir = os.path.dirname(__file__)
	rel_path = "ConfigFiles/exabgp.conf"
	abs_file_path = os.path.join(script_dir, rel_path)
	with open(abs_file_path, "wb") as f:
		f.write(template_output)
	f.close()




if __name__ == "__main__":
	# store the original SIGINT handler
	original_sigint = signal.getsignal(signal.SIGINT)
	signal.signal(signal.SIGINT, exit_gracefully)
	RenderRouterConfiguration()

