import json
import pkg_resources

import uc2data

from django.http import HttpResponse
from django.contrib.auth.models import  AnonymousUser

from rest_framework import filters, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.pagination import LimitOffsetPagination
from rest_framework import mixins
from rest_framework.decorators import action

from django_filters import rest_framework as dj_filters

from guardian.shortcuts import assign_perm, get_objects_for_user


from .filters import UC2Filter
from .models import *
from .serializers import *

from auth.views import ActionBasedPermission

class ApiResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.result = []
        self.fatal = []
    @property
    def status(self):
        if self.fatal:
            return uc2data.ResultCode['FATAL'].value
        elif self.errors:
            return uc2data.ResultCode['ERROR'].value
        elif self.warnings:
            return uc2data.ResultCode['WARNING'].value
        else:
            return uc2data.ResultCode['OK'].value

    @property
    def has_fatal(self):
        return self.status == uc2data.ResultCode.FATAL.value

    @property
    def has_errors(self):
        return self.status == uc2data.ResultCode.ERROR.value

    @property
    def has_warnings(self):
        return self.status == uc2data.ResultCode.WARNING.value

    def to_dict(self):
        return {'status': self.status,
                "fatal": self.fatal,
                "errors": self.errors,
                "warnings": self.warnings,
                "result": self.result}


def to_bool(input):
    if input.upper() in ["TRUE", "1", "YES"]:
        return True
    elif input.upper() in ['FALSE', "0", "NO"]:
        return False
    else:
        raise ValueError


class FileView(mixins.ListModelMixin,
               GenericViewSet):
    pagination_class = LimitOffsetPagination
    permission_classes = (ActionBasedPermission,)
    action_permissions = {
        IsAuthenticated: ['create', 'set_invalid', 'destroy'],
        AllowAny: ['list', 'retrieve']
    }

    filter_backends = (filters.SearchFilter, dj_filters.DjangoFilterBackend)
    filter_class = UC2Filter
    search_fields = [
                     'site__site', 'site__address',
                     'acronym__ge_title', 'acronym__en_title', 'acronym__acronym',  #institution
                     'variables__variable', 'variables__long_name', 'variables__standard_name',
                     'file_standard_name', 'keywords', 'author', 'source', 'data_content'
                     ]

    serializer_class = UC2Serializer


    def get_queryset(self):
        """
        Ensure that only objects with a licence matching the user are returned
        :return:
        """
        license_perms = License.objects.all().select_related('view_permission')
        license_set = set()
        for license_perm in license_perms:
            perm_string = license_perm.view_permission.codename
            license_set.add(perm_string)

        # license
        uc2_entries = get_objects_for_user(self.request.user, license_set, klass=UC2Observation, any_perm=True)
        return uc2_entries

    def check_object_permissions(self, request, obj):
        if self.action in ['set_invalid', 'destroy']:
            if self.action == 'set_invalid':
                msg = 'Only a superuser or a member of the uploading institution can mark a file as invalid'
            else:
                msg = 'Only a superuser or a member of the uploading institution can delete a file'

            user_in_institution_group = request.user.groups.filter(name=obj.acronym.acronym).exists()
            if not user_in_institution_group and not request.user.is_superuser:
                self.permission_denied(
                    request, message=msg
                )

        super().check_object_permissions(request, obj)

    def create(self, request):

        required_tags = {"file", "file_type"}
        possible_tags = {"ignore_errors", "ignore_warnings"}
        allowed_file_types = {"UC2"}

        user_input = request.data
        result = ApiResult()

        ####
        # parse user request
        ####

        if not required_tags.issubset(user_input):
            missing = ",".join(required_tags - set(user_input))
            result.errors.append("Missing the required tags: " + missing)
            return Response(data=result.to_dict(), status=status.HTTP_400_BAD_REQUEST)

        if user_input['file_type'] not in allowed_file_types:
            result.errors.append(user_input['file_type'] + " is not supported. Supported types are "
                                 + ",".join(allowed_file_types))
            return Response(data=result.to_dict(), status=status.HTTP_400_BAD_REQUEST)

        ignore_errors = False
        if 'ignore_errors' in user_input:
            # ignore errors is set and we can try to convert it to a bool
            try:
                ignore_errors = to_bool(user_input['ignore_errors'])
            except ValueError:
                result.warnings.append("Can not parse ignore_errors field. " + user_input['ignore_errors'] +
                                       " is not recognized as bool. The field is ignored.")

        if ignore_errors and not request.user.is_superuser:
            result.errors.append("Only a superuser can ignore errors.")
            return Response(data=result.to_dict(), status=status.HTTP_400_BAD_REQUEST)

        ignore_warnings = False
        if 'ignore_warnings' in user_input:
            # ignore warnings is set and we can try to convert it to a bool
            try:
                ignore_warnings = to_bool(user_input['ignore_warnings'])
            except ValueError:
                result.warnings.append("Can not parse ignore_warnings field. " + user_input['ignore_warnings'] +
                                       " is not recognized as bool. The field is ignored")

        extra_tags = set(user_input) - (required_tags | possible_tags)
        if extra_tags:
            result.warnings.append("The request contains the following unrecognized tags: " + ",".extra_tags + "."
                                   "This tags are ignored.")
        ####
        # check the file
        ####

        f = request.data["file"]
        # This line works because FILE_UPLOAD_HANDLERS is set to TemporaryFileUploadHandler. However
        # if the setting changes this line will break. It would be better to modify the request, but this is complicate
        # with ApiView and post. See https://docs.djangoproject.com/en/3.0/topics/http/file-uploads/#modifying-upload-handlers-on-the-fly
        # So we use this warning instead
        uc2ds = uc2data.Dataset(f.temporary_file_path())
        uc2ds.uc2_check()
        check_result = uc2ds.check_result.to_dict(sort=True)
        result.errors.extend(check_result['root']['ERROR'])
        result.warnings.extend(check_result['root']['WARNING'])

        new_entry = {}

        # We don't add errors here because it is already checked by th uc2checker
        version = None
        try:
            version = int(uc2ds.ds.attrs['version'])
        except Exception:
            result.fatal.append("Can not access the version attribute.")

        standard_name = None
        try:
            standard_name = uc2ds.filename
        except Exception:
            result.fatal.append("Can not build a standart name.")

        if standard_name and version:
            version_ok, expected_version = self._is_version_valid(standard_name, version)
            if version_ok:
                new_entry["file_standard_name"] = standard_name
                new_entry["version"] = version
            else:
                result.errors.insert(0, "The given version number does not match the accepted version number. "
                                        "The expected version number is "+str(expected_version) + ".")




        ####
        # set attributes
        ####

        if uc2ds.ds:
            for key in uc2ds.ds.attrs:
                if key in UC2Serializer().data.keys():
                    new_entry[key] = uc2ds.ds.attrs[key]

        uc2checker_version = pkg_resources.get_distribution("uc2data").version
        try:
            major, minor, sub = uc2checker_version.split('.')
        except ValueError:
            return Response(data="internal error", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        new_entry['checkerVersionMajor'] = major
        new_entry['checkerVersionMinor'] = minor
        new_entry['checkerVersionSub'] = sub

        new_entry['data_type'] = user_input['file_type']
        new_entry['file'] = request.data['file']

        new_entry["uploader"] = request.user.username
        new_entry["is_old"] = False
        new_entry["is_invalid"] = False
        new_entry["has_warnings"] = result.has_warnings
        new_entry['has_errors'] = result.has_errors

        if 'licence' in new_entry:
            try:
                i_licence = License.objects.get(full_text=new_entry['licence'])
                new_entry['licence'] = i_licence.short_name
            except ObjectDoesNotExist:
                i_licence = None
                result.fatal.append("No matching licence found")
        else:
            i_licence = License.objects.get(short_name='empty')
            new_entry['licence'] = i_licence.short_name

        # Add coordinates
        lat_lon_ok = True
        try:
            ll_lat, ll_lon, ur_lat, ur_lon, lat_lon_epsg = uc2ds.get_bounds()
        except Exception:
            result.fatal.append("Can not access the coordinates of the bounding rectangle (lat / lon )")
            lat_lon_ok = False

        if lat_lon_ok:
            new_entry['ll_lat'] = ll_lat
            new_entry['ll_lon'] = ll_lon
            new_entry['ur_lat'] = ur_lat
            new_entry['ur_lon'] = ur_lon
            new_entry['lat_lon_epsg'] = lat_lon_epsg

        utm_ok = True
        try:
            ll_n_utm, ll_e_utm, ur_n_utm, ur_e_utm, utm_epsg = uc2ds.get_bounds(utm=True)
        except Exception:
            result.fatal.append("Can not access the coordinates of the bounding rectangle (utm)")

        if utm_ok:
            new_entry['ll_n_utm'] = ll_n_utm
            new_entry['ll_e_utm'] = ll_e_utm
            new_entry['ur_n_utm'] = ur_n_utm
            new_entry['ur_e_utm'] = ur_e_utm
            new_entry['utm_epsg'] = utm_epsg

        new_entry["variables"] = uc2ds.data_vars

        ####
        # serialize, check errors, warning, fatal and save
        ####
        serializer = UC2Serializer(data=new_entry)

        if not serializer.is_valid():
            result.fatal.append(serializer.errors)

        try:
            user_in_institution_group = request.user.groups.filter(
                name=serializer.validated_data['acronym'].acronym).exists()
            if not user_in_institution_group and not request.user.is_superuser:
                result.fatal.append("You are not part of the institution this file belongs to. Uploading prohibited.")
                return Response(result.to_dict(), status=status.HTTP_403_FORBIDDEN)

        except (KeyError, AttributeError):
            if serializer.is_valid:
                result.fatal.append("Can not access 'acronym' field on validated data")
            else:
                pass  # we already have fatal errors which cause this to happen

        if result.has_warnings and not ignore_warnings:
            return Response(data=result.to_dict(), status=status.HTTP_300_MULTIPLE_CHOICES)

        if result.has_errors and not ignore_errors:
            return Response(data=result.to_dict(), status=status.HTTP_406_NOT_ACCEPTABLE)

        if result.has_fatal:
            return Response(data=result.to_dict(), status=status.HTTP_406_NOT_ACCEPTABLE)

        #  toggle old version before saving -> in case of error we don't pollute the db
        if version > 1:
            self._toggle_old_entry(standard_name, version)

        serializer.save()
        # assign view permissions
        if i_licence.public:
            assign_perm(i_licence.view_permission, AnonymousUser(), serializer.instance)
            default_gr = Group.objects.get(name='users')
            assign_perm(i_licence.view_permission, default_gr, serializer.instance)
        else:
            for gr in i_licence.view_groups.all():
                assign_perm(i_licence.view_permission, gr, serializer.instance)

        result.result = serializer.data
        return Response(result.to_dict(), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'])
    def set_invalid(self, request, pk=None):
        entry = self.get_object()
        result = ApiResult()
        data = {'is_invalid': True}
        serializer = UC2Serializer(entry, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            result.result = serializer.data
            return Response(data=result.to_dict(), status=status.HTTP_205_RESET_CONTENT)
        else:
            result.errors.extend(serializer.errors)
            return Response(result.to_dict(), status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        obj = self.get_object()
        response = HttpResponse(obj.file, content_type='multipart/form', status=status.HTTP_200_OK)
        response['Content-Disposition'] = "attachment; filename=%s" % str(obj.file_standard_name)
        response['Content-Length'] = obj.file.size
        # change download_count of object
        obj.download_count += 1
        obj.save()
        return response

    def destroy(self, request, pk=None):
        obj = self.get_object()
        if obj.download_count != 0:
            return Response("Download count not 0.", status=status.HTTP_403_FORBIDDEN)
        obj.delete()
        return Response("File deleted", status=status.HTTP_204_NO_CONTENT)

    def _is_version_valid(self, standart_name, version):
        """
        check validity of request version by querying for database entries.
        Returns True/False
        """

        input_name = "-".join(standart_name.split("-")[:-1])  # ignore version in standart_name
        max_version = UC2Observation.objects.filter(file_standard_name__startswith=input_name).order_by('version').last()

        if max_version:
            if max_version.version+1 == version:
                return True, version
            else:
                return False, max_version.version+1
        else:
            #  no matching file_standard_name is found -> should be version one
            if version == 1:
                return True, version
            else:
                return False, 1

    def _toggle_old_entry(self, standart_name, version):
        """ Queries for previous entry with the same input (file) name and switches urns it, if found.
        Returns False if previous version of file is not in database"""
        input_name = "-".join(standart_name.split("-")[:-1])  # ignore version in standart_name

        prev_entries = UC2Observation.objects.filter(file_standard_name__startswith=input_name, version=(version - 1))
        for prev_entry in prev_entries:
            prev_entry.is_old = True  # switch "is_old" attribute in previous entries for file
            prev_entry.save()
        return True


class LicenseView(ModelViewSet):
    serializer_class = LicenceSerializer
    queryset = License.objects.all()
    permission_classes = (ActionBasedPermission,)
    action_permissions = {
        IsAdminUser: ['update', 'partial_update', 'destroy', 'create'],
        AllowAny: ['list', 'retrieve']
    }


class CsvViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    """
    A class representing data read from a CSV file
    """
    permission_classes = (ActionBasedPermission,)
    action_permissions = {
        IsAdminUser: ['create'],
        AllowAny: ['list']
    }

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, many=True)
        if not serializer.is_valid():
            result = ApiResult()
            result.fatal.extend(serializer.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST, data=result.to_dict())
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InstitutionView(CsvViewSet):
    pagination_class = LimitOffsetPagination
    serializer_class = InstitutionSerializer
    queryset = Institution.objects.all()


class SiteView(CsvViewSet):
    serializer_class = SiteSerializer
    queryset = Site.objects.all()


class VariableView(CsvViewSet):

    serializer_class = VariableCsvSerializer
    queryset = Variable.objects.filter(deprecated=False)
