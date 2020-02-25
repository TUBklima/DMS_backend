from django.urls import path

from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("upload/", views.upload, name="upload"),
    path("<int:file_id>/detail/", views.detail, name="detail"),
]

# for development: Access to files via URL
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
