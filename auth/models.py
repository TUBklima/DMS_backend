from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.auth.models import UserManager as DefaultUserManager
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


class UserManager(DefaultUserManager):

    @staticmethod
    def _add_default_group(user):
        # The default group 'users' ensures that logged in users can view public files.
        default_gr, created = Group.objects.get_or_create(name='users')
        user.groups.add(default_gr)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        user = super().create_superuser(username, email=email, password=password, **extra_fields)
        UserManager._add_default_group(user)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        '''
        New users are by default not active
        '''
        # Licence handling goes over the requested group -> 3DO can read Files licenced for 3DO
        # we have to check this here since _create_user uses self.model which refers to the original user model
        # a least thats what I think is happening
        if not email:
            raise ValidationError(message="An empty email field is not allowed")
        extra_fields.setdefault("is_active", False)
        user = super().create_user(username, email=email, password=password, **extra_fields)
        UserManager._add_default_group(user)
        return user


class User(AbstractUser):

    objects = UserManager()
    email = models.EmailField(blank=False, null=False)
    phone_number = models.CharField(max_length=30, blank=True, null=True)
