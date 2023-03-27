import requests
from flask import request, Blueprint, jsonify
from backend.node import Node
from backend.block import Block, dictToBlock
from threading import Event, Thread
from time import sleep


def chooseConflictResolutionListenConstructor(myNode: Node):
    chooseConflictResolution = Blueprint('chooseConflictResolution', __name__)

    @chooseConflictResolution.route('/', methods=['PUT', 'GET'])
    def chooseConflictResolutionActions():
        if request.method == 'PUT':

            payload = request.get_json()
            senderLastBlockHash = payload["lastBlockHash"]
            senderInvalidCount = payload["numOfInvalidBlocks"]
            isValid = False
            countBlocks = 0
            for iBlock in reversed(myNode.chain.listOfBlocks):
                if senderLastBlockHash == iBlock.getHash():
                    isValid = True
                    break
                countBlocks += 1
            if isValid:
                blocksToSend = myNode.chain.getlistOfDictBlocks(count=countBlocks)
                response = {"isBlockValid": isValid, "blocksToAdd": blocksToSend}
            else:
                response = {"isBlockValid": isValid, "blocksToAdd": []}

            return response, 200
        if request.method == 'GET':
            myNode.createListenerChoiceThread()
            return {}, 200

    return chooseConflictResolution
