from django.urls import path

from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.index, name="index"),
]

# for development: Access to files via URL
#  if settings.DEBUG:
#      urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
