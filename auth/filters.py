import django_filters
from auth.models import User


class UserFilter(django_filters.FilterSet):
    class Meta:
        model = User
        fields = ['username', 'id']
