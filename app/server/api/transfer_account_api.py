import datetime
from flask import Blueprint, request, make_response, jsonify, g
from flask.views import MethodView

from sqlalchemy import and_, or_

from server import db
from server.models import paginate_query, TransferAccount
from server.schemas import transfer_accounts_schema, transfer_account_schema, \
    view_transfer_account_schema, view_transfer_accounts_schema
from server.utils.auth import requires_auth

transfer_account_blueprint = Blueprint('transfer_account', __name__)


class TransferAccountAPI(MethodView):
    @requires_auth(allowed_roles=['is_admin', 'is_view'])
    def get(self, transfer_account_id):

        # can_see_full_details = role in ['is_admin', 'is_view']
        #
        # if not (can_see_full_details):
        #     return less_detail


        account_type_filter = request.args.get('account_type')
        result = None

        if transfer_account_id:
            transfer_account = TransferAccount.query.get(transfer_account_id)

            if transfer_account is None:
                response_object = {
                    'message': 'No such transfer account: {}'.format(transfer_account_id),
                }

                return make_response(jsonify(response_object)), 400

            if g.user.is_admin:
                result = transfer_account_schema.dump(transfer_account)
            elif g.user.is_view:
                result = view_transfer_account_schema.dump(transfer_account)

            response_object = {
                'message': 'Successfully Loaded.',
                'data': {'transfer_account': result.data,}
            }
            return make_response(jsonify(response_object)), 201

        else:
            if account_type_filter == 'vendor':
                transfer_accounts_query = TransferAccount.query.filter_by(is_vendor=True)
            elif account_type_filter == 'beneficiary':
                transfer_accounts_query = TransferAccount.query.filter_by(is_vendor=False)
            else:
                transfer_accounts_query = TransferAccount.query

            transfer_accounts, total_items, total_pages = paginate_query(transfer_accounts_query, TransferAccount)

            if transfer_accounts is None:
                response_object = {
                    'message': 'No transfer accounts',
                }

                return make_response(jsonify(response_object)), 400

            if g.user.is_admin:
                result = transfer_accounts_schema.dump(transfer_accounts)
            elif g.user.is_view:
                result = view_transfer_accounts_schema.dump(transfer_accounts)

            response_object = {
                'message': 'Successfully Loaded.',
                'items': total_items,
                'pages': total_pages,
                'data': {'transfer_accounts': result.data}
            }
            return make_response(jsonify(response_object)), 201

    @requires_auth(allowed_roles=['is_admin'])
    def put(self, transfer_account_id):
        put_data = request.get_json()

        transfer_account_id_list = put_data.get('transfer_account_id_list')
        approve = put_data.get('approve')

        transfer_account_name = put_data.get('transfer_account_name')

        payable_period_type = put_data.get('payable_period_type')
        payable_period_length = put_data.get('payable_period_length')
        payable_epoch = put_data.get('payable_epoch')

        if transfer_account_id:

            transfer_account = TransferAccount.query.get(transfer_account_id)

            if not transfer_account:
                response_object = {
                    'message': 'Transfer account not found'
                }
                return make_response(jsonify(response_object)), 400

            if transfer_account_name and not transfer_account_name == transfer_account.name:
                transfer_account.name = transfer_account_name

            if payable_period_type and not payable_period_type == transfer_account.payable_period_type:
                transfer_account.payable_period_type = payable_period_type

            if payable_period_length and not payable_period_length == transfer_account.payable_period_length:
                transfer_account.payable_period_length = payable_period_length

            if payable_epoch and not payable_epoch == transfer_account.payable_epoch:
                transfer_account.payable_epoch = payable_epoch

            if not approve == transfer_account.is_approved and transfer_account.is_approved is not True:
                transfer_account.approve()

            db.session.commit()

            result = transfer_account_schema.dump(transfer_account)
            response_object = {
                'message': 'Successfully Edited Transfer Account.',
                'data': {
                    'transfer_account': result.data,
                }
            }
            return make_response(jsonify(response_object)), 201


        else:

            transfer_accounts = []
            response_list = []

            for transfer_account_id in transfer_account_id_list:

                transfer_account = TransferAccount.query.get(transfer_account_id)
                if not transfer_account:
                    response_list.append({
                        'status': 400,
                        'message': 'Transfer account id {} not found'.format(transfer_account_id)
                    })

                    continue

                if not transfer_account.is_approved and approve:
                    transfer_account.approve()

                transfer_accounts.append(transfer_account)

            db.session.commit()

            response_object = {
                'status': 'success',
                'message': 'Successfully Edited Transfer Accounts.',
                'data': {
                    'transfer_accounts': transfer_accounts_schema.dump(transfer_accounts).data
                }
            }
            return make_response(jsonify(response_object)), 201

# add Rules for API Endpoints
transfer_account_blueprint.add_url_rule(
    '/transfer_account/',
    view_func=TransferAccountAPI.as_view('transfer_account_view'),
    methods=['GET', 'PUT', 'POST'],
    defaults={'transfer_account_id': None}
)

transfer_account_blueprint.add_url_rule(
    '/transfer_account/<int:transfer_account_id>/',
    view_func=TransferAccountAPI.as_view('single_transfer_account_view'),
    methods=['GET', 'PUT']
)