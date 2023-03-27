import requests
from flask import request, Blueprint
from backend.node import Node
from backend.block import Block, dictToBlock
from threading import Event, Thread


def broadcastBlockListenConstructor(myNode: Node):
    broadcastBlock = Blueprint('broadcastBlock', __name__)

    @broadcastBlock.route('/', methods=['PUT'])
    def broadcastBlockActions():
        response = {"nodeId"  : myNode.Id, "lastHashAfterInsertion": myNode.chain.getLastBlock().getHash(),
                    "conflict": False}

        payload = request.get_json()

        newBlock = dictToBlock(payload)
        isValid, code = myNode.validate_block(newBlock)
        if isValid:
            fixMiningBlockFlag = False
            myAcquiredTransactions = myNode.acquiredTransactions.copy().keys()
            for id in newBlock.listOfTransactions.keys():
                if id not in myAcquiredTransactions:
                    print("aaaa")
                    continue
                iTransactionBlock = myNode.acquiredTransactions[id]['block']
                # if the transactions are in a block that is being mined, stop mining
                if myNode.acquiredTransactions[id]['isBeingMined']:
                    fixMiningBlockFlag = True
                    myNode.miningStopEvent.set()
                # delete the transaction from my acquired transactions
                try:
                    del myNode.acquiredTransactions[id]
                except:
                    pass
                del iTransactionBlock.listOfTransactions[id]

        else:
            if code == 'conflict':
                response.update({code: True})
                print('calling resolve')
                myNode.createResolveThread()
            else:
                response.update({'otherError': True})
            return response, 200

        myNode.chainLock.acquire()
        myNode.chain.addBlock(newBlock)
        myNode.chainLock.release()

        print("apexw to vala")

        print('\n-----------------valid-----------------\n', newBlock.getHash())

        return response, 200

    return broadcastBlock
