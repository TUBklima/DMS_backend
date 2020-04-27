from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from auth.serializers import *
from auth.models import User
from auth.filters import UserFilter
from django.core import mail
from auth.tokens import Actions, ActivateUserTokenGenerator
from django.urls import reverse



class IsAuthenticatedOrReadOnly(BasePermission):
    """
    The request is authenticated as a user, or is a read-only request.
    """
    SAFE_METHODS = ['POST']

    def has_permission(self, request, view):
        if (request.method in IsAuthenticatedOrReadOnly.SAFE_METHODS or
            request.user and
            request.user.is_authenticated):
            return True
        return False


class UserApi(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request):
        '''
        :param request:
        :return: A json representation of all users
        '''

        users = User.objects.all()
        f = UserFilter(request.GET, queryset=users)
        serializer = UserSerializer(f.qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        us = UserSerializer(data=request.data, context={'request': request})
        if not us.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=us.errors)
        new_user = us.save()
        mail.send_mail("Account request on klima-dms",
                       "Your account was created successfully and is waiting for activation by an administrator.",
                       "dms@klima.tu-berlin.de",
                       [new_user.email]
                       )

        # generate tokens
        gen = ActivateUserTokenGenerator()
        activate_token = gen.make_token(new_user, Actions.ACTIVATE)
        decline_token = gen.make_token(new_user, Actions.DECLINE)

        # find admin mails
        admin_mails = User.objects.filter(is_superuser=True).values_list('email', flat=True)

        # generate user info
        user_info = ''
        for key, value in us.data.items():
            user_info += "\t" + str(key) + ":" + str(value) + "\n"

        bp = request.build_absolute_uri('/')
        mail.send_mail("Account request on klima-dms",
                       "A new account was requested. The user entered the following information: \n\n"
                       + user_info + "\n" +
                       "Click : " + bp + reverse('manageAccount',
                                                 kwargs={'token': activate_token}) + " to accept the request. \n"
                                                                                     "Click : " + bp + reverse(
                           'manageAccount', kwargs={'token': decline_token}) + " to decline the request. \n",
                       "dms@klima.tu-berlin.de",
                       admin_mails
                       )
        return Response(status=status.HTTP_201_CREATED, data=us.data)

    def patch(self, request):
        if 'id' in request.data:
            try:
                user = User.objects.get(id=request.data['id'])
            except ObjectDoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND, data={"Requested id not found"})
        else:
            user = request.user

        us = UserSerializer(user, data=request.data, partial=True, context={'request': request})
        if not us.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=us.errors)
        us.save()
        return Response(us.data)

class GroupView(ModelViewSet):
    serializer_class = GroupSerializer
    queryset = Group.objects.all()




@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def manage_account(request, token):
    if not token:
        Response(status=status.HTTP_400_BAD_REQUEST)
    gen = ActivateUserTokenGenerator()
    valid, pk, action = gen.check_token(token)
    if not valid:
        return Response(status=status.HTTP_400_BAD_REQUEST, data="Bad token")

    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if action == Actions.ACTIVATE:
        user.is_active = True
        user.save()
        us = UserSerializer(user)
        mail.send_mail("Account activated on klima-dms",
                       "Your account was activated. You can now login at : \n" +
                       reverse("login"),
                       "dms@klima.tu-berlin.de",
                       [user.email]
        )
        return Response(status=status.HTTP_200_OK, data=us.data)

    elif action == Actions.DECLINE:
        user_mail = user.email
        user.delete()
        mail.send_mail("Account request declined on klima-dms",
                       "Your account request was declined. We are sorry for this inconvenience."
                       "If you believe this is a mistake please get in touch with us.",
                       "dms@klima.tu-berlin.de",
                       [user_mail]
                       )
        return Response(status=status.HTTP_200_OK)
