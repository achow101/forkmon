from django.core.management.base import BaseCommand, CommandError

import requests
import os
import datetime

from .models import *

def update_nodes():

    # update in-db chain for each node
    nodes = Node.objects.all()
    print("Beginning update at " + str(datetime.datetime.now()))
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

            # check that this node's current top block is this block or the previous block
            blocks = Block.objects.all().filter(node=node, active=True).order_by("-height")

            # same block
            if blocks[0].hash == hash:
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
                while blocks[i].height > height:
                    # deactivate the block here
                    blocks[i].active = False
                    blocks[i].save()

                    # increment
                    i += 1
                # now DB and node are at same height, walk backwards through both to find common ancestor
                deactivated = 0
                while blocks[i].hash != hash:
                    # deactivate the block here
                    blocks[i].active = False
                    blocks[i].save()
                    deactivated += 1

                    # increment
                    i += 1

                    # get block from node
                    r = requests.post(url, data='{"method": "getblockheader", "params": ["' + prev + '"] }',
                              auth=(os.environ['RPC_USER'], os.environ['RPC_PASSWORD']))
                    if r.status_code != 200:
                        continue
                    rj = r.json()
                    header = rj['result']
                    prev = header['previousblockhash']
                    hash = header['hash']
                    blocks_to_add.append(hash)

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

            # mark as up and save
            node.is_up = True
            node.save()
        except:
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

        # skip if there is no blockchain for some reason
        if blockchain.count() == 0:
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

            # skip if there is no blockchain for some reason
            if cmp_blockchain == 0:
                continue

            # get these to matching heights
            while cmp_blockchain[cmp_it].height > blockchain[it].height and diverged <= 6:
                cmp_it += 1
                diverged += 1
            while blockchain[it].height > cmp_blockchain[cmp_it].height and diverged <= 6:
                it += 1
                diverged += 1

            # walk down both chains until common ancestor found
            while blockchain[it].hash != cmp_blockchain[cmp_it].hash and diverged <= 6:
                cmp_it += 1
                it += 1
                diverged += 1

            # updated diverged block if within the last 6
            if it > 0 and cmp_it > 0 and blockchain[it].hash == cmp_blockchain[cmp_it].hash and blockchain[it - 1].hash != cmp_blockchain[cmp_it - 1].hash:
                if blockchain[it - 1].height > node.highest_divergence and diverged > 1:
                    node.highest_divergence = blockchain[it - 1].height
                    node.highest_diverged_hash = blockchain[it - 1].hash
                    node.save()

            # split detected, mark as such
            if diverged > 1:
                if it - 1 < 0:
                    node.is_behind = True
                else:
                    node.is_behind = False

                if not node.is_up:
                    no_split = True
                    has_split = has_split or False
                else:
                    has_split = True
                    no_split = False
                node.save()

    # Update fork state if split detected
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

    print("Updated Completed at " + str(datetime.datetime.now()))