from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from auth.serializers import *
from auth.models import *
from auth.filters import UserFilter


class UserApi(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        '''
        :param request:
        :return: A json representation of all users
        '''

        users = User.objects.all()
        f = UserFilter(request.GET, queryset=users)
        serializer = UserSerializer(f.qs, many=True)
        return Response(serializer.data)

