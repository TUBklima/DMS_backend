# test_views.py

import os

from django.core.handlers.wsgi import WSGIRequest
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from data.models import UC2Observation
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
        assert self.client.post("/uc2upload/").status_code == status.HTTP_401_UNAUTHORIZED

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

    def test_version(self):
        req = self._get_request("good_format_file_v2.nc")
        resp = self.view(req)

        self.assertEqual(resp.data['status'], uc2data.ResultCode.ERROR)
        self.assertEqual(resp.status_code, status.HTTP_406_NOT_ACCEPTABLE, "Version 2 with no version 1 should be an error")

        req = self._get_request("good_format_file.nc")
        resp = self.view(req)
        self.assertEqual(resp.data['status'], uc2data.ResultCode.OK)

        req2 = self._get_request("good_format_file.nc")
        resp2 = self.view(req2)
        self.assertEqual(resp2.status_code, status.HTTP_406_NOT_ACCEPTABLE, "Posting the same version again is an error")

        req = self._get_request("good_format_file_v2.nc")
        resp = self.view(req)

        self.assertEqual(resp.data['status'], uc2data.ResultCode.OK)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, "V1 exist so we can upload v2")

        p = self.file_dir / "good_format_file.nc"
        uc2ds = uc2data.Dataset(p)
        fname = uc2ds.filename

        old_version = UC2Observation.objects.get(file_standard_name=fname)
        self.assertTrue(old_version.is_old)

    def test_set_invalid(self, user=None):
        #  check if data base has entries
        if not UC2Observation.objects.all().exists():
            self.test_post_good_file()
        p = self.file_dir / "good_format_file.nc"
        uc2ds = uc2data.Dataset(p)
        fname = uc2ds.filename
        entry = UC2Observation.objects.get(file_standard_name=fname)
        self.assertFalse(entry.is_invalid, "Entry should not be invalid before update")

        data = {'is_invalid': 1, 'file_standard_name': fname}
        req = self.factory.patch("/uc2upload/", data=data)
        if user:
            req.user = user
        else:
            req.user = self.user
        resp = self.view(req)
        self.assertEqual(resp.status_code, status.HTTP_205_RESET_CONTENT, 'Should update content')

        entry = UC2Observation.objects.get(file_standard_name=fname)
        self.assertTrue(entry.is_invalid, "Entry should be invalid")
