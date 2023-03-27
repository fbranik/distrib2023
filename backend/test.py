# from wallet import Wallet
# from transaction import Transaction
# from cryptography.hazmat.primitives import serialization as serialization
# from cryptography.hazmat.primitives.asymmetric import rsa, padding
# from cryptography.hazmat.primitives.hashes import SHA256
# from cryptography.hazmat.primitives import hashes
# from cryptography.hazmat.backends import default_backend

# myWallet    = Wallet()
# otherWallet = Wallet()

# myTransaction = Transaction(myWallet.public_key, otherWallet.public_key, 10)

# myTransaction.sign_transaction(myWallet.private_key)

# print(myTransaction.transaction_id)


# otherPublic = serialization.load_pem_public_key(otherWallet.public_key)
# myPublic    = serialization.load_pem_public_key(myWallet.public_key)

# print(myTransaction.verify_signature())

# badTransaction = Transaction(myWallet.public_key, otherWallet.public_key, 10)

# # badTransaction.signature = myTransaction.signature

# print(badTransaction.verify_signature())


# import requests

# with open('public5000.key', 'rb') as keyIn:
#         pemlines = keyIn.read()

# public_keyObject = serialization.load_ssh_public_key(pemlines)
# myPublic_key     = requests.utils.quote(public_keyObject.public_bytes(serialization.Encoding.OpenSSH,
#                                                  serialization.PublicFormat.OpenSSH
#                                                 ))

# with open('public5001.key', 'rb') as keyIn:
#         pemlines = keyIn.read()

# public_keyObject = serialization.load_ssh_public_key(pemlines)
# theirPublic_key  = requests.utils.quote(public_keyObject.public_bytes(serialization.Encoding.OpenSSH,
#                                                  serialization.PublicFormat.OpenSSH
#                                                 ))

# addressString = f'http://127.0.0.1:5000/api/createNewTransaction?senderAddress={myPublic_key}&recipientAddress={theirPublic_key}&amount=10'
# addressString = addressString.replace('ssh-rsa%20', '')

# print(addressString)
# resp = requests.get(addressString)
# print(resp)
