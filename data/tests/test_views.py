# test_views.py

import os

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from auth.models import User
from dms_backend import settings

from .. import views

pytestmark = pytest.mark.django_db


class TestFileView(APITestCase):
    def setUp(self):
        self.tearDown()
        self.user = User.objects.create_superuser(username="TestUser", email="test@user.com", password="test")
        self.view = views.FileView.as_view({"post": "create"})
        self.factory = APIRequestFactory()

    def test_that_authentication_is_required(self):
        self.assertEqual(self.client.post("/uc2upload/").status_code, status.HTTP_401_UNAUTHORIZED, "Should require Authentication")

    def test_post_bad_file(self):
        testfile = os.path.join(settings.MEDIA_ROOT, "bad_format_file.nc")
        req = self.factory.post(
            "/uc2upload/",
            data={"file": open(testfile, "rb"), "version": 1, "data_type": "UC2Observation"},
            # content_type="multipart/form-data",
        )
        req.user = self.user
        resp = self.view(req)

        self.assertEqual(resp.data["uc2resultcode"], 1, "error code should be 1, uc2check should have resulted in errors")
        self.assertEqual(status.HTTP_406_NOT_ACCEPTABLE, resp.status_code, "Should reject because of bad uc2check!")

    def test_post_good_file(self):
        testfile = os.path.join(settings.MEDIA_ROOT, "good_format_file.nc")
        req = self.factory.post(
            "/uc2upload/",
            data={"file": open(testfile, "rb"), "version": 1, "data_type": "UC2Observation"},
            # content_type="multipart/form-data",
        )
        req.user = self.user
        resp = self.view(req)

        assert resp.data["uc2resultcode"] in [0, 2], "error code should be 0 or 2 (warnings)"
        assert status.HTTP_201_CREATED == resp.status_code, "Should create a database entry!"
        resp2 = self.view(req)
        assert status.HTTP_406_NOT_ACCEPTABLE == resp2.status_code, "Entry should already exist"
