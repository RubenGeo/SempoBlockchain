class IconNotSupportedException(Exception):
    """
    Raise if trying to set TransferUsage to an icon not supported on mobile (currently only MaterialCommunityIcons)
    """

class TypeNotFoundException(Exception):
    """
    Raise if trying to set kyc application type to type that does not exist
    """
    pass

class TierNotFoundException(Exception):
    """
    Raise if trying to set user role to tier that does not exist
    """
    pass

class InvalidTransferTypeException(Exception):
    """
    Raise if the transfer type string isn't one of the enumerated transfer types
    """
    pass

class InsufficientBalanceException(Exception):
    """
    Raise if the transfer account doesn't have sufficient balance to make the transfer
    """
    pass


class NoTransferAccountError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class InsufficientBalanceError(Exception):
    pass


class AccountNotApprovedError(Exception):

    def __init__(self, message, is_sender=None):
        self.message = message
        self.is_sender = is_sender

    def __repr__(self):
        return self.message


class InvalidTargetBalanceError(Exception):
    pass


class BlockchainError(Exception):
    pass


class NoTransferCardError(Exception):
    pass