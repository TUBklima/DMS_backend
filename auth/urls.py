from django.urls import path
from rest_framework_jwt.views import obtain_jwt_token
from auth import views as auth_views

urlpatterns = [
    path('login/', obtain_jwt_token, name="login"),
    path('requestAccount/', auth_views.request_account, name='requestAccount'),
    path('users/', auth_views.UserApi.as_view(), name="users")
]
