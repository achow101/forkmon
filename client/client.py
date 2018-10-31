#! /usr/bin/env python3

import argparse
import http.server
import threading
import queue
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

parser = argparse.ArgumentParser(description='Daemon that waits for block notifications and sends updates to the server')
parser.add_argument('rpcuser', help='rpcuser for the running bitcoind')
parser.add_argument('rpcpassword', help='rpcpassword for the running bitcoind')
parser.add_argument('--port', '-p', type=int, help='Port to run on', default=8000)
args = parser.parse_args()

blocks_queue = queue.Queue()

class NewBlockHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        blockhash = self.rfile.read(int(self.headers['Content-Length']))

        # Basic sanity check
        if len(blockhash) != 64:
            self.send_response(400)
            self.send_header('Content-type', 'text/text')
            self.end_headers()
            self.wfile.write(b'bad block hash')
            return

        # Insert into queue
        blocks_queue.put(blockhash)

        # Respond that everything is ok
        self.send_response(200)
        self.send_header('Content-type', 'text/text')
        self.end_headers()
        self.wfile.write(b'queued block hash for processing')

# Setup RPC
rpc = AuthServiceProxy('http://{}:{}@127.0.0.1:8332'.format(args.rpcuser, args.rpcpassword))
rpc.getblockchaininfo() # make sure rpc is working

# Start http server
httpd = http.server.HTTPServer(('', args.port), NewBlockHandler)
httpd_thread = threading.Thread(target=httpd.serve_forever)

# Process blocks
while True:
    blockhash = blocks_queue.get()
    block = rpc.getblock(blockhash)
