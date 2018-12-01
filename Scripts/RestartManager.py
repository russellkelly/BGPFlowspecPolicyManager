#!/usr/bin/env python

import os
import sys
from time import sleep
path = "/home/flowspec/ConfigFiles"

def main():
	os.chdir( path )
	data = {"user": "flowspec",
		"host": "localhost",
		"password": "flowspec",
		"commands": "sudo pkill -9 exabgp ; sudo pkill -9 screen ; screen -wipe ; screen -dm exabgp exabgp.conf --debug "}
	command = "sshpass -p {password} ssh -o StrictHostKeyChecking=no {user}@{host} {commands}"
	os.system(command.format(**data))
	exit(0)

if __name__ == "__main__":
	main()
	os.system("sudo pkill -9 python")
