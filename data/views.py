import json

import uc2data
from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse
from django.utils import dateformat, timezone
from django.contrib.auth.models import Group, AnonymousUser

from rest_framework import filters, renderers, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework import mixins

from guardian.shortcuts import assign_perm, get_objects_for_user

import csv

from .filters import UC2Filter
from .models import *
from .serializers import *

from auth.views import ActionBasedPermission, IsAuthenticatedOrPost

class PassthroughRenderer(renderers.BaseRenderer):
    """
        Return data as-is. View should supply a Response.
    """

    media_type = ""
    format = ""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


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


class IsAuthenticatedOrGet(IsAuthenticatedOrPost):
    SAFE_METHODS = ['GET']


class FileView(APIView):
    permission_classes = (IsAuthenticatedOrGet,)
    parser_classes = (MultiPartParser, FormParser)
    filter_backends = (filters.SearchFilter,)

    def post(self, request):

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

        # We don't add errors here because it is already checked by th uc2checker
        version = None
        try:
            version = int(uc2ds.ds.attrs['version'])
        except Exception:
            result.fatal.append("Can not access the version attribute.")

        standart_name = None
        try:
            standart_name = uc2ds.filename
        except Exception:
            result.fatal.append("Can not build a standart name.")

        if standart_name and version:
            version_ok, expected_version = self._is_version_valid(standart_name, version)
            if not version_ok:
                result.errors.insert(0, "The given version number does not match the accepted version number. "
                                        "The expected version number is "+str(expected_version) + ".")

        if result.has_errors and not ignore_errors:
            return Response(data=result.to_dict(), status=status.HTTP_406_NOT_ACCEPTABLE)

        if result.has_warnings and not ignore_warnings:
            return Response(data=result.to_dict(), status=status.HTTP_300_MULTIPLE_CHOICES)

        ####
        # set attributes
        ####

        new_entry = {}
        for key in uc2ds.ds.attrs:
            if key in UC2Serializer().data.keys():
                new_entry[key] = uc2ds.ds.attrs[key]

        new_entry['data_type'] = user_input['file_type']
        new_entry['file'] = request.data['file']
        if new_entry['keywords'] == '':
            new_entry['keywords'] = None

        new_entry["file_standard_name"] = standart_name
        new_entry["version"] = version

        new_entry["upload_date"] = dateformat.format(timezone.now(), "Y-m-d H:i:s")
        new_entry["uploader"] = request.user.pk
        new_entry["is_old"] = False
        new_entry["is_invalid"] = False
        new_entry["has_warnings"] = result.has_warnings
        new_entry['has_errors'] = result.has_errors

        try:
            licence = License.objects.get(full_text=new_entry['licence'])
            new_entry['licence'] = licence.id
        except ObjectDoesNotExist:
            licence = None
            result.fatal.append("No matching licence found")

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

        new_entry["variables"] = []
        new_variables = []

        # read variables from fiel and create if they not already exist
        for uc2var in uc2ds.data_vars:
            try:
                var_id = Variable.objects.get(variable=uc2var).id
                new_entry["variables"].append(var_id)
            except ObjectDoesNotExist:
                long_name = None
                try:
                    long_name = uc2ds.ds.data_vars[uc2var].long_name
                except AttributeError:
                    result.fatal.append("Can not access long_name for variable "+str(uc2var))
                standart_name = None
                try:
                    standart_name = uc2ds.ds.data_vars[uc2var].standard_name
                except AttributeError:
                    result.fatal.append("Can not access standard_name for variable "+str(uc2var))

                new_var = {
                    "variable": uc2var,
                    "long_name": long_name,
                    "standard_name": standart_name,
                }
                new_variables.append(new_var)

        if not result.has_fatal:
            # we do this in an extra step so we can avoid creating
            # variables if a fatal error exist. A unsuccessful request should not mutate
            # the db state
            serializer = VariableSerializer(data=new_variables, many=True)
            if serializer.is_valid():
                serializer.save()
                new_entry["variables"].extend([var['id'] for var in serializer.data])
            else:
                result.fatal.append(serializer.errors)

        ####
        # serialize and save
        ####

        serializer = UC2Serializer(data=new_entry)
        if not serializer.is_valid():
            result.fatal.append(serializer.errors)
            return Response(result.to_dict(), status=status.HTTP_406_NOT_ACCEPTABLE)

        #  toggle old version before saving -> in case of error we don't pollute the db
        if version > 1:
            self._toggle_old_entry(standart_name, version)

        serializer.save()
        # assign view permissions
        if licence.public:
            assign_perm(licence.view_permission, AnonymousUser(), serializer.instance)
            default_gr = Group.objects.get(name='users')
            assign_perm(licence.view_permission, default_gr, serializer.instance)
        else:
            for gr in licence.view_groups.all():
                assign_perm(licence.view_permission, gr, serializer.instance)

        result.result = serializer.data
        return Response(result.to_dict(), status=status.HTTP_201_CREATED)

    def patch(self, request):
        if 'is_invalid' in request.data and to_bool(request.data['is_invalid']):
            resp = self._set_invalid(request)
            return resp
        return Response("Patch method not available for" + json.dumps(request.data), status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def get(self, request):
        '''
        :param request:
        :return: A json representation of search query
        '''

        license_perms = License.objects.all().select_related('view_permission')
        license_set = set()
        for license_perm in license_perms:
            perm_string = license_perm.view_permission.codename
            license_set.add(perm_string)

        uc2_entries = get_objects_for_user(request.user, license_set, klass=UC2Observation, any_perm=True)
        f = UC2Filter(request.GET, queryset=uc2_entries)
        serializer = UC2Serializer(f.qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def _set_invalid(request):
        try:
            entry = UC2Observation.objects.get(file_standard_name=request.data['file_standard_name'])
            if request.user == entry.uploader or request.user.is_superuser:
                result = ApiResult()
                data = {'is_invalid': to_bool(request.data['is_invalid'])}
                serializer = UC2Serializer(entry, data=data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    result.result = serializer.data
                    return Response(data=result.to_dict(), status=status.HTTP_205_RESET_CONTENT)
                else:
                    result.errors.extend(serializer.errors)
                    return Response(result.to_dict(), status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
        except ObjectDoesNotExist:
            return Response("Object does not exist in data base.", status=status.HTTP_404_NOT_FOUND)

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
        # FIXME: Only allow if uploaders are the same one?

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
            #errors = [x for x in serializer.errors if x]
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InstitutionView(CsvViewSet):
    serializer_class = InstitutionSerializer
    queryset = Institution.objects.all()


class SiteView(CsvViewSet):
    serializer_class = SiteSerializer
    queryset = Site.objects.all()


class VariableView(CsvViewSet):
    serializer_class = VariableCsvSerializer
    queryset = Variable.objects.all()


@action(methods=["get"], detail=True, renderer_classes=(PassthroughRenderer,))
def download(self, *args, **kwargs):
    instance = self.get_object()
    file_handle = instance.file_path.open()

    response = FileResponse(file_handle)

    return response
