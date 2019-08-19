import pytest

from flask import current_app
from server import create_app, db
# from app.manage import manager

# ---- https://www.patricksoftwareblog.com/testing-a-flask-application-using-pytest/
# ---- https://medium.com/@bfortuner/python-unit-testing-with-pytest-and-mock-197499c4623c


@pytest.fixture(scope='function')
def requires_auth(test_client):
    from server.utils.auth import requires_auth
    return requires_auth


@pytest.fixture(scope='function')
def new_admin_user():
    from server.models import User
    user = User()
    user.create_admin_auth(email='tristan@sempo.ai', password='TestPassword')
    return user


@pytest.fixture(scope='function')
def create_admin_user(test_client, init_database, new_admin_user):
    db.session.add(new_admin_user)

    # Commit the changes for the users
    db.session.commit()
    return new_admin_user


@pytest.fixture(scope='module')
def create_transfer_account_user(test_client, init_database):
    from server.utils.user import create_transfer_account_user
    user = create_transfer_account_user(first_name='Tristan', last_name='Cole', phone='0401391419')
    db.session.commit()
    return user


@pytest.fixture(scope='module')
def create_user_with_existing_transfer_account(test_client, init_database, create_transfer_account):
    from server.utils.user import create_transfer_account_user
    user = create_transfer_account_user(first_name='Tristan', last_name='Cole',
                                        phone='0401391419', existing_transfer_account=create_transfer_account)
    db.session.commit()
    return user


@pytest.fixture(scope='module')
def new_transfer_account():
    from server.models import TransferAccount
    return TransferAccount()


@pytest.fixture(scope='module')
def create_transfer_account(new_transfer_account):
    db.session.add(new_transfer_account)
    db.session.commit()
    return new_transfer_account

@pytest.fixture(scope='module')
def new_disbursement(create_transfer_account_user):
    from server.utils.credit_transfers import make_disbursement_transfer
    disbursement = make_disbursement_transfer(100,create_transfer_account_user)
    return disbursement

@pytest.fixture(scope='function')
def new_credit_transfer(create_transfer_account_user):
    from server.models import CreditTransfer
    credit_transfer = CreditTransfer(
        amount=100, sender=create_transfer_account_user, recipient=create_transfer_account_user)
    return credit_transfer

@pytest.fixture(scope='function')
def new_credit_transfer(create_transfer_account_user):
    from server.models import CreditTransfer
    credit_transfer = CreditTransfer(
        amount=100, sender=create_transfer_account_user, recipient=create_transfer_account_user)
    return credit_transfer


@pytest.fixture(scope='function')
def create_credit_transfer(new_credit_transfer):
    db.session.add(new_credit_transfer)
    db.session.commit()
    return new_credit_transfer


@pytest.fixture(scope='function')
def proccess_phone_number(test_client):
    from server.utils.phone import proccess_phone_number
    return proccess_phone_number


@pytest.fixture(scope='function')
def save_device_info(test_client, init_database, create_transfer_account_user):
    from server.utils.user import save_device_info
    return save_device_info


@pytest.fixture(scope='function')
def create_blacklisted_token(create_admin_user):
    from server.models import BlacklistToken
    auth_token = create_admin_user.encode_auth_token().decode()
    blacklist_token = BlacklistToken(token=auth_token)
    db.session.add(blacklist_token)
    db.session.commit()
    return blacklist_token


@pytest.fixture(scope='function')
def create_transfer_usage(test_client, init_database):
    from server.models import TransferUsage
    transfer_usage = TransferUsage(name='Food', icon='food-apple', translations=dict(en='Food', fr='aliments'))

    db.session.add(transfer_usage)
    db.session.commit()
    return transfer_usage


@pytest.fixture(scope='function')
def create_ip_address(create_admin_user):
    from server.models import IpAddress
    ip_address = IpAddress(ip="210.18.192.196")
    ip_address.user = create_admin_user
    db.session.add(ip_address)
    db.session.commit()
    return ip_address


@pytest.fixture(scope='module')
def test_request_context():
    flask_app = create_app()

    # can be used in combination with the WITH statement to activate a request context temporarily.
    # with this you can access the request, g and session objects in view functions
    yield flask_app.test_request_context


@pytest.fixture(scope='module')
def test_client():
    flask_app = create_app()

    # Flask provides a way to test your application by exposing the Werkzeug test Client
    # and handling the context locals for you.
    testing_client = flask_app.test_client()

    # Establish an application context before running the tests.
    ctx = flask_app.app_context()
    ctx.push()

    yield testing_client  # this is where the testing happens!

    ctx.pop()


@pytest.fixture(scope='module')
def init_database():
    # Create the database and the database table

    with current_app.app_context():
        db.create_all()  # todo- use manage.py

    yield db  # this is where the testing happens!

    with current_app.app_context():
        db.session.close_all()  # DO NOT DELETE THIS LINE. We need to close sessions before dropping tables.
        db.drop_all()
