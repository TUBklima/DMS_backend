import uc2data
import os

from django.http import FileResponse, HttpResponse, JsonResponse

from rest_framework import viewsets, renderers
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated  # , AllowAny

from .models import UC2Observation
from .serializers import UC2Serializer


class PassthroughRenderer(renderers.BaseRenderer):
    """
        Return data as-is. View should supply a Response.
    """
    media_type = ''
    format = ''

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class FileView(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)
    model = UC2Observation
    queryset = UC2Observation.objects.all()
    serializer_class = UC2Serializer

    def create(self, request, format=None):
        print(request.data)
        print("\n\n\n")
        serializer = UC2Serializer(data=request.data)
        if serializer.is_valid():
            # Save the file (have to do that first because: How to open and read file from request.FILES??
            serializer.save()
            file_path = serializer.data.get("file_path")
            #  do the database stuff
            data = uc2data.Dataset(file_path)
            data.uc2_check()
            error_code = 0
            warning_code = 0
            for i in data.check_result:
                for j in data.check_result[i]:
                    if data.check_result[i][j].result[0].result == uc2data.ResultCode.ERROR:
                        error_code = 1
                    if data.check_result[i][j].result[0].result == uc2data.ResultCode.WARNING:
                        warning_code = 1
            #  if error_code:
            #      #  TODO: get error message to right format and respond with json
            #      self.perform_destroy(UC2Observation.objects.filter(file_path=file_path))
            #      os.remove(file_path)
            #      return HttpResponse(data.check_result.errors)
            #  if warning_code:
            #      os.remove(file_path)
            #      self.perform_destroy(UC2Observation.objects.filter(file_path=file_path))
            #      return HttpResponse(data.check_result.warnings)
            #  else:
            db_entry = UC2Observation.objects.get(file_path=file_path)
            db_entry.feature_type = data.ds.featureType
            db_entry.keywords = data.ds.keywords
            db_entry.author = data.ds.author
            db_entry.source = data.ds.source
            db_entry.institution = data.ds.institution
            db_entry.version = data.ds.version
            db_entry.licence = data.ds.licence
            db_entry.data_content = data.ds.data_content
            db_entry.acronym = data.ds.acronym
            db_entry.location = data.ds.location
            db_entry.site = data.ds.site
            db_entry.origin_lon = data.ds.origin_lon
            db_entry.origin_lat = data.ds.origin_lat
            db_entry.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors, status=400)

    @action(methods=['get'], detail=True, renderer_classes=(PassthroughRenderer,))
    def download(self, *args, **kwargs):
        instance = self.get_object()
        file_handle = instance.file_path.open()

        response = FileResponse(file_handle)

        return response
