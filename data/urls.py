from django.urls import path, include

from . import views
from rest_framework import routers
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
#      path('', include(router.urls)),
#      #  path('', views.FileView.as_view(), name='uc2upload'),
    path('uc2upload/', views.FileView.as_view(), name='uc2upload')
]

# for development: Access to files via URL
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
