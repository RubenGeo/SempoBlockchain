from flask import current_app
from sqlalchemy import or_, and_, text
from server.models import TransferAccount, CreditTransfer, Feedback


def request_feedback_questions(user):
    questions = current_app.config['DEFAULT_FEEDBACK_QUESTIONS']
    balance_below_trigger = current_app.config['FEEDBACK_TRIGGERED_WHEN_BALANCE_BELOW']
    transfer_count_above_trigger = current_app.config['FEEDBACK_TRIGGERED_WHEN_TRANSFER_COUNT_ABOVE']
    if transfer_count_above_trigger == -1:
        # Makes it easy to disable the transfer count trigger by setting it to -1
        transfer_count_above_trigger = 999999999999

    if user.is_beneficiary and (user.transfer_account_id is not None):
        transfer_account = TransferAccount.query.get(user.transfer_account_id)

        transfer_number = CreditTransfer.query.filter(or_(CreditTransfer.recipient_transfer_account_id == user.transfer_account_id, CreditTransfer.sender_transfer_account_id == user.transfer_account_id)).count()

        feedback = Feedback.query.filter(and_(Feedback.transfer_account_id == user.transfer_account_id,
                                              Feedback.question.in_(questions))).first()

        if feedback is None and transfer_account.is_approved:

            if transfer_account.balance < balance_below_trigger or transfer_number > transfer_count_above_trigger:
                return questions

    return []
