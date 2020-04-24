from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

User = get_user_model()


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name']
        extra_kwargs = {
            'name': {'validators': []}
        }


class UserSerializer(serializers.ModelSerializer):
    superuser_fields = ['is_superuser', 'is_active']
    groups = GroupSerializer(many=True, write_only=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser', 'phone_number', 'is_active',
                  'password', 'groups']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        is_superuser = False
        if request and hasattr(request, "user"):
            if request.user.is_superuser:
                is_superuser = True

        if not is_superuser:
            for field in UserSerializer.superuser_fields:
                self.fields.pop(field)  # removing fields is easier than adding

    def create(self, validated_data):
        user_groups = None
        if 'groups' in validated_data:
            user_groups = validated_data.pop('groups')
        new_user = User.objects.create_user(**validated_data)
        if user_groups:
            for user_group in user_groups:
                # validated in validate groups
                gr = Group.objects.get(name=user_group['name'])
                new_user.groups.add(gr.id)
        return new_user

    def validate_groups(self, groups_data):
        query = Q()
        request_names = set()
        for gr in groups_data:
            if 'name' not in gr:
                raise ValidationError("Missing name attribute in group")
            if gr['name'] not in request_names:
                request_names.add(gr['name'])
                query |= Q(name=gr['name'])

        names = set(Group.objects.filter(query).values_list('name', flat=True))
        if len(names) != len(groups_data):
            missing = request_names - names
            raise ValidationError("Not all referenced groups exist. The missing groups are " + ",".join(missing))
        return groups_data

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
                if id_data != re_user.id:  # only super users can update other users
                    raise ValidationError("Can only update own user")
        return id_data


