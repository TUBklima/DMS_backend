from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
import bcrypt

User = get_user_model()


class KBBackend(BaseBackend):
    """
    This class allows the usage of legacy passwords from the kb
    """
    def authenticate(self, request, username=None, password=None):
        if not username and password:
            return None

        user = list(User.objects.filter(username=username, is_active=True))
        if len(user) != 1:
            return None
        if not bcrypt.checkpw(password.encode('utf8'), user[0].password.encode('utf8')):
            return None
        return user[0]
