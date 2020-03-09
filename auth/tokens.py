from datetime import date

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import base36_to_int, int_to_base36, urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from enum import Enum


class Actions(Enum):
    ACTIVATE = 0
    DECLINE = 1


class ActivateUserTokenGenerator(PasswordResetTokenGenerator):
    """
    Strategy object used to generate and check tokens which either activate or deactivate a user.

    This follows the basic ideas of django.contrib.auth.tokens.PasswordResetTokenGenerator except it also
    encodes the user and the action to take (activate or deactivate)
    """

    key_salt = "auth.tokens.ActivateUserTokenGenerator"
    secret = settings.SECRET_KEY

    def make_token(self, user, action):
        """
        Return a token that can be used to activate or deactivate the
        given user
        """
        if action not in Actions:
            raise ValueError("Action must be Actions.ACTIVATE or Actions.DEACTIVATE")

        return self._make_token_with_timestamp(user.pk, self._num_days(self._today()), action)

    def check_token(self, token):
        """
        Check that a token is correct. Return the encoded user_pk and action.
        """
        invalid_return = (False, None, None)
        if not token:
            return invalid_return
        # Parse the token
        try:
            pk_b64, action_value, ts_b36, _ = token.split("-")
            pk = urlsafe_base64_decode(pk_b64).decode("UTF-8")
            action = Actions(int(action_value))
            ts = base36_to_int(ts_b36)
        except ValueError:
            return invalid_return

        # Check that the pk/timestamp/action has not been tampered with
        if not constant_time_compare(self._make_token_with_timestamp(pk, ts, action), token):
            return invalid_return

        try:
            timeout = settings.ACTIVATE_USER_TIMEOUT_DAYS
        except AttributeError:
            # if no special timeout is set use the PW reset timeout
            timeout = settings.PASSWORD_RESET_TIMEOUT_DAYS

        # Check the timestamp is within limit. Timestamps are rounded to
        # midnight (server time) providing a resolution of only 1 day. If a
        # link is generated 5 minutes before midnight and used 6 minutes later,
        # that counts as 1 day. Therefore, PASSWORD_RESET_TIMEOUT_DAYS = 1 means
        # "at least 1 day, could be up to 2."
        if (self._num_days(self._today()) - ts) > timeout:
            return invalid_return

        return True, pk, action


    def _make_token_with_timestamp(self, user_pk, timestamp, action):
        # timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        ts_b36 = int_to_base36(timestamp)
        # convert the user pk to bytes. We can not assume it will always be an int
        pk_byte = str(user_pk).encode('UTF-8')
        # convert the byte representation to something that can be printed in an url
        pk_b64 = urlsafe_base64_encode(pk_byte)
        hash_string = salted_hmac(
            self.key_salt,
            self._make_hash_value(user_pk, timestamp, action),
            secret=self.secret,
        ).hexdigest()[::2]  # Limit to 20 characters to shorten the URL.
        return "%s-%i-%s-%s" % (pk_b64, action.value, ts_b36, hash_string)

    def _make_hash_value(self, user_pk, timestamp, action):
        """
        In contrast to the implementation in django.contrib.auth.tokens.PasswordResetTokenGenerator we can not ensure
        each token is only used once. However, the actions we take here are a lot less sensitive the password reset.
        """
        return str(user_pk) + str(action.value) + str(timestamp)