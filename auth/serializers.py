from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from data.models import Institution

User = get_user_model()


class IdSerializer(serializers.Serializer):
    id = serializers.IntegerField()


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name']
        extra_kwargs = {
            'name': {'validators': []}
        }


class UserSerializer(serializers.ModelSerializer):
    superuser_fields = ['is_superuser', 'is_active']
    groups = GroupSerializer(many=True, write_only=False, required=False)
    institutions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser', 'phone_number', 'is_active',
                  'password', 'groups', 'institutions']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        self.is_superuser = False
        if request and hasattr(request, "user"):
            if request.user.is_superuser:
                self.is_superuser = True

        if not self.is_superuser:
            for field in UserSerializer.superuser_fields:
                self.fields.pop(field)  # removing fields is easier than adding

    def get_institutions(self, obj):
        groups = obj.groups.all().values_list('name', flat=True)
        if groups:
            return list(Institution.objects.filter(acronym__in=groups).values_list('acronym', flat=True))
        else:
            return []

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

    def update(self, instance, validated_data):
        update_groups = None
        if 'groups' in validated_data:
            request_groups = set([gr['name'] for gr in validated_data.pop('groups')])
            query = Q()
            for name in request_groups:
                query |= Q(name=name)
            update_groups = list(Group.objects.filter(query))

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if update_groups is not None:
            instance.groups.set(update_groups)
        instance.save()
        return instance


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

        if self.instance:
            user_groups = set(self.instance.groups.values_list('name', flat=True))
            if not self.is_superuser and request_names != user_groups:
                raise ValidationError("Only a superuser can update groups")
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


