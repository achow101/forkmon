#! /usr/bin/env python3

# This is called by blocknotify when a new block is received

import argparse
import requests

parser = argparse.ArgumentParser(description='Notify the client daemon of the new block')
parser.add_argument('blockhash', help='The hash of the block that has been received')
args = parser.parse_args()

# Post block to client daemon
r = requests.post('http://127.0.0.1:8000', data=args.blockhash)
