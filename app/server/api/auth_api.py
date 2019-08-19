from flask import Blueprint, request, make_response, jsonify, g, current_app
from flask.views import MethodView
from server import db, sentry, basic_auth
# from server import limiter
from server.constants import DENOMINATION_DICT
from server.models import User, BlacklistToken, EmailWhitelist, CurrencyConversion, TransferUsage
from server.utils.intercom import create_intercom_android_secret
from server.utils.auth import requires_auth, tfa_logic
from server.utils.user import save_device_info
from server.utils.phone import proccess_phone_number
from server.utils.feedback import request_feedback_questions
from server.utils.amazon_ses import send_reset_email, send_activation_email, send_invite_email
from server.utils.blockchain_transaction import get_usd_to_satoshi_rate
from sqlalchemy import and_, or_


from datetime import datetime
import time, random

auth_blueprint = Blueprint('auth', __name__)


def get_denominations():
    currency_name = current_app.config['CURRENCY_NAME']
    return DENOMINATION_DICT.get(currency_name, {})

def get_highest_admin_tier(user):
    if user.is_superadmin:
        return 'superadmin'
    elif user.is_admin:
        return 'admin'
    elif user.is_subadmin:
        return 'subadmin'
    elif user.is_view:
        return 'view'
    else:
        return None


def create_user_response_object(user, auth_token, message):

    if current_app.config['IS_USING_BITCOIN']:
        try:
            usd_to_satoshi_rate = get_usd_to_satoshi_rate()
        except Exception:
            usd_to_satoshi_rate = None
    else:
        usd_to_satoshi_rate = None

    must_answer_targeting_survey = False
    if user.is_beneficiary and current_app.config['REQUIRE_TARGETING_SURVEY'] and not user.targeting_survey_id:
        must_answer_targeting_survey = True

    conversion_rate = 1
    currency_name = current_app.config['CURRENCY_NAME']
    if user.default_currency:
        conversion = CurrencyConversion.query.filter_by(code = user.default_currency).first()
        if conversion is not None:
            conversion_rate = conversion.rate
            currency_name = user.default_currency

    transfer_usages = []
    usage_objects = TransferUsage.query.order_by(TransferUsage.priority).limit(11).all()
    for usage in usage_objects:
        if ((usage.is_cashout and user.cashout_authorised) or not usage.is_cashout):
            transfer_usages.append({
                'id': usage.id,
                'name': usage.name,
                'icon': usage.icon,
                'priority': usage.priority,
                'translations': usage.translations
            })

    responseObject = {
        'status': 'success',
        'message': message,
        'auth_token': auth_token.decode(),
        'user_id': user.id,
        'email': user.email,
        'admin_tier': get_highest_admin_tier(user),
        'is_vendor': user.is_vendor,
        'is_supervendor': user.is_supervendor,
        'server_time': int(time.time() * 1000),
        'ecdsa_public': current_app.config['ECDSA_PUBLIC'],
        'pusher_key': current_app.config['PUSHER_KEY'],
        'currency_decimals': current_app.config['CURRENCY_DECIMALS'],
        'currency_name': currency_name,
        'currency_conversion_rate': conversion_rate,
        'secret': user.secret,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'must_answer_targeting_survey': must_answer_targeting_survey,
        'deployment_name': current_app.config['DEPLOYMENT_NAME'],
        'ap_is_active': current_app.config['AP_IS_ACTIVE'],
        'denominations': get_denominations(),
        'terms_accepted': user.terms_accepted,
        'request_feedback_questions': request_feedback_questions(user),
        'default_feedback_questions': current_app.config['DEFAULT_FEEDBACK_QUESTIONS'],
        #This is here to stop the old release from dying
        'feedback_questions': request_feedback_questions(user),
        'transfer_usages': transfer_usages,
        'usd_to_satoshi_rate': usd_to_satoshi_rate,
        'android_intercom_hash': create_intercom_android_secret(user_id=user.id)
    }

    if user.transfer_account:
        responseObject['transfer_account_ID'] = user.transfer_account.id
        responseObject['name'] = user.transfer_account.name

    return responseObject

class CheckBasicAuth(MethodView):

    @basic_auth.required
    def get(self):

        responseObject = {
            'status': 'success',
        }

        return make_response(jsonify(responseObject)), 201

class RefreshTokenAPI(MethodView):
    """
    User Refresh Token Resource
    """
    @requires_auth
    def get(self):
        try:

            auth_token = g.user.encode_auth_token()

            responseObject = create_user_response_object(g.user,auth_token,'Token refreshed successfully.')

            return make_response(jsonify(responseObject)), 201

        except Exception as e:

            responseObject = {
                'status': 'fail',
                'message': 'Some error occurred. Please try again.'
            }

            return make_response(jsonify(responseObject)), 403



class RegisterAPI(MethodView):
    """
    User Registration Resource
    """

    def post(self):
        # get the post data
        post_data = request.get_json()

        email = post_data.get('email')
        password = post_data.get('password')

        # email_tail = email.split('@')[-1]
        email_ok = False

        whitelisted_emails = EmailWhitelist.query.filter_by(used=False).all()

        tier = None
        if '@sempo.ai' in email:
            email_ok = True
            tier = 'superadmin'

        for whitelisted in whitelisted_emails:
            if whitelisted.allow_partial_match and whitelisted.email in email:
                email_ok = True
                tier = whitelisted.tier
                continue
            elif whitelisted.email == email:
                email_ok = True

                whitelisted.used = True
                tier = whitelisted.tier
                continue

        db.session.commit()

        if not email_ok:
            responseObject = {
                'status': 'fail',
                'message': 'Invalid email domain.',
            }
            return make_response(jsonify(responseObject)), 403

        if len(password) < 7:
            responseObject = {
                'status': 'fail',
                'message': 'Password must be at least 6 characters long',
            }
            return make_response(jsonify(responseObject)), 403


        # check if user already exists
        user = User.query.filter_by(email=email).first()
        if user:
            responseObject = {
                'status': 'fail',
                'message': 'User already exists. Please Log in.',
            }
            return make_response(jsonify(responseObject)), 403


        try:

            if tier is None:
                tier = 'subadmin'

            user = User()
            user.create_admin_auth(email, password, tier)

            # insert the user
            db.session.add(user)
            db.session.commit()

            activation_token = user.encode_single_use_JWS('A')

            send_activation_email(activation_token, email)

            # generate the auth token
            responseObject = {
                'status': 'success',
                'message': 'Successfully registered.',
            }

            return make_response(jsonify(responseObject)), 201

        except Exception as e:

            print('Error at: ' + str(datetime.utcnow()))
            print(e)

            raise e







class ActivateUserAPI(MethodView):
    """
    User Registration Resource
    """

    def post(self):
        # get the post data
        post_data = request.get_json()

        activation_token = post_data.get('activation_token')

        if activation_token and activation_token != 'null':
            auth_token = activation_token.split(" ")[0]
        else:
            auth_token = ''
        if auth_token:

            validity_check =  User.decode_single_use_JWS(activation_token, 'A')

            if not validity_check['success']:

                responseObject = {
                    'status': 'fail',
                    'message': validity_check['message']
                }

                return make_response(jsonify(responseObject)), 401

            user = validity_check['user']

            if user.is_activated:
                responseObject = {
                    'status': 'fail',
                    'message': 'Already activated.'
                }

                return make_response(jsonify(responseObject)), 401


            user.is_activated = True

            db.session.commit()

            auth_token = user.encode_auth_token()

            responseObject = {
                'status': 'success',
                'message': 'Successfully activated.',
                'auth_token': auth_token.decode(),
                'user_id': user.id,
                'email': user.email,
            }

            return make_response(jsonify(responseObject)), 201

        else:
            responseObject = {
                'status': 'fail',
                'message': 'Provide a valid auth token.'
            }
            return make_response(jsonify(responseObject)), 401



class LoginAPI(MethodView):
    """
    User Login Resource
    """

    def get(self):

        print("process started")

        challenges = [
            ('Why don’t they play poker in the jungle?','Too many cheetahs.'),
            ('What did the Buddhist say to the hot dog vendor?', 'Make me one with everything.'),
            ('What does a zombie vegetarian eat?', 'Graaaaaaaains!'),
            ('My new thesaurus is terrible.', 'Not only that, but it’s also terrible.'),
            ('Why didn’t the astronaut come home to his wife?', 'He needed his space.'),
            ('I got fired from my job at the bank today.', 'An old lady came in and asked me to check her balance, so I pushed her over.'),
            ('I like to spend every day as if it’s my last', 'Staying in bed and calling for a nurse to bring me more pudding.')
        ]

        challenge = random.choice(challenges)

        # time.sleep(int(request.args.get('delay', 0)))
        # from functools import reduce
        # reduce(lambda x, y: x + y, range(0, int(request.args.get('count', 1))))

        # memory_to_consume = int(request.args.get('MB', 0)) * 1000000
        # bytearray(memory_to_consume)

        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        user_agent = request.environ["HTTP_USER_AGENT"]
        ip = request.environ["REMOTE_ADDR"]
        # proxies = request.headers.getlist("X-Forwarded-For")
        # http://esd.io/blog/flask-apps-heroku-real-ip-spoofing.html

        responseObject = {
            'status': 'success',
            'who_allows_a_get_request_to_their_auth_endpoint': 'We do.',
            challenge[0]: challenge[1],
            # 'metadata': {'user_agent': user_agent, 'ip': ip_address, 'otherip': ip, 'proxies': proxies},
        }
        return make_response(jsonify(responseObject)), 200

    # @limiter.limit("20 per day")
    def post(self):
        # get the post data

        post_data = request.get_json()

        user = None

        email = post_data.get('username') or post_data.get('email')
        password = post_data.get('password')
        tfa_token = post_data.get('tfa_token')

        # First try to match email
        if email:
            user = User.query.filter_by(email=email).first()

        #Now try to match the public serial number (comes in under the phone)
        if not user:
            public_serial_number_or_phone = post_data.get('phone')

            user = User.query.filter_by(public_serial_number=public_serial_number_or_phone).first()

        #Now try to match the phone
        if not user:
            phone = proccess_phone_number(post_data.get('phone'))

            if phone:

                user = User.query.filter_by(phone=phone).first()

        if not (email or post_data.get('phone')):
            responseObject = {
                'status': 'fail',
                'message': 'No username supplied'
            }
            return make_response(jsonify(responseObject)), 401

        if post_data.get('phone') and user and user.one_time_code and not user.is_activated:
            if user.one_time_code == password:
                responseObject = {
                        'status': 'success',
                        'pin_must_be_set': True,
                        'message': 'Please set your pin.'
                }
                return make_response(jsonify(responseObject)), 200

        try:

            if not user or not user.verify_password(post_data.get('password')):

                responseObject = {
                    'status': 'fail',
                    'message': 'Invalid username or password'
                }

                return make_response(jsonify(responseObject)), 401

            if not user.is_activated:

                responseObject = {
                    'status': 'fail',
                    'is_activated': False,
                    'message': 'Account has not been activated. Please check your emails.'
                }
                return make_response(jsonify(responseObject)), 401

            if post_data.get('deviceInfo'):

                save_device_info(post_data.get('deviceInfo'), user)

                db.session.commit()

            auth_token = user.encode_auth_token()

            if not auth_token:

                responseObject = {
                    'status': 'fail',
                    'message': 'Invalid username or password'
                }
                return make_response(jsonify(responseObject)), 401

            # Possible Outcomes:
            # TFA required, but not set up
            # TFA enabled, and user does not have valid TFA token
            # TFA enabled, and user has valid TFA token
            # TFA not required

            tfa_response_oject = tfa_logic(user, tfa_token)
            if tfa_response_oject:

                tfa_response_oject['auth_token'] = auth_token.decode()

                return make_response(jsonify(tfa_response_oject)), 401

            #Update the last_seen TS for this user
            user.update_last_seen_ts()

            responseObject = create_user_response_object(user, auth_token, 'Successfully logged in.')

            return make_response(jsonify(responseObject)), 200

        except Exception as e:

            sentry.captureException()

            raise e

            # responseObject = {
            #     'status': 'fail',
            #     'message': "Unknown Error."
            # }
            #
            # return make_response(jsonify(responseObject)), 500


class LogoutAPI(MethodView):
    """
    Logout Resource
    """
    def post(self):
        # get auth token
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[0]
        else:
            auth_token = ''
        if auth_token:
            resp = User.decode_auth_token(auth_token)
            if not isinstance(resp, str):
                # mark the token as blacklisted
                blacklist_token = BlacklistToken(token=auth_token)
                try:
                    # insert the token
                    db.session.add(blacklist_token)
                    db.session.commit()
                    responseObject = {
                        'status': 'success',
                        'message': 'Successfully logged out.'
                    }
                    return make_response(jsonify(responseObject)), 200
                except Exception as e:
                    responseObject = {
                        'status': 'fail',
                        'message': e
                    }
                    return make_response(jsonify(responseObject)), 200
            else:
                responseObject = {
                    'status': 'fail',
                    'message': resp
                }
                return make_response(jsonify(responseObject)), 401

        else:
            responseObject = {
                'status': 'fail',
                'message': 'Provide a valid auth token.'
            }
            return make_response(jsonify(responseObject)), 403

class RequestPasswordResetEmailAPI(MethodView):
    """
    Password Reset Email Resource
    """
    def post(self):
        # get the post data
        post_data = request.get_json()

        email = post_data.get('email')

        if not email:
            responseObject = {
                'status': 'fail',
                'message': 'No email supplied'
            }

            return make_response(jsonify(responseObject)), 401

        user = User.query.filter_by(email=email).first()

        if user:

            password_reset_token = user.encode_single_use_JWS('R')

            send_reset_email(password_reset_token,email)

        responseObject = {
            'status': 'success',
            'message': 'Reset email sent'
        }

        return make_response(jsonify(responseObject)), 200


class ResetPasswordAPI(MethodView):
    """
    Password Reset Resource
    """
    def post(self):

        # get the post data
        post_data = request.get_json()

        old_password  = post_data.get('old_password')
        new_password  = post_data.get('new_password')
        phone         = proccess_phone_number(post_data.get('phone'))
        one_time_code = post_data.get('one_time_code')


        auth_header = request.headers.get('Authorization')

        #Check authorisation using a one time code
        if phone and one_time_code:
            card = phone[-6:]
            user = (User.query.filter_by(phone = phone).first() or
                    User.query.filter_by(public_serial_number=card).first()
                    )


            if not user:

                responseObject = {
                    'status': 'fail',
                    'message': 'User not found'
                }

                return make_response(jsonify(responseObject)), 401

            if user.is_activated:
                responseObject = {
                    'status': 'fail',
                    'message': 'Account already activated'
                }

                return make_response(jsonify(responseObject)), 401

            if str(one_time_code) != user.one_time_code:

                responseObject = {
                    'status': 'fail',
                    'message': 'One time code not valid'
                }

                return make_response(jsonify(responseObject)), 401

            user.hash_password(new_password)

            user.is_activated = True
            user.one_time_code = None

            auth_token = user.encode_auth_token()

            responseObject = create_user_response_object(user, auth_token, 'Successfully set pin')

            db.session.commit()

            return make_response(jsonify(responseObject)), 200

        # Check authorisation using regular auth
        elif auth_header and auth_header != 'null' and old_password:
            auth_token = auth_header.split(" ")[0]

            resp = User.decode_auth_token(auth_token)

            if isinstance(resp, str):

                responseObject = {
                    'status': 'fail',
                    'message': 'Invalid auth token'
                }

                return make_response(jsonify(responseObject)), 401

            user = User.query.filter_by(id=resp.get('user_id')).first()

            if not user:

                responseObject = {
                    'status': 'fail',
                    'message': 'User not found'
                }

                return make_response(jsonify(responseObject)), 401

            if not user.verify_password(old_password):

                responseObject = {
                    'status': 'fail',
                    'message': 'invalid password'
                }

                return make_response(jsonify(responseObject)), 401

        # Check authorisation using a reset token provided via email
        else:

            reset_password_token = post_data.get('reset_password_token')

            if not reset_password_token:

                responseObject = {
                    'status': 'fail',
                    'message': 'Missing token.'
                }

                return make_response(jsonify(responseObject)), 401

            reset_password_token = reset_password_token.split(" ")[0]

            validity_check = User.decode_single_use_JWS(reset_password_token, 'R')

            if not validity_check['success']:
                responseObject = {
                    'status': 'fail',
                    'message': validity_check['message']
                }

                return make_response(jsonify(responseObject)), 401

            user = validity_check['user']

        if not new_password or len(new_password) < 6:
            responseObject = {
                'status': 'fail',
                'message': 'Password must be at least 6 characters long'
            }

            return make_response(jsonify(responseObject)), 401

        user.hash_password(new_password)
        db.session.commit()

        responseObject = {
            'status': 'success',
            'message': 'Password changed, please log in'
        }

        return make_response(jsonify(responseObject)), 200

class PermissionsAPI(MethodView):

    @requires_auth(allowed_roles=['is_admin'])
    def get(self):

        admins = User.query.filter(or_(
            User.is_subadmin == True,
            User.is_admin == True,
            User.is_superadmin == True,
            User.is_view == True,
        )
        ).all()

        admin_list = []
        for admin in admins:

            tier = None

            if admin.is_superadmin:
                tier = 'superadmin'
            elif admin.is_admin:
                tier = 'admin'
            elif admin.is_subadmin:
                tier = 'subadmin'
            else:
                tier = 'view'

            admin_list.append({
                'id': admin.id,
                'email': admin.email,
                'admin_tier': tier,
                'created': admin.created,
                'is_activated': admin.is_activated,
                'is_disabled': admin.is_disabled
            })

        responseObject = {
            'status': 'success',
            'message': 'Admin List Loaded',
            'admin_list': admin_list
        }

        return make_response(jsonify(responseObject)), 200

    @requires_auth(allowed_roles=['is_superadmin'])
    def post(self):

        post_data = request.get_json()

        email = post_data.get('email')
        tier = post_data.get('tier')

        email_exists = EmailWhitelist.query.filter_by(email=email).first()

        if email_exists:
            response_object = {'message': 'Email already on whitelist.'}
            return make_response(jsonify(response_object)), 400

        if not (email or tier):
            response_object = {'message': 'No email or tier provided'}
            return make_response(jsonify(response_object)), 400

        user = EmailWhitelist(email=email,
                              tier=tier)

        db.session.add(user)
        db.session.commit()

        send_invite_email(email)

        responseObject = {
            'message': 'An invite has been sent!',
        }

        return make_response(jsonify(responseObject)), 200


    @requires_auth(allowed_roles=['is_superadmin'])
    def put(self):

        post_data = request.get_json()

        user_id = post_data.get('user_id')
        admin_tier = post_data.get('admin_tier')
        deactivated = post_data.get('deactivated', None)

        user = User.query.get(user_id)

        if not user:
            responseObject = {
                'status': 'fail',
                'message': 'User not found'
            }

            return make_response(jsonify(responseObject)), 401

        if admin_tier:
            user.set_admin_role_using_tier_string(admin_tier)

        if deactivated is not None:
            user.is_disabled = deactivated

        db.session.commit()

        responseObject = {
            'status': 'success',
            'message': 'Account status modified',
        }

        return make_response(jsonify(responseObject)), 200


class BlockchainKeyAPI(MethodView):

    @requires_auth(allowed_roles=['is_superadmin'])
    def get(self):

        responseObject = {
            'status': 'success',
            'message': 'Key loaded',
            'private_key': current_app.config['MASTER_WALLET_PRIVATE_KEY'],
            'address': current_app.config['MASTER_WALLET_ADDRESS']
        }

        return make_response(jsonify(responseObject)), 200


class KoboCredentialsAPI(MethodView):

    @requires_auth(allowed_roles=['is_admin'])
    def get(self):

        response_object = {
            'username': current_app.config['KOBO_AUTH_USERNAME'],
            'password': current_app.config['KOBO_AUTH_PASSWORD']
        }

        return make_response(jsonify(response_object)), 200

class TwoFactorAuthAPI(MethodView):
    @requires_auth
    def get(self):
        tfa_url = g.user.tfa_url
        responseObject = {
           'data': {"tfa_url": tfa_url}
        }

        return make_response(jsonify(responseObject)), 200

    @requires_auth(ignore_tfa_requirement = True)
    def post(self):
        request_data = request.get_json()
        user = g.user
        otp_token = request_data.get('otp')
        otp_expiry_interval = request_data.get('otp_expiry_interval')
        if user.validate_OTP(otp_token):
            tfa_auth_token = user.encode_TFA_token(otp_expiry_interval)
            user.TFA_enabled = True

            db.session.commit()

            if tfa_auth_token:
                auth_token = g.user.encode_auth_token()

                responseObject = create_user_response_object(user, auth_token, 'Successfully logged in.')

                responseObject['tfa_auth_token'] = tfa_auth_token.decode()

                return make_response(jsonify(responseObject)), 200

        responseObject = {
                            'status': "Failed",
                            'message': "Validation failed. Please try again."
                        }

        return make_response(jsonify(responseObject)), 400


# add Rules for API Endpoints

auth_blueprint.add_url_rule(
    '/auth/check_basic_auth/',
    view_func=CheckBasicAuth.as_view('check_basic_auth'),
    methods=['GET']
)

auth_blueprint.add_url_rule(
    '/auth/refresh_api_token/',
    view_func=RefreshTokenAPI.as_view('refresh_token_api'),
    methods=['GET']
)

auth_blueprint.add_url_rule(
    '/auth/register/',
    view_func=RegisterAPI.as_view('register_api'),
    methods=['POST']
)

auth_blueprint.add_url_rule(
    '/auth/request_api_token/',
    view_func=LoginAPI.as_view('login_api'),
    methods=['POST', 'GET']
)

auth_blueprint.add_url_rule(
    '/auth/logout/',
    view_func=LogoutAPI.as_view('logout_view'),
    methods=['POST']
)

auth_blueprint.add_url_rule(
    '/auth/activate/',
    view_func=ActivateUserAPI.as_view('activate_view'),
    methods=['POST']
)

auth_blueprint.add_url_rule(
    '/auth/reset_password/',
    view_func=ResetPasswordAPI.as_view('reset_view'),
    methods=['POST']
)

auth_blueprint.add_url_rule(
    '/auth/request_reset_email/',
    view_func=RequestPasswordResetEmailAPI.as_view('request_reset_email_view'),
    methods=['POST']
)

auth_blueprint.add_url_rule(
    '/auth/permissions/',
    view_func=PermissionsAPI.as_view('permissions_view'),
    methods=['POST', 'PUT', 'GET']
)

auth_blueprint.add_url_rule(
    '/auth/blockchain/',
    view_func=BlockchainKeyAPI.as_view('blockchain_view'),
    methods=['GET']
)

auth_blueprint.add_url_rule(
    '/auth/kobo/',
    view_func=KoboCredentialsAPI.as_view('kobo_view'),
    methods=['GET']
)

auth_blueprint.add_url_rule(
    '/auth/tfa/',
    view_func=TwoFactorAuthAPI.as_view('tfa_view'),
    methods=['GET','POST']
)