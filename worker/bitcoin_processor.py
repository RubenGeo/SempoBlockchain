from bit import Key, PrivateKeyTestnet
from bit.network import currency_to_satoshi_cached

from time import sleep

import json, base64
from web3 import Web3, HTTPProvider

from ethereum import utils
from cryptography.fernet import Fernet

from celery import chain

import requests
from requests.auth import HTTPBasicAuth

from worker import celery_tasks, red

import config

import datetime


class PreBlockchainError(Exception):
    pass

class BitcoinProcessor(object):

    def cents_to_native_amount(self, cents):
        # dividing by 100 because we work in cents
        return float(cents) * (10**self.decimals) / 100


    def native_amount_to_cents(self, native_amount):
        return int(float(native_amount) / (10**self.decimals) * 100)

    def create_address_only_credit_transfer_in_app(self,
                                                   sender_address,
                                                   recipient_address,
                                                   transaction_hash,
                                                   amount):

        converted_amount = self.native_amount_to_cents(amount)

        body = {
            'sender_blockchain_address': sender_address,
            'recipient_blockchain_address': recipient_address,
            'blockchain_transaction_hash': transaction_hash,
            'transfer_amount': converted_amount
        }

        r = requests.post(config.APP_HOST + '/api/credit_transfer/internal/',
                          json=body,
                          auth=HTTPBasicAuth(config.BASIC_AUTH_USERNAME,
                                             config.BASIC_AUTH_PASSWORD))

        return r

    def _send_blockchain_result_to_app(self, result, request_method):

        if result.get('credit_transfer_id') is None:
            print('########WARNING: No credit transfer id supplied########')

        result['is_bitcoin'] = True
        result['signing_address'] = self.key.address

        print('sending result:')
        print(str(result))

        r = request_method(config.APP_HOST + '/api/blockchain_transaction/',
                          json=result,
                          auth=HTTPBasicAuth(config.BASIC_AUTH_USERNAME,
                                             config.BASIC_AUTH_PASSWORD))

        if r.status_code >= 400:
            raise Exception("Error with sending result: {}".format(str(r.json())))

        return r

    def post_blockchain_result_to_app(self, result):
        return self._send_blockchain_result_to_app(result, requests.post)

    def put_blockchain_result_to_app(self, result):
        return self._send_blockchain_result_to_app(result, requests.put)

    def parse_blockchain_task(self, task):

        print('-----------------------------------------------------------------')
        print('{} parsing task:'.format(datetime.datetime.utcnow()))
        print(task)

        type = task.get('type')
        transfer_amount = task.get('transfer_amount')
        recipient = task.get('recipient')
        credit_transfer_id = task.get('credit_transfer_id')

        if type == 'DISBURSEMENT':
            self.add_disbursement_to_next_transaction(recipient, transfer_amount, credit_transfer_id)

    def add_disbursement_to_next_transaction(self,recipient, transfer_amount, credit_transfer_id):

        # next_transaction is dict with:
        # list of outputs to be sent in the next transaction
        # list of credit transfer ids for these outputs
        next_transaction = red.get('next_transaction')

        # Only start a countdown if there isn't one already running
        if next_transaction is None:

            start_submit_countdown = True

            next_transaction = {
                'outputs': [],
                'credit_transfer_ids': [],
            }

        else:

            start_submit_countdown = False

            next_transaction = json.loads(next_transaction)

        converted_transfer_amount = self.cents_to_native_amount(transfer_amount)
        # /100 : remove platform-wide cents conversion
        # /10**8: sat -> BTC

        print("Sending: " + str(converted_transfer_amount))
        next_transaction['outputs'].append((recipient,converted_transfer_amount, 'btc'))
        next_transaction['credit_transfer_ids'].append(credit_transfer_id)

        red.set('next_transaction', json.dumps(next_transaction))

        if start_submit_countdown:
            chain_list = [
                celery_tasks.get_next_transaction_outputs.s(),
                celery_tasks.resilient_bitcoin_send.s(),
                celery_tasks.check_whether_transaction_sent_to_pool.s(),
                celery_tasks.check_transaction_status_in_pool.s()
            ]

            chain(chain_list).apply_async(countdown=self.hold_transaction_seconds)

    def get_next_transaction_outputs(self):

        next_transaction = json.loads(red.get('next_transaction'))

        red.delete('next_transaction')

        return next_transaction

    def send_bitcoin_transaction(self, outputs):

        self.key.get_unspents()

        transaction_hash = self.key.send(outputs)

        return transaction_hash


    def check_whether_transaction_sent_to_pool(self, transaction_hash, credit_transfer_ids):

        submitted_date = datetime.datetime.utcnow()

        blockchain_transaction_ids = []

        result = requests.get(self.blockchain_explorer_url + 'tx/' + transaction_hash)

        if result.status_code == 200:
            for credit_transfer_id in credit_transfer_ids:
                response = self.post_blockchain_result_to_app({
                    'credit_transfer_id': credit_transfer_id,
                    'status': 'PENDING',
                    'transaction_type': 'transfer',
                    'transaction_hash': transaction_hash,
                    'submitted_date': submitted_date.isoformat()
                })

                blockchain_transaction_ids.append(response.json()['transaction_id'])

            return (transaction_hash, blockchain_transaction_ids)

        return None

    def check_transaction_status_in_pool(self, transaction_hash, blockchain_transaction_ids):

        result = requests.get(self.blockchain_explorer_url + 'tx/' + transaction_hash)

        added_date = datetime.datetime.utcnow()

        if result.json()['transaction']['confirmations'] > 0:
            for transaction_id in blockchain_transaction_ids:
                response = self.put_blockchain_result_to_app({
                    'transaction_id': transaction_id,
                    'status': 'SUCCESS',
                    'added_date': added_date.isoformat()
                })

            return True

        return False

    def find_new_outputs(self):
        # First get transactions needing outputs

        r = requests.get(config.APP_HOST + '/api/blockchain_transaction/',
                         auth=HTTPBasicAuth(config.BASIC_AUTH_USERNAME,
                                            config.BASIC_AUTH_PASSWORD))

        if not r.status_code == 201:
            return

        transactions = r.json()['transactions']

        # transactions is:
        # A dict of transactions hashes representing unspent bitcoin transactions
        # Mapping to the recipient blockchain addresses of that transaction
        # Mapping to the transaction ID in the database
        # (One bitcoin transaction can have multiple recipients,
        #  and so multiple blockchain transactions & credit transfers)

        new_transfers = {}

        for hash in transactions:
            result = requests.get(self.blockchain_explorer_url + 'tx/' + hash)

            try:
                outputs = result.json()['transaction']['outputs']
            except KeyError:
                outputs = []

            for output in outputs:

                output_address = output['addresses'][0]

                if output_address in transactions[hash] and output['spend_txid']:
                    # The txn recipient is one of our platform's recipients (expected)
                    # and this recipient has spent their output

                    platform_address = output_address
                    # Just so we're clear that we're referring to a platform recipient

                    output_transaction_details = []

                    spend_txid = output['spend_txid']
                    spend_txn = requests.get(self.blockchain_explorer_url + 'tx/' + spend_txid).json()
                    spend_txn_outputs = spend_txn['transaction']['outputs']

                    for spend_output in spend_txn_outputs:
                        if spend_output['addresses'][0] != platform_address:
                            # The recipient of the spending transaction isn't one of our platform addresses
                            # AKA it's not the return transaction
                            output_transaction_details.append({
                                'spend_transaction_recipient': spend_output['addresses'][0],
                                'spend_transaction_value': spend_output['value']
                            })

                    for output_detail in output_transaction_details:
                        put = self.put_blockchain_result_to_app({
                            'transaction_id': transactions[hash][platform_address],
                            'has_output_txn': True
                        })

                        if spend_txid not in new_transfers:
                            new_transfers[spend_txid] = {
                                'sender_address': platform_address,
                                'recipient_address': output_detail['spend_transaction_recipient'],
                                'transaction_hash': spend_txid,
                                'amount': output_detail['spend_transaction_value']
                            }

        for transaction_hash in new_transfers:

            data = new_transfers[transaction_hash]

            result = self.create_address_only_credit_transfer_in_app(
                sender_address=data['sender_address'],
                recipient_address=data['recipient_address'],
                transaction_hash=data['transaction_hash'],
                amount=data['amount']
            )

    def get_master_wallet_balance_async(self):

        # Multiply by 100 because the main system always works in 100 * base unit
        return float(self.key.get_balance()) * 100

    def get_usd_to_satoshi_rate(self):
        return currency_to_satoshi_cached(1, 'usd')

    def __init__(self, master_wallet_wif, testnet=False, hold_transaction_seconds=20, decimals=-8):

        if testnet:
            self.key = PrivateKeyTestnet(master_wallet_wif)
            self.blockchain_explorer_url = 'https://testnet-api.smartbit.com.au/v1/blockchain/'
        else:
            self.key = Key(master_wallet_wif)
            self.blockchain_explorer_url = 'https://api.smartbit.com.au/v1/blockchain/'

        self.hold_transaction_seconds = hold_transaction_seconds

        self.decimals = decimals

