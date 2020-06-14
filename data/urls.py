from django.urls import path  # , include

from . import views
# from rest_framework import routers
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter

# router = routers.DefaultRouter()
# router.register('uc2upload', views.FileView)

urlpatterns = [
    # path('', include(router.urls)),
    #  path('', views.FileView.as_view(), name='uc2upload'),
    path('uc2upload/', views.FileView.as_view(), name='uc2upload'),
    path('uc2list/', views.FileView.as_view(), name='uc2list'),
    path('uc2list/<int:id>/', views.DetailView.as_view(), name='detail')
]

router = DefaultRouter()
router.register(r'institution', views.InstitutionView, basename='institution')
router.register(r'site', views.SiteView, basename='site')
router.register(r'variable', views.VariableView, basename='variable')

urlpatterns.extend(router.urls)

# for development: Access to files via URL
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
