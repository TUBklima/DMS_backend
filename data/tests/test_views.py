# test_views.py

import os

from django.core.handlers.wsgi import WSGIRequest
from django.contrib.auth.models import Group, AnonymousUser


from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from data.models import *
from auth.models import User

from data.serializers import *
from guardian.shortcuts import get_objects_for_user

from django.urls import reverse

from dms_backend import settings

import uc2data
from pathlib import Path
import json

from .. import views
from django.core.management import call_command
import io


def make_fixture(path, model_str, ignore_pk=True, ignore_fields=None, append=False):
    mode = 'w'
    if append:
        mode = 'a'

    with io.StringIO() as out:
        call_command('dumpdata', model_str, '--natural-primary', '--natural-foreign', stdout=out)
        text = out.getvalue()

    dc = json.loads(text)
    for elm in dc:
        if ignore_pk:
            elm.pop('pk')
        for key, item in elm['fields'].items():
            if ignore_fields and key in ignore_fields:
                elm['fields'].pop('key')

    with open(path, mode, encoding='utf-8') as f:
        json.dump(dc, f, indent=4, ensure_ascii=False)


class TestFileView(APITestCase):
    file_dir = Path(__file__).parent / "test_files"
    fixtures = ['groups_and_licenses.json', 'data/tests/fixtures/institutions.json', 'data/tests/fixtures/variables.json']

    def setUp(self):
        self.super_user = User.objects.create_superuser(username="TestUser", email="test@user.com", password="test")
        self.user = User.objects.create_user(username="TestUser2", email="test@user2.com", password="test")
        self.user_3do = User.objects.create_user("test3", email="foo@baa.de", password="xxx", is_active=True)

        gr = Group.objects.get(name="3DO")
        self.user_3do.groups.add(gr)

        self.view = views.FileView.as_view()
        self.factory = APIRequestFactory()

    def _build_post_request(self, filename, user=None, ignore_warnings=None, ignore_errors=None):
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
            req.user = self.super_user
        return req

    def _build_patch_request(self, data, user=None):
        req = self.factory.patch(
            "/uc2upload/",
            data=data
        )
        if user:
            req.user = user
        else:
            req.user = self.super_user
        return req

    def _build_get_request(self, data, user=None):
        req = self.factory.get("/uc2upload/", data=data)
        if user:
            req.user = user
        else:
            req.user = self.super_user
        return req

    def test_that_authentication_is_required(self):
        assert self.client.post("/uc2upload/").status_code == status.HTTP_401_UNAUTHORIZED

    def test_post_bad_file(self):

        req = self._build_post_request("bad_format_file.nc", ignore_errors=False, ignore_warnings=False)
        resp = self.view(req)

        self.assertEqual(resp.data['status'], uc2data.ResultCode.FATAL.value, "uc2check should result in errors")
        self.assertEqual(resp.status_code, status.HTTP_406_NOT_ACCEPTABLE)

    def test_post_good_file(self):
        req = self._build_post_request("good_format_file.nc", user=self.user_3do)
        resp = self.view(req)

        self.assertEqual(resp.data['status'], uc2data.ResultCode.OK.value)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, "Should create a database entry!")
        obj = get_objects_for_user(self.user_3do, 'view_uc2observation', klass=UC2Observation)
        self.assertEqual(obj[0].file_standard_name, 'LTO-B-bamberger-TUBklima-plev-20150401-001.nc')
        obj = get_objects_for_user(self.user, 'view_uc2observation', klass=UC2Observation)
        self.assertFalse(obj.exists())

    def test_version(self):
        req = self._build_post_request("good_format_file_v2.nc")
        resp = self.view(req)

        self.assertEqual(resp.data['status'], uc2data.ResultCode.ERROR.value)
        self.assertEqual(resp.status_code, status.HTTP_406_NOT_ACCEPTABLE, "Version 2 with no version 1 should be an error")

        req = self._build_post_request("good_format_file.nc")
        resp = self.view(req)
        self.assertEqual(resp.data['status'], uc2data.ResultCode.OK.value)

        req2 = self._build_post_request("good_format_file.nc")
        resp2 = self.view(req2)
        self.assertEqual(resp2.status_code, status.HTTP_406_NOT_ACCEPTABLE, "Posting the same version again is an error")

        req = self._build_post_request("good_format_file_v2.nc")
        resp = self.view(req)

        self.assertEqual(resp.data['status'], uc2data.ResultCode.OK.value)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, "V1 exist so we can upload v2")

        p = self.file_dir / "good_format_file.nc"
        uc2ds = uc2data.Dataset(p)
        fname = uc2ds.filename

        old_version = UC2Observation.objects.get(file_standard_name=fname)
        self.assertTrue(old_version.is_old)

    def test_set_invalid(self):
        #  check if data base has entries
        if not UC2Observation.objects.all().exists():
            self.test_post_good_file()

        p = self.file_dir / "good_format_file.nc"
        uc2ds = uc2data.Dataset(p)
        fname = uc2ds.filename
        entry = UC2Observation.objects.get(file_standard_name=fname)
        self.assertFalse(entry.is_invalid, "Entry should not be invalid before update")

        # false patch requests
        for val in ["0", 0, False, "False", "FALSE", "no"]:
            data = {'is_invalid': val, 'file_standard_name': fname}
            req = self._build_patch_request(data)
            resp = self.view(req)
            self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, 'Patch method should not be available for this data')
            entry = UC2Observation.objects.get(file_standard_name=fname)
            self.assertFalse(entry.is_invalid, "Entry should still be invalid")

        data = {'is_invalid': val, 'file_standard_name': fname}
        req = self._build_patch_request(data)
        resp = self.view(req)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED,
                         'Patch method should not be available with this request')
        entry = UC2Observation.objects.get(file_standard_name=fname)
        self.assertFalse(entry.is_invalid, "Entry should still be valid")

        # correct patch requests
        for val in ["1", 1, True, "True", "TRUE", "yes"]:
            data = {'is_invalid': val, 'file_standard_name': fname}
            req = self._build_patch_request(data)
            resp = self.view(req)
            self.assertEqual(resp.status_code, status.HTTP_205_RESET_CONTENT, 'Should update content')
            entry = UC2Observation.objects.get(file_standard_name=fname)
            self.assertTrue(entry.is_invalid, "Entry should be invalid")

        # unauthorized user requests
        data = {'is_invalid': val, 'file_standard_name': fname}
        req = self._build_patch_request(data, user=self.user)
        resp = self.view(req)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED, 'User is neither uploader nor superuser')

        # patch wrong field requests
        # TODO: Should superuser be able to patch any field?
        data = {'acronym': val, 'file_standard_name': fname}
        req = self._build_patch_request(data)
        resp = self.view(req)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, 'Method should only is_invalid should be patchable')

    def test_get(self):
        #  check if data base has entries
        if not UC2Observation.objects.all().exists():
            self.test_post_good_file()
        p = self.file_dir / "good_format_file.nc"
        uc2ds = uc2data.Dataset(p)
        fname = uc2ds.filename
        entry = UC2Observation.objects.get(file_standard_name=fname)

        # query one field
        data = {'acronym': uc2ds.ds.acronym}
        req = self._build_get_request(data, user=AnonymousUser)
        resp = self.view(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, 'Search query should succeed')
        self.assertEqual(resp.data, [], "Anonymous user should not see a file licensed to 3DO")

        req = self._build_get_request(data, user=self.user_3do)
        resp = self.view(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, 'Search query should succeed')
        self.assertEqual(len(resp.data), 1, "3DO user should see the object")

        data = {'acronym': "not_in_db"}
        req = self._build_get_request(data, user=self.user_3do)
        resp = self.view(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, 'Search query should succeed')
        self.assertEqual(resp.data, [])


class TestInstitutionView(APITestCase):
    file_dir = Path(__file__).parent / "test_files" / "tables"
    fixtures = ['groups_and_licenses.json']

    def setUp(self):
        self.super_user = User.objects.create_superuser(username="TestUser", email="test@user.com", password="test")
        self.user = User.objects.create_user(username="TestUser2", email="test@user2.com", password="test")
        self.user_3do = User.objects.create_user("test3",email="foo@baa.de", password="xxx", is_active=True)

    def test_create_institution(self):
        self.client.force_login(self.super_user)
        testfile_path = self.file_dir / "institutions.csv"
        url = reverse('institution-list')
        with open(testfile_path, 'rb') as f:
            resp = self.client.post(
                url,
                data={
                    'file': f
                }
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Institution.objects.filter(acronym='TUBklima').exists())

        self.assertTrue(Group.objects.filter(name='TUBklima').exists())

        new_institution_file = self.file_dir / 'with_new_inst.csv'
        with open(new_institution_file, 'rb') as f:
            resp = self.client.post(
                url,
                data={
                    'file': f
                }
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, "Reposting existing data fails")
        self.assertTrue(Institution.objects.filter(acronym='NoSe').exists())

    def test_list_institution(self):
        self.client.force_login(self.super_user)
        testfile_path = self.file_dir / "institutions.csv"
        url = reverse('institution-list')
        with open(testfile_path, 'rb') as f:
            resp = self.client.post(
                url,
                data={
                    'file': f
                }
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Institution.objects.filter(acronym='TUBklima').exists())

        url = reverse('institution-list')
        resp = self.client.get(url)
        self.assertGreater(len(resp.data), 0)


class TestSiteView(APITestCase):
    file_dir = Path(__file__).parent / "test_files" / "tables"
    fixtures = ['groups_and_licenses.json', 'data/tests/fixtures/institutions.json']

    def setUp(self):
        self.super_user = User.objects.create_superuser(username="TestUser", email="test@user.com", password="test")

    def test_sites(self):

        self.client.force_login(self.super_user)
        test_site = {
            'location': 'S',
            'site': 'marienpl',
            'description': 'Marienplatz',
            'address': 'Marienplatz, Süd, 70178 Stuttgart',
            'institution': 'FZJiek8, LUHimuk, USifk, DWDku1',
            'campaign': 'LTO, IOP'
        }
        se = SiteSerializer(data=test_site)
        self.assertTrue(se.is_valid())
        site = se.save()
        inst = list(site.institution.all().values_list('acronym', flat=True))
        self.assertCountEqual(inst, ['FZJiek8', 'LUHimuk', 'USifk', 'DWDku1'])  # compares elements ignoring the order

        testfile_path = self.file_dir / "sites.csv"
        url = reverse('site-list')
        with open(testfile_path, 'rb') as f:
            resp = self.client.post(
                url,
                data={
                    'file': f
                }
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class TestVariableView(APITestCase):
    file_dir = Path(__file__).parent / 'test_files' / 'tables'
    fixtures = ['groups_and_licenses.json', 'data/tests/fixtures/institutions.json']

    def setUp(self):
        self.super_user = User.objects.create_superuser(username='TestUser', email='test@user.com', password='test')

    def test_variable(self):
        self.client.force_login(self.super_user)
        testfile_path = self.file_dir / 'variables.csv'
        url = reverse('variable-list')
        with open(testfile_path, 'rb') as f:
            resp = self.client.post(
                url,
                data={
                    'file': f
                }
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

