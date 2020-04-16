from django.urls import path, include

from . import views
# from rest_framework import routers
from django.conf import settings
from django.conf.urls.static import static

# router = routers.DefaultRouter()
# router.register('uc2upload', views.FileView)

urlpatterns = [
    # path('', include(router.urls)),
    #  path('', views.FileView.as_view(), name='uc2upload'),
    path('uc2upload/', views.FileView.as_view(), name='uc2upload'),
    path('uc2list/', views.FileView.as_view(), name='uc2list'),
    path('download/', views.download, name='download')
]

# for development: Access to files via URL
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
