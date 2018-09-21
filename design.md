# Design

This documents the design of the fork monitoring system

## Server

The server serves the website and waits for updates from nodes.

The server loads from the database a list of node names and their public keys. When a new node connects, it provides it's pubkey and this is used to derive a shared secret for encryption. It also serves to authenticate the node.

When a node provides an updated block, the server updates it's database entry for that node's best block hash and current chainwork. If the best block hashes of the other nodes are the same as the previous best block hash, that hash is stored as the most recent common block for that node with the specific other node.

If there is a reorg, the reorg info is stored and the best block hash and chainwork is reset to the reorg fork point. The tip is updated as usual.

When a node's state is updated, a lock is held so that only one node can be updated at a time. For the threads that are waiting, a per-node bool is set indicating that new data is about to be written. Lastly a per-node boolean is set to indicate that the polling thread has not read through the data yet.

A polling thread is run every minute to check whether the nodes have diverged. It first obtains the global lock. If any thread is about to write data, it unlocks and waits for later. If the polling bool is false (i.e. poller hasn't been here yet), it sets it to true but does not do any comparisons. Once all polling bools are true, and no thread has data to write, then all nodes are stable in their states. At this point the poller checks whether they all have the same tips and chainwork. If both chainwork and chaintips are different, warn that a fork has occurred.

## Nodes

Nodes must have a direct connection to every other node and be whitelisting them.

Individual nodes run a Bitcoin daemon and a fork monitor daemon. The bitcoind has `blocknotify` set so it will call a fork monitor client script on every new block. The fork monitor daemon must be started first.

When the fork monitor daemon starts, it spawns a client script listening thread. The main thread waits for the RPC interface to be available and for the node to exit IBD. It then sends to the server that it has started and the current best block hash. Then it waits for something to be in the queue to start processing data.

The fork monitor client script checks for the existence of a lock file. If it is not there, it creates it. The client script then sends to the fork monitor daemon the block hash, deletes the lock file, and exits.

The fork monitor daemon receives block hashes from client scripts and adds them to a queue. For every block hash in the queue, it retrieves the block data from the bitcoind. It compares the best block hash stored locally and checks if the previous block was the best block hash. If so, it updates it's local best block hash and sends to the server a best block hash update.

If the best block hash does not match the previous block, it finds which blocks were reorged out and sends to the server the list of blocks that were reorged out, along with the common parent. It then sends the best block hash update.
