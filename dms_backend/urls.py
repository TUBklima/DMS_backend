"""dms_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.urls import include
from rest_framework.routers import DefaultRouter
from data.urls import router as data_router
from auth.urls import router as auth_router

#  from data import views

router = DefaultRouter()
router.registry.extend(data_router.registry)
router.registry.extend(auth_router.registry)

urlpatterns = [
    path('admin/', admin.site.urls),
]
urlpatterns.extend(router.urls)
