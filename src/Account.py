import hashlib
import json
import base64

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

class Account:
    # Default balance is 100 if not sent during account creation
    # nonce is incremented once every transaction to ensure tx can't be replayed and can be ordered (similar to Ethereum)
    # private and public pem strings should be set inside __generate_key_pair
    def __init__(self, sender_id, balance=100):
        self._id = sender_id
        self._initial_balance = balance
        self._balance = balance
        self._nonce = 0
        self._private_pem = None
        self._public_pem = None
        self.__generate_key_pair()

    @property
    def id(self):
        return self._id

    @property
    def public_key(self):
        return self._public_pem

    @property
    def balance(self):
        return self._balance

    def increase_balance(self, value):
        self._balance += value

    def decrease_balance(self, value):
        self._balance -= value

    def __generate_key_pair(self):
        # Implement key pair generation logic
        # Convert them to pem format strings and store in the class attributes already defined
        # Generating the private/public key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        # Assigning the public key from the pair
        public_key = private_key.public_key()
        # Serializing the private key data to show what the file pem data looks like
        self._private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        # Serializing the public key data to show what the file pem data looks like
        self._public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def create_transaction(self, receiver_id, value, tx_metadata=''):
        nonce = self._nonce + 1
        transaction_message = {'sender': self._id, 'receiver': receiver_id, 'value': value, 'tx_metadata': tx_metadata, 'nonce': nonce}

        signature = ''
        private_key = serialization.load_pem_private_key(self._private_pem, password=None)
        transaction_string = json.dumps(transaction_message, sort_keys=True)
        encoded_transaction_string = transaction_string.encode('utf-8')
        transaction_string_hash = hashlib.sha256(encoded_transaction_string).hexdigest().encode('utf-8')

        # Implement digital signature of the hash of the message
        signature = base64.b64encode(private_key.sign(transaction_string_hash, padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ), hashes.SHA256())).decode('utf-8')

        self._nonce = nonce
        return {'message': transaction_message, 'signature': signature}

    @property
    def initial_balance(self):
        return self._initial_balance
