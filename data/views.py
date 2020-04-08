import os

import uc2data
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse
from django.utils import dateformat, timezone
from rest_framework import renderers, status
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dms_backend.settings import MEDIA_ROOT

from .models import UC2Observation
from .serializers import UC2Serializer


#  import xarray as xr


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

    @property
    def status(self):
        if self.errors:
            return uc2data.ResultCode.ERROR
        elif self.warnings:
            return uc2data.ResultCode.WARNING
        else:
            return uc2data.ResultCode.OK

    @property
    def has_errors(self):
        return self.status == uc2data.ResultCode.ERROR

    @property
    def has_warnings(self):
        return self.status == uc2data.ResultCode.WARNING

    def to_dict(self):
        return {'status': self.status,
                "errors": self.errors,
                "warnings": self.warnings}


class FileView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

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

        ignore_errors = 'ignore_errors' in user_input and user_input['ignore_errors']
        if ignore_errors and not request.user.is_superuser:
            result.errors.append("Only a superuser can ignore errors.")
            return Response(data=result.to_dict(), status=status.HTTP_400_BAD_REQUEST)

        ignore_warnings = 'ignore_warnings' in user_input and user_input['ignore_warnings']

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

        standart_name = uc2ds.filename
        try:
            version = int(uc2ds.ds.attrs['version'])
        except Exception:
            result.errors.insert(0, "Can not access the required version attribute")

        version_ok, expected_version = self._is_version_valid(standart_name, version)
        if not version_ok:
            result.errors.insert(0, "The given version number does not match the accepted version number")

        if result.status == uc2data.ResultCode.ERROR and not ignore_errors:
            return Response(data=result.to_dict(), status=status.HTTP_406_NOT_ACCEPTABLE)
        elif result.status == uc2data.ResultCode.WARNING and not ignore_warnings:
            return Response(data=result.to_dict(), status=status.HTTP_300_MULTIPLE_CHOICES)

        ####
        # set attributes
        ####

        new_entry = {}
        for key in uc2ds.ds.attrs:
            if key in UC2Serializer().data.keys():
                new_entry[key] = uc2ds.ds.attrs[key]

        new_entry["input_name"] = standart_name
        new_entry["version"] = version

        new_entry["upload_date"] = dateformat.format(timezone.now(), "Y-m-d H:i:s")
        new_entry["uploader"] = request.user.pk
        new_entry["is_old"] = 0
        new_entry["is_invalid"] = 0
        new_entry["has_warnings"] = result.has_warnings
        new_entry['has_errors'] = result.has_errors

            serializer = UC2Serializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                response_data["file_saved"] = 1
                os.remove(tempfile_path)
                response_data["tempfile_deleted"] = 1
                response_data["serializer"] = serializer.data
                if int(request.data["version"]) > 1:
                    self._toggle_old_entry(request)
                    response_data["marked_old_version"] = 1
                return Response(response_data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=400)
        except:
            return Response(
                {"Unknown Error": "Please contact administrator"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        result.errors.extend(serializer.errors)
        return Response(result.to_dict(), status=status.HTTP_400_BAD_REQUEST)

    def _is_version_valid(self, standart_name, version):
        """
        check validity of request version by querying for database entries.
        Returns True/False
        """

        input_name = "".join(standart_name.split("-")[:-1]) #  ignore version in standart_name

        all_versions = UC2Observation.objects.filter(input_name__startswith=input_name).order_by('-version')
        last_version = all_versions.first()  # find the maximum version
        if last_version:
            if last_version+1 == version:
                return True, version
            else:
                return False, last_version+1
        else:
            if version == 1:
                return True, version
            else:
                return False, 1

    def _toggle_old_entry(self, request):
        """ Queries for previous entry with the same input (file) name and switches urns it, if found.
        Returns False if previous version of file is not in database"""

        version = int(request.data["version"])
        input_name = request.data["input_name"]
        print("getting old version")
        prev_entry = UC2Observation.objects.filter(input_name=input_name).filter(version=(version - 1)).get(is_old=0)
        print("setting 'is_old' attribute")
        prev_entry.is_old = 1  # switch "is_old" attribute in previous entry for file
        prev_entry.save()
        return True

    @action(methods=["get"], detail=True, renderer_classes=(PassthroughRenderer,))
    def download(self, *args, **kwargs):
        instance = self.get_object()
        file_handle = instance.file_path.open()

        response = FileResponse(file_handle)

        return response
