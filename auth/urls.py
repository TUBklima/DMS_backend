from django.urls import path
from rest_framework.authtoken import views as rest_views
from auth import views as auth_views

urlpatterns = [
    path('login/', rest_views.obtain_auth_token, name="login"),
    path('', auth_views.UserApi.as_view(), name='requestAccount'),
    path('manageAccount/<str:token>', auth_views.manage_account, name='manageAccount'),
    path('', auth_views.UserApi.as_view(), name="users")
]
