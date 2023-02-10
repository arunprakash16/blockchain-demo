import json
import hashlib
import base64

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.exceptions import InvalidSignature

from Block import Block


class Blockchain:
    # Basic blockchain init
    # Includes the chain as a list of blocks in order, pending transactions, and known accounts
    # Includes the current value of the hash target. It can be changed at any point to vary the difficulty
    # Also initiates a genesis block
    def __init__(self, hash_target):
        self._chain = []
        self._pending_transactions = []
        self._failed_transactions = list()
        self._chain.append(self.__create_genesis_block())
        self._hash_target = hash_target
        self._accounts = {}
        self._valid_chain = 0

    def __str__(self):
        return f"Chain:\n{self._chain}\n\nPending Transactions: {self._pending_transactions}\n"

    @property
    def hash_target(self):
        return self._hash_target

    @hash_target.setter
    def hash_target(self, hash_target):
        self._hash_target = hash_target

    # Creating the genesis block, taking arbitrary previous block hash since there is no previous block
    # Using the famous bitcoin genesis block string here :)  
    def __create_genesis_block(self):
        genesis_block = Block(0, [], 'The Times 03/Jan/2009 Chancellor on brink of second bailout for banks', 
            None, 'Genesis block using same string as bitcoin!')
        return genesis_block

    def __validate_transaction(self, transaction):
        # Serialize transaction data with keys ordered, and then convert to bytes format
        hash_string = json.dumps(transaction['message'], sort_keys=True)
        encoded_hash_string = hash_string.encode('utf-8')
        
        # Take sha256 hash of the serialized message, and then convert to bytes format
        message_hash = hashlib.sha256(encoded_hash_string).hexdigest()
        encoded_message_hash = message_hash.encode('utf-8')

        # Signature - Encode to bytes and then Base64 Decode to get the original signature format back 
        signature = base64.b64decode(transaction['signature'].encode('utf-8'))

        try:
            # Load the public_key object and verify the signature against the calculated hash
            sender_public_pem = self._accounts.get(transaction['message']['sender']).public_key
            sender_public_key = serialization.load_pem_public_key(sender_public_pem)
            sender_public_key.verify(
                                        signature,
                                        encoded_message_hash,
                                        padding.PSS(
                                            mgf=padding.MGF1(hashes.SHA256()),
                                            salt_length=padding.PSS.MAX_LENGTH
                                        ),
                                        hashes.SHA256()
                                    )
        except InvalidSignature:
            return False

        return True

    def __process_transactions(self, transactions):
        # Appropriately transfer value from the sender to the receiver
        # For all transactions, first check that the sender has enough balance. 
        # Return False otherwise
        self._pending_transactions = list()
        for transaction in transactions:
            print(transaction)
            sender_accnt = self.get_account_ref(transaction['message']['sender'])
            print('Sender id: ', sender_accnt.id)
            print('Sender balance: ', sender_accnt.balance)
            if sender_accnt.balance > transaction['message']['value']:
                receiver_accnt = self.get_account_ref(transaction['message']['receiver'])
                print('Receiver id: ', receiver_accnt.id)
                print('Receiver balance: ', receiver_accnt.balance)
                sender_accnt.decrease_balance(transaction['message']['value'])
                receiver_accnt.increase_balance(transaction['message']['value'])
                print('Transferred value: ', transaction['message']['value'])
                print('Updated sender balance: ', sender_accnt.balance)
                print('Updated receiver balance: ', receiver_accnt.balance)
                self._pending_transactions.append(transaction)
            else:
                print('{} has {} only, hence cannot transfer {} to {}'.format(sender_accnt.id.capitalize(),
                                                                              sender_accnt.balance,
                                                                              transaction['message']['value'],
                                                                              transaction['message']['receiver'].capitalize()))
                self._failed_transactions.append(transaction)

        if len(self._pending_transactions) > 0:
            return True
        else:
            return False

    # Creates a new block and appends to the chain
    # Also clears the pending transactions as they are part of the new block now
    def create_new_block(self):
        if self.__process_transactions(self._pending_transactions):
            new_block = Block(len(self._chain), self._pending_transactions, self._chain[-1].block_hash,
                              self._hash_target)
            self._chain.append(new_block)
            self._pending_transactions = []
            return new_block
        else:
            print("No valid transaction exists to create a block!")
            return False

    # Simple transaction with just one sender, one receiver, and one value
    # Created by the account and sent to the blockchain instance
    def add_transaction(self, transaction):
        if self.__validate_transaction(transaction):
            self._pending_transactions.append(transaction)
            return True
        else:
            print(f'ERROR: Transaction: {transaction} failed signature validation')
            return False


    # def __validate_chain_hash_integrity(self):
    #     # Run through the whole blockchain and ensure that previous hash is actually the hash of the previous block
    #     # Return False otherwise
    #     valid_chain = True
    #     prev_hash = self._chain[0].block_hash
    #     valid_chain_height = 0
    #     for __chain in self._chain[1:]:
    #         print('Block hash off {} : {}'.format(valid_chain_height, prev_hash))
    #         print('Previous block hash off {} : {}'.format(__chain.block_index, __chain.previous_block_hash))
    #         if __chain.previous_block_hash == prev_hash:
    #             prev_hash = __chain.block_hash
    #             valid_chain_height = __chain.block_index
    #         else:
    #             valid_chain = False
    #             break
    #     return valid_chain

    def __validate_chain_hash_integrity(self):
        # Run through the whole blockchain and ensure that previous hash is actually the hash of the previous block
        # Return False otherwise
        __valid_chain = True
        i = 0
        chain_len = len(self._chain) - 1
        prev_hash = self._chain[0].block_hash
        accnt_balances = self.get_initial_account_balances()
        while __valid_chain and i < chain_len:
            i += 1
            print('Block hash off {} : {}'.format(self._chain[i-1].block_index, prev_hash))
            print('Previous block hash off {} : {}'.format(self._chain[i].block_index,
                                                           self._chain[i].previous_block_hash))
            print('Block hash off {} : {}'.format(self._chain[i].block_index, self._chain[i].block_hash))
            if self._chain[i].previous_block_hash == prev_hash:
                prev_hash = self._chain[i].block_hash
                __valid_chain, accnt_balances = Blockchain.__validate_block_hash_target(self._chain[i], accnt_balances)
            else:
                __valid_chain = False

        if __valid_chain:
            self._valid_chain = self._chain[i].block_index
            print('All blocks are valid, current block height is : ', self._valid_chain)
        else:
            self._valid_chain = self._chain[i-1].block_index
            print('Block validation failed, blocks valid until - ', self._valid_chain)

        return __valid_chain

    @staticmethod
    def __validate_block_hash_target(__current_block, accnt_balances):
        # Run through the whole blockchain and ensure that block hash meets hash target criteria, and is the actual
        # hash of the block
        # Return False otherwise
        __valid_block = True
        print('Hash value of block {}: {}'.format(__current_block.block_index,
                                                  __current_block.block_hash))
        print('Hash target of block {}: {}'.format(__current_block.block_index,
                                                   __current_block.hash_target))
        if __current_block.block_hash >= __current_block.hash_target or \
                __current_block.block_hash != __current_block.hash_block():
            __valid_block = False
        else:
            __valid_block, accnt_balances = Blockchain.__validate_complete_account_balances(
                __current_block.transactions, accnt_balances)

        return __valid_block, accnt_balances

    @staticmethod
    def __validate_complete_account_balances(transactions, accnt_balances):
        # Run through the whole blockchain and ensure that balances never become negative from any transaction
        # Return False otherwise
        __valid_transactions = True
        print("Initial balance: ", accnt_balances)
        for transaction in transactions:
            if accnt_balances[transaction['message']['sender']] >= transaction['message']['value']:
                accnt_balances[transaction['message']['sender']] -= transaction['message']['value']
                accnt_balances[transaction['message']['receiver']] += transaction['message']['value']
            else:
                __valid_transactions = False
                print(transaction['message'], 'is invalid since not enough funds')
                print('{} account has only {}.'.format(transaction['message']['sender'],
                                                       accnt_balances[transaction['message']['sender']]))
                break
        print("Updated balance: ", accnt_balances)
        return __valid_transactions, accnt_balances

    # Blockchain validation function
    # Runs through the whole blockchain and applies appropriate validations
    def validate_blockchain(self):
        # Call __validate_chain_hash_integrity and implement that method. Return False if check fails
        # Call __validate_block_hash_target and implement that method. Return False if check fails
        # Call __validate_complete_account_balances and implement that method. Return False if check fails
        __valid_blockchain = True
        __valid_blockchain = self.__validate_chain_hash_integrity()
        return __valid_blockchain

    def add_account(self, account):
        self._accounts[account.id] = account

    def get_account_balances(self):
        return [{'id': account.id, 'balance': account.balance} for account in self._accounts.values()]

    def get_account_ref(self, account_id):
        return self._accounts[account_id]

    def get_initial_account_balances(self):
        initial_balances = dict()
        for account in self._accounts.values():
            initial_balances[account.id] = account.initial_balance
        return initial_balances



