from django.views import generic
from django.shortcuts import get_object_or_404, render
#  from .models import File, make_path, get_file_info
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from django.template.response import TemplateResponse
from django.http import HttpResponse


def index(request):
    return HttpResponse("Download")
