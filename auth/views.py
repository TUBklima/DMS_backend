from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, BasePermission
from auth.serializers import *
from auth.models import User
from auth.filters import UserFilter
from django.core import mail
from auth.tokens import Actions, ActivateUserTokenGenerator
from django.urls import reverse



class IsAuthenticatedOrPost(BasePermission):
    """
    The request is authenticated as a user, or is a read-only request.
    """
    SAFE_METHODS = ['POST']

    def has_permission(self, request, view):
        if (request.method in self.SAFE_METHODS or
            request.user and
            request.user.is_authenticated):
            return True
        return False


class UserApi(APIView):
    permission_classes = (IsAuthenticatedOrPost,)

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

class ActionBasedPermission(AllowAny):
    """
    Grant or deny access to a view, based on a mapping in view.action_permissions
    """
    def has_permission(self, request, view):
        for klass, actions in getattr(view, 'action_permissions', {}).items():
            if view.action in actions:
                return klass().has_permission(request, view)
        return False


class GroupView(ModelViewSet):
    serializer_class = GroupSerializer
    queryset = Group.objects.all()
    permission_classes = (ActionBasedPermission,)
    action_permissions = {
        IsAdminUser: ['update', 'partial_update', 'destroy', 'create', 'add_users', 'set_users', 'remove_users'],
        IsAuthenticated: ['list', 'retrieve']
    }

    def _get_user_by_request(self, data):

        request_ids = IdSerializer(data=data, many=True)
        if not request_ids.is_valid():
            raise ValidationError(request_ids.errors)

        request_ids = set([o['id'] for o in request_ids.validated_data])
        users = User.objects.filter(pk__in=request_ids)
        user_ids = set(users.values_list('id', flat=True))
        if request_ids != user_ids:
            missing_ids = request_ids - user_ids
            raise ValidationError("invalid user ids: "+",".join(missing_ids))

        return user_ids


    @action(detail=True, methods=['post'])
    def add_users(self, request, pk=None):
        try:
            gr = Group.objects.get(name=pk)
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data="requested group does not exist")

        try:
            user_ids = self._get_user_by_request(request.data)
        except ValidationError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=e.detail)

        users_in_group = set(gr.user_set.values_list('id', flat=True))
        add_user_ids = user_ids - users_in_group

        if len(add_user_ids) == 0:
            return Response(status=status.HTTP_208_ALREADY_REPORTED)

        for user_id in add_user_ids:
            gr.user_set.add(user_id)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def set_users(self, request, pk=None):
        try:
            gr = Group.objects.get(name=pk)
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data="requested group does not exist")

        try:
            user_ids = self._get_user_by_request(request.data)
        except ValidationError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=e.detail)

        users_in_group = set(gr.user_set.values_list('id', flat=True))
        if user_ids == users_in_group:
            return Response(status=status.HTTP_208_ALREADY_REPORTED)

        gr.user_set.set(user_ids)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def remove_users(self, request, pk=None):
        try:
            gr = Group.objects.get(name=pk)
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data="requested group does not exist")

        try:
            user_ids = self._get_user_by_request(request.data)
        except ValidationError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=e.detail)

        users_in_group = set(gr.user_set.values_list('id', flat=True))
        remove_users = user_ids.intersection(users_in_group)
        if len(remove_users) == 0:
            return Response(status=status.HTTP_208_ALREADY_REPORTED)

        for user_id in remove_users:
            gr.user_set.remove(user_id)
        return Response(status=status.HTTP_200_OK)

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
