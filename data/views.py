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
            fs = FileSystemStorage()
            tempfile_path = os.path.join(MEDIA_ROOT, "temp", f.name)
            fs.save(os.path.join("temp", f.name), f)
            response_data["tempfile_saved"] = 1
            data = uc2data.Dataset(tempfile_path)
            data.uc2_check()
            response_data["uc2check"] = 1
            error_code = 0
            for i in data.check_result:
                for j in data.check_result[i]:
                    if data.check_result[i][j].result[0].result == uc2data.ResultCode.ERROR:
                        error_code = 1  # error code 1 for check error
                    if data.check_result[i][j].result[0].result == uc2data.ResultCode.WARNING:
                        error_code = 2  # error code 2 for check warnings
            if error_code:
                os.remove(tempfile_path)
                response_data["tempfile_deleted"] = 1
                response_data["uc2resultcode"] = 1
                return Response(response_data, status=status.HTTP_406_NOT_ACCEPTABLE)
            elif error_code == 2:
                response_data["uc2resultcode"] = 2
                return Response(response_data, status=status.HTTP_300_MULTIPLE_CHOICES)
            response_data["uc2resultcode"] = 0
            for key in data.ds.attrs:
                if key in UC2Serializer().data.keys():
                    request.data[key] = data.ds.attrs[key]

            request.data["input_name"] = data.filename
            request.data["upload_date"] = dateformat.format(timezone.now(), "Y-m-d H:i:s")
            request.data["uploader"] = request.user.pk
            request.data["is_old"] = 0
            request.data["is_invalid"] = 0

            if not self._is_version_valid(request):
                response_data["is_version_valid"] = 0
                return Response(response_data, status=status.HTTP_406_NOT_ACCEPTABLE)

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

    def _is_version_valid(self, request):
        """
        check validity of request version by querying for database entries.
        Returns True/False
        """

        print("querying versions")
        version = int(request.data["version"])
        input_name = request.data["input_name"]
        if version != 1:
            if UC2Observation.objects.filter(input_name=input_name).filter(
                version=(version - 1)
            ) and not UC2Observation.objects.filter(input_name=input_name).filter(version=version):
                print("version seems to be valid")
                return True
        if UC2Observation.objects.filter(input_name=input_name).filter(version=version):
            print("version already exists")
            return False
        else:
            print("version seems to be valid")
            return True

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
