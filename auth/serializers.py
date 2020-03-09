from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser', 'phone_number',
                  'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_id(self, id_data):
        re_user = None
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            re_user = request.user
        if not re_user:
            raise ValidationError("User must be logged in")
        if self.instance:
            # update existing user
            if not re_user.is_superuser:
                if id_data != re_user.id:
                    raise ValidationError("Can only update own user")
        return id_data
