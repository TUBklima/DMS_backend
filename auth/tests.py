from urllib import response

from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from auth.models import *
import json
import re
from django.core import mail


class UserTest(APITestCase):
    """
    Test user interactions
    """

    def setUp(self):
        self.user = User.objects.create_superuser(username='foo', email='foo@baa.de', first_name="foo",
                                                  last_name="baa", password="xxx")
        User.objects.create_user(username="Bob", password="Bob", email="bob@baa.de")

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
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_users(self):
        self.client.force_login(self.user)
        url = reverse('users')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_users(self):
        self.client.force_login(self.user)
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
                                        'password': 'xxx'
                                    }),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg="missing email field")
        # account request
        response = self.client.post(url,
                                    data=json.dumps({
                                        'username': 'balu',
                                        'password': 'xxx',
                                        'email': 'balu@foo.de'
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

    def test_account_decline(self):

        url = reverse("requestAccount")
        self.client.post(url,
                        data=json.dumps({
                            'username': 'evil',
                            'password': 'xxx',
                            'email': 'evil@foo.de'
                        }),
                        content_type='application/json')
        decline_link = re.search('(http://testserver/)(.*?)( .*decline)', mail.outbox[1].body).group(2)
        response = self.client.get(decline_link)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(mail.outbox), 2)  # mail was send
        self.assertTrue('Account request declined' in mail.outbox[2].subject)

