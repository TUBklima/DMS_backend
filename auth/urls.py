from django.urls import path
from rest_framework.authtoken import views as rest_views
from rest_framework.routers import DefaultRouter
from auth import views as auth_views

urlpatterns = [
    path('login/', rest_views.obtain_auth_token, name="login"),
    path('', auth_views.UserApi.as_view(), name='requestAccount'),
    path('manageAccount/<str:token>', auth_views.manage_account, name='manageAccount'),
    path('', auth_views.UserApi.as_view(), name="users")
]
router = DefaultRouter()
router.register(r'group', auth_views.GroupView, basename='group')
urlpatterns.extend(router.urls)

