import logging

from django.utils import timezone
from django.utils.crypto import get_random_string

import requests
import os
import datetime

from .models import *

logger = logging.getLogger("forkmon.task")

def update_nodes():
    update_id = get_random_string(length=10)
    logger.info("Update ID: " + update_id + " - Beginning update at " + str(datetime.datetime.now()))

    # Retrieve the database lock
    lock = UpdateLock.objects.all().first()
    lock_version = lock.version

    # Check that the lock is currently not in use
    if lock.in_use:
        logger.info("Update ID: " + update_id + " - Database in use, exiting at " + str(datetime.datetime.now()))
        return

    # Update the lock
    locked = UpdateLock.objects.filter(version=lock_version).update(in_use = True, version=lock_version + 1)

    # exit if 0 objects were updated as that means someone was locking at the same time
    if locked == 0:
        logger.info("Update ID: " + update_id + " - Database lock version was updated by another process, exiting at " + str(datetime.datetime.now()))
        return

    # update in-db chain for each node
    nodes = Node.objects.all()
    for node in nodes:
        # try except statements for catching any errors that come from the requests. if there is an error, just skip
        # the node and continue
        try:
            url = node.url

            # get best block hash
            r = requests.post(url, data='{"method": "getbestblockhash", "params": [] }',
                              auth=(os.environ['RPC_USER'], os.environ['RPC_PASSWORD']))
            if r.status_code != 200:
                continue
            rj = r.json()
            best_block = rj['result']

            # Get the block header for best block hash
            r = requests.post(url, data='{"method": "getblockheader", "params": ["'+ best_block + '"] }',
                              auth=(os.environ['RPC_USER'], os.environ['RPC_PASSWORD']))
            if r.status_code != 200:
                continue
            rj = r.json()
            header = rj['result']
            prev = header['previousblockhash']
            height = header['height']
            hash = header['hash']

            # Update node's MTP
            node.mtp = datetime.datetime.fromtimestamp(header['mediantime'], timezone.utc)

            # check that this node's current top block is this block or the previous block
            blocks = Block.objects.all().filter(node=node, active=True).order_by("-height")

            # If there is no blockchain, add the first block
            if not blocks:
                Block(hash=hash, height=height, node=node).save()
                node.best_block_hash = hash
                node.best_block_height = height
                node.prev_block_hash = prev

            # same block
            elif blocks[0].hash == hash:
                node.best_block_hash = hash
                node.best_block_height = height
                node.prev_block_hash = prev
            # different block
            # next block: prev hash matches
            elif prev == blocks[0].hash:
                # Add block to db
                Block(hash=hash, height=height, prev=blocks[0], node=node).save()
                node.best_block_hash = hash
                node.best_block_height = height
                node.prev_block_hash = prev
            # otherwise need to reorg
            else:
                # node's height is ahead
                blocks_to_add = [hash]
                i = 0
                # walk backwards until node height matches db height
                while height > blocks[i].height:
                    r = requests.post(url, data='{"method": "getblockheader", "params": ["' + prev + '"] }',
                              auth=(os.environ['RPC_USER'], os.environ['RPC_PASSWORD']))
                    if r.status_code != 200:
                        continue
                    rj = r.json()
                    header = rj['result']
                    prev = header['previousblockhash']
                    hash = header['hash']
                    height = header['height']
                    if height > blocks[i].height:
                        blocks_to_add.append(hash)
                # walk down db chain until node height matches
                deactivated = 0
                while blocks[i].height > height:
                    # deactivate the block here
                    block = blocks[i]
                    block.active = False
                    block.save()
                    deactivated += 1

                    # increment
                    i += 1
                # now DB and node are at same height, walk backwards through both to find common ancestor
                while blocks[i].hash != hash:
                    # deactivate the block here
                    block = blocks[i]
                    block.active = False
                    block.save()
                    deactivated += 1

                    # increment
                    i += 1

                    # Add this hash to add
                    blocks_to_add.append(hash)

                    # get block from node
                    r = requests.post(url, data='{"method": "getblockheader", "params": ["' + prev + '"] }',
                              auth=(os.environ['RPC_USER'], os.environ['RPC_PASSWORD']))
                    if r.status_code != 200:
                        continue
                    rj = r.json()
                    header = rj['result']
                    prev = header['previousblockhash']
                    hash = header['hash']

                # at common ancestor
                # now add new blocks
                prev_block = blocks[i]
                for hash in blocks_to_add[::-1]:
                    block = Block(hash=hash, height=prev_block.height+1, node=node, active=True, prev=prev_block)
                    block.save()
                    node.best_block_hash = block.hash
                    node.best_block_height = block.height
                    node.prev_block_hash = prev_block.hash
                    prev_block = block

                # update node's tip and if it has reorged
                node.has_reorged = node.has_reorged or deactivated > 2 # only reorged if reorg was greater than 2 blocks

            # Gather stats from stats node
            if node.stats_node:
                r = requests.post(url, data='{"method": "getblockchaininfo", "params": [] }',
                                  auth=(os.environ['RPC_USER'], os.environ['RPC_PASSWORD']))
                if r.status_code != 200:
                    continue
                rj = r.json()
                forks = rj['result']['bip9_softforks']
                current = rj['result']['blocks']
                for name, info in forks.items():
                    # Get status
                    state = info['status']

                    # Get the fork from the database
                    db_forks = BIP9Fork.objects.all().filter(name=name)

                    # skip if state is active or defined and was not already in the db
                    if (state == "active" or state == 'defined') and not db_forks:
                        continue

                    # Only get stats if started
                    if state == 'started':
                        # Get statistics
                        period = info['statistics']['period']
                        threshold = info['statistics']['threshold']
                        elapsed = info['statistics']['elapsed']
                        count = info['statistics']['count']

                        # If the fork does not exist, make it
                        if not db_forks:
                            BIP9Fork(name=name, state=state, period=period, threshold=threshold, elapsed=elapsed, count=count).save()
                        # otherwise update it
                        else:
                            fork = db_forks[0]
                            fork.elapsed = elapsed
                            fork.count = count
                            fork.state = state
                            fork.current = current
                            fork.since = info['since']
                            fork.save()
                    else:
                        fork = db_forks[0]
                        fork.state = state
                        fork.since = info['since']
                        fork.current = current
                        fork.save()


            # mark as up and save
            node.is_up = True
            node.save()
        except Exception as e:
            print(e)
            # mark that node is currently down
            node.is_up = False
            node.save()
            continue

    # now that nodes are updated, check for chain splits
    nodes = Node.objects.all()
    has_split = False
    no_split = True
    for node in nodes:
        blockchain = Block.objects.all().filter(node=node, active=True).order_by("-height")

        # skip if there is no blockchain for some reason or the node is down
        if not blockchain or not node.is_up:
            continue

        for cmp_node in nodes:
            # don't compare to self
            if node == cmp_node:
                continue

            # check top block is same
            if node.best_block_hash == cmp_node.best_block_hash:
                node.is_behind = False
                continue

            # top block hashes are not the same. find if the divergence is within the past 6 blocks
            # once the block is found, it will be saved until a new divergence is found
            cmp_it = 0
            it = 0
            diverged = 0
            cmp_blockchain = Block.objects.all().filter(node=cmp_node, active=True).order_by("-height")

            # skip if there is no blockchain for some reason or if the node is down
            if not cmp_blockchain or not cmp_node.is_up:
                continue

            # If the two nodes have mtp forks, skip their comparison
            if cmp_node.mtp_fork and node.mtp_fork and cmp_node.mtp > cmp_node.mtp_fork.activation_time and node.mtp > node.mtp_fork.activation_time:
                continue

            no_split = False

            # get these to matching heights
            while cmp_blockchain[cmp_it].height > blockchain[it].height and diverged <= 6:
                cmp_it += 1
                diverged += 1
            while blockchain[it].height > cmp_blockchain[cmp_it].height and diverged <= 6:
                it += 1
                diverged += 1

            # walk down both chains until common ancestor found
            while blockchain[it].hash != cmp_blockchain[cmp_it].hash and diverged <= 15:
                cmp_it += 1
                it += 1
                diverged += 1

            # updated diverged block if within the last 6
            if it > 0 and cmp_it > 0 and blockchain[it].hash == cmp_blockchain[cmp_it].hash and blockchain[it - 1].hash != cmp_blockchain[cmp_it - 1].hash:
                if blockchain[it - 1].height > node.highest_divergence and diverged > 1:
                    node.highest_divergence = blockchain[it - 1].height
                    node.highest_diverged_hash = blockchain[it - 1].hash
                    node.save()

            # For MTP forks. Mark MTP forks as no_split
            if diverged > 0:
                # Only mark node has having MTP forked if node's mtp is past the mtp fork time
                if node.mtp_fork and node.mtp > node.mtp_fork.activation_time:
                    no_split = True
                    node.sched_forked = True
                    node.save()
                    continue
                # If the cmp_node had an mtp fork, ignore this divergence.
                elif cmp_node.mtp_fork and cmp_node.mtp > cmp_node.mtp_fork.activation_time:
                    no_split = True
                    continue
            # Normal split detected, mark as such
            if diverged > 1:
                has_split = True
                if it - 1 < 0:
                    node.is_behind = True
                else:
                    node.is_behind = False
                node.save()

    # Update fork state if split detected
    states = ForkState.objects.all()
    if not states:
        ForkState().save()
    if has_split:
        state = ForkState.objects.all()[0]
        state.has_forked = True
        state.is_currently_forked = True
        state.save()
    if no_split:
        state = ForkState.objects.all()[0]
        state.is_currently_forked = False
        state.save()

        # reset node stuff
        for node in nodes:
            node.highest_divergence = 0
            node.save()

    # release database lock
    UpdateLock.objects.filter(version=lock_version + 1).update(in_use = False, version=lock_version + 2)

    logger.info("Update ID: " + update_id + " - Completed at " + str(datetime.datetime.now()))
