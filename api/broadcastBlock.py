import requests
from flask import request, Blueprint
from backend.node import Node
from backend.block import Block, dictToBlock
from threading import Event, Thread


def broadcastBlockConstructor(myNode: Node):
    broadcastBlock = Blueprint('broadcastBlock', __name__)

    @broadcastBlock.route('/', methods=['PUT'])
    def broadcastBlockActions():
        response = {"nodeId": myNode.Id, "lastHashAfterInsertion": myNode.chain.getLastBlock().getHash(),
                    "conflict": False}

        payload = request.get_json()

        newBlock = dictToBlock(payload)
        isValid, code = myNode.validate_block(newBlock)
        if isValid:
            myAcquiredTransactions = myNode.acquiredTansactions.copy().keys()
            if any(id in newBlock.listOfTransactions for id in myAcquiredTransactions):
                for id in myAcquiredTransactions:
                    iTransactionBlock = myNode.acquiredTansactions[id]
                    if id in newBlock.listOfTransactions:
                        # delete the transaction from my acquired transactions
                        try:
                            del myNode.acquiredTansactions[id]
                        except:
                            pass
                        if iTransactionBlock.timestamp in myNode.miningStopEvents.keys():
                            # if the transaction is included in the new block 
                            # and i have included the transaction in a block that's
                            # being mined, cancel the mining
                            myNode.miningStopEvents[iTransactionBlock.timestamp].set()
                            try:
                                del myNode.miningStopEvents[iTransactionBlock.timestamp]
                            except:
                                pass
                        else:
                            # delete the transaction from the block that it was found in 
                            try:
                                del iTransactionBlock.listOfTransactions[id]
                            except:
                                pass
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
