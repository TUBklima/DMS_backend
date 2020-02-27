from urllib import response

from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from auth.models import *
import json

class UserTest(APITestCase):
    """
    Test user interactions
    """

    def setUp(self):
        self.user = User.objects.create_superuser(username='foo', email='foo@baa.de', first_name="foo",
                                                  last_name="baa", password="xxx")
        User.objects.create_user(username="Bob", password="Bob")


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
        self.assertEqual(len(response.data), 1, msg="Test expects just one user foo")
        self.assertEqual(response.data[0]['username'], 'foo')
