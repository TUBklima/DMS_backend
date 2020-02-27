from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DefaultUserManager
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


class UserManager(DefaultUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        '''
        New users are by default not active
        '''
        # we have to check this here since _create_user uses self.model which refers to the original user model
        # a least thats what I think is happening
        if not email:
            raise ValidationError(message="An empty email field is not allowed")
        extra_fields.setdefault("is_active", False)
        return super().create_user(username, email, password=None, **extra_fields)


class User(AbstractUser):
    # TODO: add institution foreign key
    objects = UserManager()
    email = models.EmailField(blank=False, null=False)

    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True)  # validators should be a list
