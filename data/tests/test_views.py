# test_views.py

import os

from django.core.handlers.wsgi import WSGIRequest
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from auth.models import User
from dms_backend import settings

import uc2data
from pathlib import Path

from .. import views


class TestFileView(APITestCase):
    file_dir = Path(__file__).parent / "test_files"

    def setUp(self):
        self.user = User.objects.create_superuser(username="TestUser", email="test@user.com", password="test")
        self.view = views.FileView.as_view()
        self.factory = APIRequestFactory()

    def _get_request(self, filename, user=None, ignore_warnings=None, ignore_errors=None):
        testfile_path = self.file_dir / Path(filename)
        data = {'file_type': 'UC2'}
        if ignore_warnings:
            data['ignore_warnings'] = ignore_warnings
        if ignore_errors:
            data['ignore_errors'] = ignore_errors
        with open(testfile_path, "rb") as testfile:
            data['file'] = testfile
            req = self.factory.post(
                "/uc2upload/",
                data=data
            )
        if user:
            req.user = user
        else:
            req.user = self.user
        return req

    def test_that_authentication_is_required(self):
        self.assertEqual(self.client.post("/uc2upload/").status_code, status.HTTP_401_UNAUTHORIZED, "Should require Authentication")

    def test_post_bad_file(self):

        req = self._get_request("bad_format_file.nc", ignore_errors=False, ignore_warnings=False)
        resp = self.view(req)

        self.assertEqual(resp.data['status'], uc2data.ResultCode.ERROR, "uc2check should result in errors")
        self.assertEqual(resp.status_code, status.HTTP_406_NOT_ACCEPTABLE)

    def test_post_good_file(self):

        req = self._get_request("good_format_file.nc")
        resp = self.view(req)

        self.assertEqual(resp.data['status'], uc2data.ResultCode.OK)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, "Should create a database entry!")

        req2 = self._get_request("good_format_file.nc")
        resp2 = self.view(req2)
        self.assertEqual(resp2.status_code, status.HTTP_406_NOT_ACCEPTABLE, "Entry should already exist")

