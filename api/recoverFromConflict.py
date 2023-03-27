import requests
from flask import request, Blueprint, jsonify
from backend.node import Node
from backend.block import Block, dictToBlock
from threading import Event, Thread
from time import sleep


def recoverFromConflictConstructor(myNode: Node):
    recoverFromConflict = Blueprint('recoverFromConflict', __name__)

    @recoverFromConflict.route('/', methods=['PUT'])
    def recoverFromConflictActions():
        print("phra recover")
        payload = request.get_json()
        myChainChosen = payload['myChainChosen']
        response = {}
        myNode.recoverFromConflict(myChainChosen)

        return response, 200

    return recoverFromConflict
