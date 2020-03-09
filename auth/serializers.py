from rest_framework import serializers
from django.contrib.auth import get_user_model


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser', 'phone_number',
                  'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }
