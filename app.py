#!/usr/bin/env python

from flask import Flask, request
from sys import stdout

import sys
from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)

 
app = Flask(__name__)
 
# Setup a command route to listen for prefix advertisements

@app.route('/', methods=['POST'])
def command():
	command = request.form['command']
	stdout.write('%s\n' % command)
	stdout.flush()
	return '%s\n' % command	


if __name__ == '__main__':
	app.run(
	host='0.0.0.0',
	port=5000,
	debug=True,
	use_reloader=False,
	)

