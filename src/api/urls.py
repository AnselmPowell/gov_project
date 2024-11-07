from django.urls import path
from .views import api_root, user_list_create, user_detail, admin_user_list

urlpatterns = [
    path('', api_root, name='api-root'),
    path('users/', user_list_create, name='user-list-create'),
    path('users/<int:pk>/', user_detail, name='user-detail'),
    path('admin-users/', admin_user_list, name='admin-user-list'),
]