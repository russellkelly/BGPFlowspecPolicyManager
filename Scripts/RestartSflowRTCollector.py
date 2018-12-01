#!/usr/bin/env python

import os
import sys
from time import sleep
path = "/home/flowspec/sflow-rt"

def main():
	os.chdir( path )
	data = {"user": "flowspec",
		"host": "localhost",
		"password": "flowspec",
		"commands": "cd /home/demo/sflow-rt;  screen -dm bash start.sh"}
	command = "sshpass -p {password} ssh -o StrictHostKeyChecking=no {user}@{host} {commands}"
	os.system(command.format(**data))
	print ("\n\nStarting Sflow Collector ........\n\n\n")
	print ("\n\nDone! ........\n\n\n")
	exit(0)

if __name__ == "__main__":
	main()
