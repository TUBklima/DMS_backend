# test_views.py

import os

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

    def test_that_authentication_is_required(self):
        assert self.client.post("/uc2upload/").status_code == status.HTTP_401_UNAUTHORIZED

    def test_post_bad_file(self):
        testfile_path = self.file_dir / Path("bad_format_file.nc")
        with open(testfile_path, "rb") as testfile:
            req = self.factory.post(
                "/uc2upload/",
                data={"file": testfile,
                      "file_type": "UC2",
                      "ignore_warnings": False,
                      "ignore_errors": False
                      }
            )
        req.user = self.user
        resp = self.view(req)

        self.assertEqual(resp.data['status'], uc2data.ResultCode.ERROR, "uc2check should result in errors")
        self.assertEqual(resp.status_code, status.HTTP_406_NOT_ACCEPTABLE)

    def test_post_good_file(self):

        testfile_path = self.file_dir / Path("good_format_file.nc")

        with open(testfile_path, "rb") as testfile:
            req = self.factory.post(
                "/uc2upload/",
                data={"file": testfile,
                      "file_type": "UC2"
                      },
            )
        req.user = self.user
        resp = self.view(req)

        self.assertEqual(resp.data['status'], uc2data.ResultCode.OK)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, "Should create a database entry!")
        resp2 = self.view(req)
        self.assertEqual(resp2.status_code, status.HTTP_406_NOT_ACCEPTABLE, "Entry should already exist")
