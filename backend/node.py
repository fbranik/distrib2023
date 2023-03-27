from backend.block import Block, dictToBlock
from backend.wallet import Wallet
from backend.blockchain import Blockchain
from backend.transaction import Transaction, dictToTransaction
from backend.transaction_input import TransactionInput
from backend.broadcastRequest import broadcastRequest
import requests
from sys import maxsize
from random import randint
from threading import Event
from threading import Thread, Lock
from multiprocessing import Queue
from datetime import datetime
from time import sleep


class Node:
    def __init__(self, blockchain: Blockchain, difficulty: int, wallet: Wallet = None, isBootstrap=False):
        self.chain = blockchain
        self.difficulty = difficulty
        self.miningStopEvent = Event()
        self.conflictActive = False
        self.Choosing = False
        self.conflictsTable = {}
        self.conflictedChainSizes = {}
        self.acquiredTransactions = {}
        self.recoveryTransactions = {}
        self.chainLock = Lock()
        # initialize a block to add transactions in it
        self.runningBlock = Block(self.chain.sizeOfBlock)
        # list of transactions in the block that's being mined
        if wallet is not None:
            # if a wallet already exist no need to create a new one
            self.wallet = wallet
        else:
            self.generate_wallet()

        if isBootstrap:
            self.Id = 0
            self.nodeCount = 1
        else:
            self.Id = None
            self.nodeCount = None
        # Initialize my utxos with an empty entry from my wallet's address
        self.utxos = {}
        self.utxos[self.wallet.public_key] = {}
        self.nodesTable = None
        self.miningQueue = Queue()
        thread = Thread(target=self.mine_block, args=(self.miningStopEvent,), daemon=True)
        thread.start()

    def generate_wallet(self):
        self.wallet = Wallet()

    def syncNodesTable(self, id, walletAddress, balance, ip, port, utxos=None):
        """
        Method to update the nodesTable dictionary of the node
        When a new node is created, this should be ran with the
        ip of the node, as well as with the values from the
        already existant table from the other nodes
        """
        if self.nodesTable is None:
            self.nodesTable = {}

        self.nodesTable[id] = {'walletAddress': walletAddress,
                               'walletBalance': balance,
                               'ip'           : ip,
                               'port'         : port
                               }

        if utxos is not None:
            self.utxos.update(utxos)

    def create_transaction(self, receiver, value):
        # the sender address is the address of the node that creates the transaction
        sender_address = self.wallet.public_key
        # the sender node finds the receiver address from its table
        receiver_address = self.nodesTable[receiver]['walletAddress']

        # collect the required UTXOs
        sum = 0
        transaction_inputs = []

        for _, utxo in self.utxos[self.wallet.public_key].items():
            if sum >= value:
                break
            sum += utxo['amount']
            transaction_inputs.append(TransactionInput(
                    utxo['transaction_output_id'], utxo['amount']))

        if sum < value:
            # not enough NBCs
            return None

        # create the new transaction and sign it
        transaction = Transaction(
                sender_address, receiver_address, value, transaction_inputs)
        transaction.sign_transaction(self.wallet.private_key)

        # remove previous utxos using the keys from the transaction inputs
        for trInput in transaction.transaction_inputs:
            old_transaction_output_id = trInput['previous_output_id']
            del self.utxos[sender_address][old_transaction_output_id]

        # add new utxos
        for _, newUTXO in transaction.transaction_outputs.items():
            # make sure the dict is created
            if newUTXO['recipient_id'] not in self.utxos.keys():
                self.utxos.update({newUTXO['recipient_id']: {}})
            iRecipient = newUTXO['recipient_id']
            newEntry = {newUTXO['transaction_output_id']: newUTXO}
            self.utxos[iRecipient].update(newEntry)

        transactions_log = open(f'logs/transactions{self.Id}_{self.chain.sizeOfBlock}_{self.difficulty}.txt', 'a')
        transactions_log.write(f'{transaction.timestamp}\n')
        transactions_log.close()
        return transaction

    def broadcast_transaction(self, transaction: Transaction):
        """
        Method to broadcast a transaction to every node found in the nodesTable
        """
        broadcastRequest("/api/broadcastTransaction", self.nodesTable, self.Id, json=transaction.toDict())
        # add the transaction to my running block
        self.addTransactionToBlock(transaction)

    def validate_transaction(self, transaction: Transaction):
        if not transaction.verify_signature():
            return False
        # check inputs
        if transaction.sender_address not in self.utxos.keys():
            self.utxos.update({transaction.sender_address: {}})
        sum = 0

        # check if the transactionInputs come from a previous transaction output
        for transactionInput in transaction.transaction_inputs:
            if transactionInput['previous_output_id'] not in self.utxos[transaction.sender_address]:
                return False
            sum += transactionInput['amount']
        # if the amount from the transaction inputs is greater than the transaction amount
        # the transaction isn't valid
        if sum < transaction.amount:
            return False

        # check outputs
        for _, utxo in transaction.transaction_outputs.items():
            if utxo['recipient_id'] == transaction.receiver_address:
                if utxo['amount'] != transaction.amount:
                    # print('edw3')
                    return False
            if utxo['recipient_id'] == transaction.sender_address:
                if utxo['amount'] != sum - transaction.amount:
                    # print('edw4')
                    return False

        # remove previous utxos using the keys from the transaction inputs
        for trInput in transaction.transaction_inputs:
            old_transaction_output_id = trInput['previous_output_id']
            del self.utxos[transaction.sender_address][old_transaction_output_id]

        # add new utxos
        for _, newUTXO in transaction.transaction_outputs.items():
            # make sure the dict is created
            if newUTXO['recipient_id'] not in self.utxos.keys():
                self.utxos.update({newUTXO['recipient_id']: {}})
            iRecipient = newUTXO['recipient_id']
            newEntry = {newUTXO['transaction_output_id']: newUTXO}
            self.utxos[iRecipient].update(newEntry)

        return True

    def wallet_balance(self, walletAddress=None):
        if walletAddress == None:
            walletAddress = self.wallet.public_key
        sum = 0
        for _, utxo in self.utxos[walletAddress].items():
            sum += utxo['amount']
        return sum

    def addTransactionToBlock(self, transaction: Transaction):
        currentRunningBlock = self.runningBlock
        self.acquiredTransactions[transaction.transaction_id] = {'block'       : currentRunningBlock,
                                                                 'isBeingMined': False}
        isBlockFull = currentRunningBlock.add_transaction(transaction)

        if isBlockFull:
            self.miningQueue.put(currentRunningBlock)
            self.runningBlock = Block(self.chain.sizeOfBlock)

    def mine_block(self, stopEvent: Event):

        while True:

            while self.conflictActive:
                # busy wait for conflict to be resolved
                pass
            block = self.miningQueue.get()
            if block is not None:
                for iTransaction in block.listOfTransactions.keys():
                    try:
                        self.acquiredTransactions[iTransaction]['isBeingMined'] = True
                    except:
                        pass
                block.previousHash = self.chain.getLastBlock().getHash()
                block.nonce = randint(0, maxsize)
                startingTransactions = block.getAllTransactionsIds()
                print("\n---------------Starting Mining---------------\n")
                while not (block.getHash().startswith(self.difficulty * '0') or stopEvent.is_set()):
                    block.nonce = randint(0, maxsize)
                    block.hash = None

                if not stopEvent.is_set() and startingTransactions == block.getAllTransactionsIds():
                    print("\n-----------------Mined block-----------------\n")
                    if not self.conflictActive:
                        self.chainLock.acquire()
                        self.chain.addBlock(block)
                        self.chainLock.release()

                        self.broadcast_block(block)
                else:
                    # mining was interrupted either because a new block had some
                    # transactions that were in the block being mined
                    # or because a  conflict was detected
                    print("\n-------------Mining Interrupted--------------\n")
                    # busy wait until mining can restart
                    self.miningStopEvent.clear()

    def broadcast_block(self, block: Block):
        # delete the blocks transactions from my acquired transactions
        for iTransaction in block.listOfTransactions.keys():
                try:
                    del self.acquiredTransactions[iTransaction]
                except:
                    pass
        broadcastRequest("/api/broadcastBlock", self.nodesTable, self.Id, json=block.toDict())

    def validate_block(self, block: Block, currentLastBlockHash=None, chain: Blockchain = None):
        if chain is None:
            chain = self.chain
        if currentLastBlockHash is None:
            currentLastBlockHash = '1'
            lastBlock = chain.getLastBlock()
            if lastBlock != None:
                currentLastBlockHash = chain.getLastBlock().getHash()
        # 'wrongHash' for invalid block hash
        # 'conflict' for conflict in previous Hash
        # 'valid' for fully valid block
        if not block.getHash().startswith(self.difficulty * '0'):
            # print('oxi starts with')
            return False, 'wrongHash'
        currentLastBlockHash = chain.getLastBlock().getHash()
        if block.previousHash != currentLastBlockHash:
            # print('oxi consensus')
            return False, 'conflict'
        elif self.conflictActive:
            # print('ksypna')
            return False, ''

        return True, 'valid'

    def validate_chain(self, chain=None):
        if chain is None:
            chain = self.chain
        blocksList = chain.listOfBlocks
        genesis = blocksList[0]
        if genesis.previousHash != '1' or genesis.nonce != 0:
            return False
        currentLastBlockHash = genesis.getHash()
        for i in range(1, len(blocksList)):
            if not self.validate_block(blocksList[i], currentLastBlockHash, chain):
                return False
            currentLastBlockHash = blocksList[i].getHash()
        return True

    def resolve_conflict(self, broadcast=True):
        # pause mining
        self.conflictRole = broadcast
        self.conflictActive = True
        # stop all mining threads
        self.miningStopEvent.set()
        self.nodeCount = len(self.nodesTable)
        self.conflictedChainSizes[str(self.Id)] = len(self.chain.listOfBlocks)
        if broadcast:
            responsesBool = True
            while not (len(self.conflictedChainSizes) == self.nodeCount and responsesBool):
                # print("conflict broadcaster", get_ident(), self.conflictedChainSizes)
                responsesBool = True
                for id, tableInfoDict in self.nodesTable.items():
                    if self.Id != id:
                        addressString = f"http://{tableInfoDict['ip']}:{tableInfoDict['port']}/api/resolveConflicts"
                        response = requests.put(addressString, json=self.conflictedChainSizes, timeout=1000)
                        responsesBool = responsesBool and (len(response.json()) == self.nodeCount)
                        # print(responsesBool, (len(response.json()) == self.nodeCount), len(response.json()), self.nodeCount)
                        self.conflictedChainSizes.update(response.json())

            if len(self.conflictedChainSizes) == self.nodeCount and not self.Choosing and responsesBool:
                self.Choosing = True
                for id, tableInfoDict in self.nodesTable.items():
                    if self.Id != id:
                        addressString = f"http://{tableInfoDict['ip']}:{tableInfoDict['port']}/api/chooseConflictResolution"
                        response = requests.get(addressString, timeout=1000)
                conflictThread = Thread(target=self.chooseConflictedChain, args=())
                conflictThread.start()
                conflictThread.join()

    def createListenerChoiceThread(self):
        sleep(0.2)
        if not self.Choosing:
            self.Choosing = True
            conflictThread = Thread(target=self.chooseConflictedChain, args=())
            conflictThread.start()
            conflictThread.join()

    def chooseConflictedChain(self):
        # print("choice", self.conflictedChainSizes)

        # if all chain sizes are erqual, choose the chain of the node with the smallest id
        # (always the bootstrap in our case)
        countInvalidBlocks = 0
        if all(chainSize == self.conflictedChainSizes[str(self.Id)] for chainSize in
               self.conflictedChainSizes.values()):
            chosenChainId = int(min(self.conflictedChainSizes.keys()))
        else:
            chosenChainId = int(max(self.conflictedChainSizes, key=self.conflictedChainSizes.get))
        # print(chosenChainId, self.Id)
        if chosenChainId != self.Id:

            chosenInfo = self.nodesTable[chosenChainId]
            addressString = f"http://{chosenInfo['ip']}:{chosenInfo['port']}/api/chooseConflictResolution"
            response = requests.put(addressString,
                                    json={"lastBlockHash"     : self.chain.getLastBlock().getHash(),
                                          "numOfInvalidBlocks": countInvalidBlocks},
                                    timeout=1000)

            isBlockValid = response.json()["isBlockValid"]
            while not isBlockValid:
                countInvalidBlocks += 1
                # print("eeeeeee",self.chain.listOfBlocks.pop())
                response = requests.put(addressString,
                                        json={"lastBlockHash"     : self.chain.getLastBlock().getHash(),
                                              "numOfInvalidBlocks": countInvalidBlocks},
                                        timeout=1000)

                isBlockValid = response.json()["isBlockValid"]

            newBlocks = response.json()["blocksToAdd"]
            for iBlockDict in newBlocks:
                self.chain.addBlock(dictToBlock(iBlockDict))
        else:
            newBlocks = []

        self.conflictNewBlocks = newBlocks
        chosenInfo = self.nodesTable[self.Id]
        addressString = f"http://{chosenInfo['ip']}:{chosenInfo['port']}/api/runRecoverFromConflict"
        response = requests.put(addressString,
                                json={"myChainChosen": countInvalidBlocks == 0})
        # print("esteila recover")
        # print("\n", self.conflictActive, self.Choosing, "\n")

    def recoverFromConflict(self, myChainChosen):
        # print("mpika recover")

        self.conflictActive = False
        self.Choosing = False
        for id, iTransaction in self.runningBlock.listOfTransactions.items():
            self.addTransactionToBlock(dictToTransaction(iTransaction))
        del self.runningBlock
        self.runningBlock = Block(self.chain.sizeOfBlock)
        if not myChainChosen:
            while bool(self.recoveryTransactions):
                for id, iTransaction in self.recoveryTransactions.copy().items():
                    for iNewBlockDicts in self.conflictNewBlocks:
                        iNewBlock = dictToBlock(iNewBlockDicts)
                        if not id in iNewBlock.listOfTransactions.keys():
                            self.broadcast_transaction(iTransaction)
                            self.addTransactionToBlock(iTransaction)
                    try:
                        del self.recoveryTransactions[id]
                    except:
                        pass
        else:
            while bool(self.recoveryTransactions):
                for id, iTransaction in self.recoveryTransactions.copy().items():
                    self.broadcast_transaction(iTransaction)
                    self.addTransactionToBlock(iTransaction)
                    try:
                        del self.recoveryTransactions[id]
                    except:
                        pass

        # if len(self.chain.listOfBlocks)>2:
        # for i in range(2):
        # #print(i+1, self.chain.listOfBlocks[-(i+1)].getAllTransactionsIds())
        self.conflictedChainSizes.clear()
        self.recoveryTransactions.clear()

    def createListenerConflictThread(self):
        if not self.Choosing:
            resolveThread = Thread(target=self.resolve_conflict, args=(False,))
            resolveThread.start()
            resolveThread.join()

    def createBroadcasterConflictThread(self):
        if not self.Choosing:
            resolveThread = Thread(target=self.resolve_conflict, args=())
            resolveThread.start()

    def view_transactions(self):
        pkeyToId = {}
        for id, node in self.nodesTable.items():
            pkeyToId[node["walletAddress"]] = id
        transactions = {}
        for transaction in self.chain.getLastBlock().listOfTransactions.values():
            i = transaction["transaction_id"]
            transactions[i] = {}
            transactions[i]["amount"] = transaction["amount"]
            transactions[i]["receiver_address"] = pkeyToId[transaction["receiver_address"]]
            if transaction["sender_address"] != '0':
                transactions[i]["sender_address"] = pkeyToId[transaction["sender_address"]]
            transactions[i]["timestamp"] = datetime.fromtimestamp(transaction["timestamp"])
        return transactions

    def writeWalletFiles(self, privateFilename, publicFilename):
        with open(privateFilename, 'wb') as keyOut:
            keyOut.write(bytes.fromhex(self.wallet.private_key))
        with open(publicFilename, 'wb') as keyOut:
            keyOut.write(bytes.fromhex(self.wallet.public_key))

    def createResolveThread(self):
        self.conflictActive = True
        self.chainLengths = {}
        requestThreads = []
        lengthsLock = Lock()
        for id, tableInfoDict in self.nodesTable.items():
            if self.Id != id:
                addressString = f"http://{tableInfoDict['ip']}:{tableInfoDict['port']}/api/getChainLength"
                iThread = Thread(target=self.resolveThread, args=(addressString, lengthsLock,))
                requestThreads.append(iThread)
                iThread.start()

        for iThread in requestThreads:
            iThread.join()

        self.chainLengths[str(self.Id)] = len(self.chain.getlistOfDictBlocks())
        # print(self.chainLengths)
        if all(chainSize == self.chainLengths[str(self.Id)] for chainSize in self.chainLengths.values()):
            chosenChainId = int(min(self.chainLengths.keys()))
        else:
            tempKeys = list(self.chainLengths.keys())
            tempKeys.sort()
            sortedLengths = {i: self.chainLengths[i] for i in tempKeys}
            chosenChainId = int(max(sortedLengths, key=sortedLengths.get))
        if chosenChainId != self.Id:
            chosenInfo = self.nodesTable[chosenChainId]
            addressString = f"http://{chosenInfo['ip']}:{chosenInfo['port']}/api/getChain"
            response = requests.get(addressString,
                                    timeout=10000)
            # print("phra to", chosenChainId)
            tempChainList = response.json()['chain']
            self.chain.listOfBlocks.clear()
            # get the blocks from the blockchain that was sent
            for iBlockDict in tempChainList:
                iBlock = dictToBlock(iBlockDict)
                self.chain.addBlock(iBlock)
        self.conflictActive = False

    def resolveThread(self, addressString, lengthsLock):
        response = requests.get(addressString, timeout=1000)
        with lengthsLock:
            self.chainLengths.update(response.json())
