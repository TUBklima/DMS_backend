from django.views import generic
from django.shortcuts import get_object_or_404, render
from .models import UC2Observation, make_path, get_file_info
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from django.template.response import TemplateResponse
from django.http import HttpResponse


class IndexView(generic.ListView):
    template_name = 'data/index.html'
    context_object_name = 'file_list'

    def get_queryset(self):
        return UC2Observation.objects.filter(is_old=False, is_invalid=False)


def upload(request):
    if request.method == 'POST':
        uploaded_file = request.FILES['UC2Observation']
        new_filename = make_path()

        fs = FileSystemStorage
        fs.save(new_filename, uploaded_file)

        try:
            file_info = get_file_info(new_filename)
            this_version = int(file_info['version'])
            older_files = UC2Observation.objects.filter(filename_autogen="test").values_list("version", flat=True).order_by('version')
            if older_files.count() > 0:
                if list(older_files) != list(range(1, older_files.count()+1)):
                    raise Exception("The older versions of this file are not ordered")
                if this_version != older_files.count() + 1:
                    raise Exception("The uploaded file must have a version which is 1 higher than previous versions.")
                older_files.update(is_old=True)
            else:
                if this_version != 1:
                    raise Exception("The uploaded file must have version = 1")

            db_file = UC2Observation()
            db_file.filename_user = uploaded_file.name
            db_file.filename_autogen = file_info['filename_autogen']
            db_file.path = new_filename
            db_file.uploader = request.user
            db_file.upload_time = timezone.now()
            db_file.institution = '???'
            db_file.version = this_version

            check_results = db_file.cf_check()
            if check_results['ok']:
                db_file.save()
            else:
                fs.delete(new_filename)
            # TODO check file institution = user institution (=> ERROR)
            # TODO check dependencies file exists in DMS (=> WARNING)
        except Exception as e:
            fs.delete(new_filename)
            return render(request, 'data/upload.html', {'error': e, 'user': request.user})

        return render(request, 'data/check_results.html', {'check_results': check_results, 'file': db_file})

    return render(request, 'data/upload.html')


def detail(request, file_id):
    file = get_object_or_404(UC2Observation, pk=file_id)
    return TemplateResponse(request, 'data/detail.html', {
        "file": file
    })


def check_results(request):
    return render(request, 'data/check_results.html')
