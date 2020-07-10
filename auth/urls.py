from rest_framework.routers import DefaultRouter
from auth import views as auth_views

urlpatterns = [
]
router = DefaultRouter()
router.register(r'auth/group', auth_views.GroupView, basename='group')
router.register(r'auth/user', auth_views.UserApi, basename='user')
router.register(r'auth/login', auth_views.AuthTokenViewSet, basename='login')
urlpatterns.extend(router.urls)