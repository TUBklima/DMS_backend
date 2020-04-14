import uc2data
from django.http import FileResponse
from django.utils import dateformat, timezone
from rest_framework import renderers, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UC2Observation, Variable
from .serializers import UC2Serializer, VariableSerializer


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
                "warnings": self.warnings,
                "result": self.result}

def to_bool(input):
    if input.upper() in ["TRUE", "0"]:
        return True
    elif input.upper() in ['FALSE', "1"]:
        return False
    else:
        raise ValueError


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
        try:
            version = int(uc2ds.ds.attrs['version'])
        except Exception:
            version = None

        try:
            standart_name = uc2ds.filename
        except Exception:
            standart_name = None

        if standart_name and version:
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

        new_entry['data_type'] = user_input['file_type']
        new_entry['file'] = request.data['file']
        if new_entry['keywords'] == '':
            new_entry['keywords'] = None

        new_entry["input_name"] = standart_name
        new_entry["version"] = version

        new_entry["upload_date"] = dateformat.format(timezone.now(), "Y-m-d H:i:s")
        new_entry["uploader"] = request.user.pk
        new_entry["is_old"] = False
        new_entry["is_invalid"] = False
        new_entry["has_warnings"] = result.has_warnings
        new_entry['has_errors'] = result.has_errors

        for var in uc2ds.data_vars:
            if not Variable.objects.filter(variable=var).exists():
                new_var = {
                    "variable": var,
                    "long_name": uc2ds.ds.data_vars[var].long_name,
                    "standard_name": uc2ds.ds.data_vars[var].standard_name,
                }
                serializer = VariableSerializer(data=new_var)
                if serializer.is_valid():
                    serializer.save()
            new_entry["variables"] = Variable.objects.get(variable=var).id

        ####
        # serialize and save
        ####

        serializer = UC2Serializer(data=new_entry)
        if serializer.is_valid():
            #  toggle old version before saving -> in case of error we don't pollute the db
            if version > 1:
                self._toggle_old_entry(standart_name, version)

            serializer.save()
            result.result = serializer.data
            return Response(result.to_dict(), status=status.HTTP_201_CREATED)

        result.errors.extend(serializer.errors)
        return Response(result.to_dict(), status=status.HTTP_400_BAD_REQUEST)

    def _is_version_valid(self, standart_name, version):
        """
        check validity of request version by querying for database entries.
        Returns True/False
        """

        input_name = "-".join(standart_name.split("-")[:-1])  # ignore version in standart_name

        max_version = UC2Observation.objects.filter(input_name__startswith=input_name).order_by('version').last()

        if max_version:
            if max_version.version+1 == version:
                return True, version
            else:
                return False, max_version.version+1
        else:
            #  no matching input_name is found -> should be version one
            if version == 1:
                return True, version
            else:
                return False, 1


    def _toggle_old_entry(self, standart_name, version):
        """ Queries for previous entry with the same input (file) name and switches urns it, if found.
        Returns False if previous version of file is not in database"""

        input_name = "".join(standart_name.split("-")[:-1])  #  ignore version in standart_name

        prev_entry = UC2Observation.objects.filter(input_name__startswith=input_name, version=(version - 1))
        if prev_entry:
            prev_entry.is_old = 1  # switch "is_old" attribute in previous entry for file
            prev_entry.save()
        return True

    @action(methods=["get"], detail=True, renderer_classes=(PassthroughRenderer,))
    def download(self, *args, **kwargs):
        instance = self.get_object()
        file_handle = instance.file_path.open()

        response = FileResponse(file_handle)

        return response
