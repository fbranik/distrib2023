import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import urllib.request
import json
from os.path import dirname, realpath
from sys import path
import atexit

thisFilePath = dirname(realpath(__file__))
noobcashPath = dirname(thisFilePath)
path.append(noobcashPath)

from api.createNewTransactionListen import createNewTransactionListenConstructor
from api.syncNodesTableListen import syncNodesTableListenConstructor
from api.newNodeAddedListen import newNodeAddedListenConstructor
from api.broadcastTransactionListen import broadcastTransactionListenConstructor
from api.broadcastBlockListen import broadcastBlockListenConstructor
from api.getBalanceListen import getBalanceListenConstructor
from api.viewTransactionsListen import viewTransactionsListenConstructor
from api.runTestsListen import runTestsListenConstructor
from api.getChainListen import getChainListenConstructor
from api.getChainLengthListen import getChainLengthListenConstructor
from backend.transaction import Transaction, dictToTransaction
from backend.wallet import Wallet
from backend.blockchain import Blockchain
from backend.node import Node
from backend.block import Block, dictToBlock
from api.resolveConflictListen import resolveConflictListenConstructor
from api.chooseConflictResolutionListen import chooseConflictResolutionListenConstructor
from api.recoverFromConflictListen import recoverFromConflictListenConstructor
import logging
from os.path import exists
from os import remove as removeFile

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.disabled = True
CORS(app)

bootstrapPort = '5000'


# get all transactions in the blockchain

@app.route('/transactions/get', methods=['GET'])
def get_transactions():
    transactions = blockchain.transactions

    response = {'transactions': transactions}
    return jsonify(response), 200


@app.route('/api/writeBlockLogs', methods=["GET"])
def writeBlockLogs():
    if exists(f'logs/block{myNode.Id}_{myNode.chain.sizeOfBlock}_{myNode.difficulty}.txt'):
        removeFile(f'logs/block{myNode.Id}_{myNode.chain.sizeOfBlock}_{myNode.difficulty}.txt')

    block_log = open(f'logs/block{myNode.Id}_{myNode.chain.sizeOfBlock}_{myNode.difficulty}.txt', 'a')
    for iBlock in myNode.chain.listOfBlocks:
        block_log.write(f'{iBlock.addedToChainTimestamp - iBlock.timestamp}\n')
    block_log.close()
    return 'writing block logs', 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000,
                        type=int, help='port to listen on')
    parser.add_argument('-a', '--ipAddress', default='127.0.0.1',
                        type=str, help='ip address to be used')
    parser.add_argument('-b', '--bootstrapAdress', default='', type=str,
                        help='ip of Bootstrap Node')
    parser.add_argument('-n', '--numberOfNodes', default=5, type=int,
                        help='Number of Nodes that will participate')
    parser.add_argument('-d', '--miningDifficulty', default=5, type=int,
                        help='Number of of leading 0s in a valid Block hash')
    parser.add_argument('-c', '--blockSize', default=5, type=int,
                        help='Transactions per Block')

    args = parser.parse_args()
    myPort = args.port
    myIp = args.ipAddress
    bootstrapAdress = args.bootstrapAdress
    isBootstrap = False
    if bootstrapAdress == '':
        bootstrapAdress = myIp
        isBootstrap = True
    numberOfNodes = args.numberOfNodes
    difficulty = args.miningDifficulty
    blockSize = args.blockSize

    blockchain = Blockchain(blockSize)
    myNode = Node(blockchain=blockchain, isBootstrap=isBootstrap, difficulty=difficulty)

    newNodeAdded = newNodeAddedListenConstructor(myNode)
    app.register_blueprint(newNodeAdded, url_prefix='/api/newNodeAdded')

    syncNodesTable = syncNodesTableListenConstructor(myNode)
    app.register_blueprint(syncNodesTable, url_prefix='/api/syncNodesTable')

    createNewTransaction = createNewTransactionListenConstructor(myNode)
    app.register_blueprint(createNewTransaction,
                           url_prefix='/api/createNewTransaction')

    broadcastTransaction = broadcastTransactionListenConstructor(myNode)
    app.register_blueprint(broadcastTransaction, url_prefix='/api/broadcastTransaction')

    resolveConflict = resolveConflictListenConstructor(myNode)
    app.register_blueprint(resolveConflict, url_prefix='/api/resolveConflicts')

    chooseConflictResolution = chooseConflictResolutionListenConstructor(myNode)
    app.register_blueprint(chooseConflictResolution, url_prefix='/api/chooseConflictResolution')

    broadcastBlock = broadcastBlockListenConstructor(myNode)
    app.register_blueprint(broadcastBlock, url_prefix='/api/broadcastBlock')

    getBalance = getBalanceListenConstructor(myNode)
    app.register_blueprint(getBalance, url_prefix='/api/getBalance')

    viewTransactions = viewTransactionsListenConstructor(myNode)
    app.register_blueprint(viewTransactions, url_prefix='/api/viewTransactions')

    recoverFromConflict = recoverFromConflictListenConstructor(myNode)
    app.register_blueprint(recoverFromConflict, url_prefix='/api/runRecoverFromConflict')

    runTests = runTestsListenConstructor(myNode, myIp, myPort)
    app.register_blueprint(runTests, url_prefix='/api/runTests')

    getChain = getChainListenConstructor(myNode)
    app.register_blueprint(getChain, url_prefix='/api/getChain')

    getChainLength = getChainLengthListenConstructor(myNode)
    app.register_blueprint(getChainLength, url_prefix='/api/getChainLength')

    # Write my pulic and private key files
    myNode.writeWalletFiles('private{}.pem'.format(myPort),
                            'public{}.key'.format(myPort))

    # if this is the bootstap node, add the first entry to the table
    if isBootstrap:
        # Create the genesis block and add it to the blockchain        
        genesisBlock = Block(blockchain.sizeOfBlock)
        transactionZero = Transaction('0', myNode.wallet.public_key, 100 * numberOfNodes, [])
        genesisBlock.add_transaction(transactionZero)
        myNode.wallet.transactions.append(transactionZero)
        genesisBlock.previousHash = '1'
        genesisBlock.getHash()
        genesisBlock.nonce = 0
        blockchain.addBlock(genesisBlock)

        # Add my info to myNode's table
        myNode.syncNodesTable(myNode.Id, myNode.wallet.public_key,
                              myNode.wallet_balance(myNode.wallet.public_key), myIp, myPort)

        # Initialize transactionZero utxos
        transactionZeroOutputs = transactionZero.transaction_outputs
        for transaction_output_id, utxo in transactionZeroOutputs.items():
            if utxo['recipient_id'] != '0':
                utxoBootstrap = utxo
        myNode.utxos[myNode.wallet.public_key][utxoBootstrap['transaction_output_id']] = utxoBootstrap



    # if the node isn't the bootstrap node, then communicate with it
    # to get my ID and to synchronise the node tables
    else:
        # make a request to the boostrap node and process the data it returns
        addressString = f'http://{bootstrapAdress}:{bootstrapPort}/api/newNodeAdded'
        bootsrapResponse = requests.get(addressString)
        myNode.Id = int(bootsrapResponse.json()['newNodeId'])
        myNode.nodeCount = myNode.Id + 1
        tempChainList = bootsrapResponse.json()['blockchainState']

        # get the blocks from the blockchain that was sent
        for iBlockDict in reversed(tempChainList):
            iBlock = dictToBlock(iBlockDict)
            myNode.chain.addBlock(iBlock)
        print(f"Valid chain: {myNode.validate_chain()}")

        # get the transactions of the unmined running block of the bootstrap node
        myNode.runningBlock.listOfTransactions.update(bootsrapResponse.json()['unminedTransactions'])

        # transactionZero = dictToTransaction(genesisBlock.listOfTransactions[0])
        # for _, output in transactionZero.transaction_outputs.items():
        #     if output['recipient_id'] != '0':
        #         transactionZeroUTXO = output
        #         break
        # add transactionZero to as a utxo entry in the bootstrap wallet address

        # tempRecipient = transactionZeroUTXO['recipient_id']
        # tempOutId = transactionZeroUTXO['transaction_output_id']

        # myNode.utxos[tempRecipient] = {}
        # myNode.utxos[tempRecipient][tempOutId] = transactionZeroUTXO

        # Add my info to myNode's table
        myNode.syncNodesTable(myNode.Id, myNode.wallet.public_key,
                              myNode.wallet.balance(), myIp, myPort)

        # Get the bootstrap node's table
        bootsrapResponse = requests.get(
                f'http://{bootstrapAdress}:{bootstrapPort}/api/syncNodesTable')
        bootsrapNodesTable = bootsrapResponse.json()['nodesTable']

        # Write the entries to myNode's table
        for id, infoDict in bootsrapNodesTable.items():
            myNode.syncNodesTable(
                    int(id), infoDict['walletAddress'], infoDict['walletBalance'], infoDict['ip'], infoDict['port'],
                    bootsrapResponse.json()['utxos'])

        # Broadcast my info to every node found on myNode's updated table using a PUT request
        for id, tableInfoDict in myNode.nodesTable.items():
            if myNode.Id != id:
                addressString = f"http://{tableInfoDict['ip']}:{tableInfoDict['port']}/api/syncNodesTable"
                requests.put(addressString, json={'myNodesTable': myNode.nodesTable, 'utxo': myNode.utxos})

    app.run(host=myIp, port=myPort)
