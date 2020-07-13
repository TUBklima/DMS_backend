from django.urls import path  # , include

from . import views
# from rest_framework import routers
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'data/file', views.FileView, basename='file')
router.register(r'data/institution', views.InstitutionView, basename='institution')
router.register(r'data/site', views.SiteView, basename='site')
router.register(r'data/variable', views.VariableView, basename='variable')

