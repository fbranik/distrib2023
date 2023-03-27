import requests
from flask import request, Blueprint
from backend.node import Node
from backend.block import Block, dictToBlock
from threading import Event, Thread


def resolveConflictConstructor(myNode: Node):
    resolveConflict = Blueprint('resolveConflict', __name__)

    @resolveConflict.route('/', methods=['PUT'])
    def resolveConflictActions():
        # if I already know there is a conflict check my role in it
        if myNode.conflictActive:
            # if i am in the next phase or im a broadcater return
            if myNode.Choosing or myNode.conflictRole:
                response = {}
                return response, 200
            else:
                # im a listener, gather the chain sizes from the request payload
                myNode.nodeCount = len(myNode.nodesTable)
                payload = request.get_json()
                myNode.conflictedChainSizes.update(payload)
                # update my conflicted chain sizes and send it to the broadcaster in the response
                response = myNode.conflictedChainSizes
                if len(myNode.conflictedChainSizes) == myNode.nodeCount and not myNode.Choosing:
                    print("oxi prwti")
                    myNode.createListenerConflictThread()
                return response, 200
        # if i dont know there is a conflict, begin with listener conflict role
        else:
            payload = request.get_json()
            # update my conflicts table with my data and the data i got
            myNode.conflictedChainSizes[str(myNode.Id)] = len(myNode.chain.listOfBlocks)
            myNode.conflictedChainSizes.update(payload)
            # include in response
            response = myNode.conflictedChainSizes
            # run thread with resolve conflict as a listener
            myNode.createListenerConflictThread()

            return response, 200

    # print(myNode.chain.getLastBlock().previousHash, myNode.chain.getLastBlock().getHash())

    return resolveConflict
