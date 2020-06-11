from urllib import response

from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from auth.models import *
import json
import re
from django.core import mail
from django.contrib.auth.models import Group
from auth.views import GroupView
class UserTest(APITestCase):
    """
    Test user interactions
    """

    def setUp(self):
        test_group = Group.objects.create(name="test")

        User.objects.create_superuser(username='foo', email='foo@baa.de', first_name="foo",
                                                         last_name="baa", password="xxx")
        self.in_active_user = User.objects.create_user(username="Bob", password="Bob", email="bob@baa.de")
        self.active_user = User.objects.create_user(username="eve", password="eve", email="eve@baa.de", is_active=True)
        test_group.user_set.add(self.active_user)

    def test_login(self):
        """
        Test if an existing user can login

        :return: None
        """
        url = reverse("login")
        response = self.client.get(url)
        # must use post to send data
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        response = self.client.post(url,
                                    data=json.dumps({
                                        'username': 'foo',
                                        'password': 'xxx'
                                    }),
                                    content_type='application/json')
        user = User.objects.get(username='foo')
        # TODO: fill with test values from kb
        user.password = 'xx'
        user.save()
        response = self.client.post(url,
                                    data=json.dumps({
                                        'username': 'foo',
                                        'password': 'asdasd'
                                    }),
                                    content_type='application/json')
        # self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_users(self):
        self.client.force_login(self.active_user)
        url = reverse('users')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_user(self):
        self.client.force_login(self.active_user)
        url = reverse('users')
        response = self.client.patch(url,
                                   data=json.dumps({
                                       'first_name': "xxx"
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        u = User.objects.get(pk=self.active_user.pk)
        self.assertEqual(u.first_name, "xxx")

    def test_filter_users(self):
        self.client.force_login(self.active_user)
        url = reverse('users')
        response = self.client.get(url+"?username=foo")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['username'], 'foo')

    def test_default_is_not_active(self):
        bob = User.objects.get(username='Bob')
        self.assertFalse(bob.is_active, msg="New users should be in_active by default")
        foo = User.objects.get(username='foo')
        self.assertTrue(foo.is_active, msg="New superusers are active by default") # otherwise we could never lock in the first time

    def test_account_request(self):
        url = reverse("requestAccount")
        response = self.client.post(url,
                                    data=json.dumps({
                                        'username': 'balu',
                                        'password': 'xxx',
                                    }),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg="missing email field")
        # account request
        response = self.client.post(url,
                                    data=json.dumps({
                                        'username': 'balu',
                                        'password': 'xxx',
                                        'email': 'balu@foo.de',
                                        'groups': [{'name': "test"}]
                                    }),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'balu')
        self.assertGreater(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].body,
                         'Your account was created successfully and is waiting for activation by an administrator.')

        # accept account
        accept_link = re.search('(http://testserver/)(.*?)( .*accept)', mail.outbox[1].body).group(2)
        response = self.client.get(accept_link)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(mail.outbox), 2)  # mail was send
        self.assertTrue('Account activated' in mail.outbox[2].subject)
        test_user = User.objects.get(pk=response.data['id'])
        self.assertTrue(test_user.is_active)

        #test without groups
        response = self.client.post(url,
                                    data=json.dumps({
                                        'username': 'balu2',
                                        'password': 'xxx',
                                        'email': 'balu2@foo.de',
                                    }),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


    def test_account_decline(self):

        url = reverse("requestAccount")
        response = self.client.post(url,
                        data=json.dumps({
                            'username': 'evil',
                            'password': 'xxx',
                            'email': 'evil@foo.de'
                        }),
                        content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        decline_link = re.search('(http://testserver/)(.*?)( .*decline)', mail.outbox[1].body).group(2)
        response = self.client.get(decline_link)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(mail.outbox), 2)  # mail was send
        self.assertTrue('Account request declined' in mail.outbox[2].subject)


class GroupTest(APITestCase):

    def setUp(self):
        self.test_group = Group.objects.create(name="test")
        self.test_group2 = Group.objects.create(name="test2")

        self.super_user = User.objects.create_superuser(username='foo', email='foo@baa.de', first_name="foo",
                                                         last_name="baa", password="xxx")
        self.in_active_user = User.objects.create_user(username="Bob", password="Bob", email="bob@baa.de")
        self.active_user = User.objects.create_user(username="eve", password="eve", email="eve@baa.de", is_active=True)
        self.test_group.user_set.add(self.active_user)

    def test_group_create(self):
        self.client.force_login(self.super_user)
        url = reverse('group-list')
        response = self.client.post(url, data=json.dumps({
            'name': 'new_group'
        }), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_set_users(self):
        url = reverse('group-set-users', args=["test"])
        self.client.force_login(self.super_user)

        ids = set(self.test_group.user_set.values_list('id', flat=True))
        self.assertEqual(ids, {self.active_user.id}, 'Test assumption broken in setUp?')
        response = self.client.post(url, data=json.dumps([
            {
                'id': self.super_user.id
            }
        ]), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = set(self.test_group.user_set.values_list('id', flat=True))
        self.assertEqual(ids, {self.super_user.id})

    def test_remove_users(self):
        url = reverse('group-remove-users', args=["test"])
        self.client.force_login(self.super_user)

        ids = set(self.test_group.user_set.values_list('id', flat=True))
        self.assertEqual(ids, {self.active_user.id}, 'Test assumption broken in setUp?')
        response = self.client.post(url, data=json.dumps([
            {
                'id': self.active_user.id
            }
        ]), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = set(self.test_group.user_set.values_list('id', flat=True))
        self.assertEqual(len(ids), 0)

    def test_add_users(self):
        url = reverse('group-add-users', args=["test2"])

        # Test that only super users can add users to groups
        self.client.force_login(self.active_user)
        response = self.client.post(url, data=json.dumps([
            {
                'id': self.active_user.id
            },
            {
                'id': self.super_user.id
            }
        ]), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_login(self.super_user)
        # Adding a user which is already there
        already = reverse('group-add-users', args=["test"])
        response = self.client.post(already, json.dumps([
            {
                'id': self.active_user.id
            }
        ]), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_208_ALREADY_REPORTED)
        # Test user add

        response = self.client.post(url, data=json.dumps([
            {
                'id': self.active_user.id,
                'username': self.active_user.username

            },
            {
                'id': self.super_user.id
            },
            {
                'id': self.super_user.id  # same id multiple times is ignored
            }
        ]), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        test2_users = Group.objects.get(name='test2').user_set.values_list('id', flat=True)
        self.assertEqual(set(test2_users), {self.active_user.id, self.super_user.id} )

    def test_user_update_group(self):
        self.client.force_login(self.super_user)
        url = reverse('users')
        id = self.active_user.id
        response = self.client.patch(url, data=json.dumps({
            'id': id,
            'groups': [{'name': 'test'}, {'name': 'test2'}]
        }), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(id=self.active_user.id)
        names = list(user.groups.values_list("name", flat=True))
        self.assertEqual(names, ["test", "test2"])

        response = self.client.patch(url, data=json.dumps({
            'id': id,
            'groups': [{'name': 'test'}]
        }), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(id=self.active_user.id)
        names = list(user.groups.values_list("name", flat=True))
        self.assertEqual(names, ["test"], "Overwrite did not work")

    def test_group_get(self):
        self.client.force_login(self.active_user)
        url = reverse('group-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_create_group(self):
        self.client.force_login(self.active_user)
        url = reverse("requestAccount")
        response = self.client.post(url,
                                    data=json.dumps({
                                        'username': 'balu',
                                        'password': 'xxx',
                                        'email': 'balu@foo.de',
                                        'groups': [{'name': "test3"}, {'name': "test"}]
                                    }),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, "Can't assign an not existing group to a user.")

        response = self.client.post(url,
                                    data=json.dumps({
                                        'username': 'balu',
                                        'password': 'xxx',
                                        'email': 'balu@foo.de',
                                        'groups': [{'name': "test"}]
                                    }),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        eve = User.objects.get(username='eve')
        self.assertEqual(list(eve.groups.values_list('name', flat=True)), ['test', 'users'])


