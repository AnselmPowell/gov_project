from rest_framework import serializers
from .models import User
from django.contrib.auth.models import User as AdminUser

class UserSerializer(serializers.ModelSerializer):
  class Meta:
      model = User
      fields = ['id', 'first_name', 'last_name', 'email', 'created_at']
      read_only_fields = ['id', 'created_at']


class AdminUserSerializer(serializers.ModelSerializer):
  class Meta:
      model = AdminUser
      fields = ['id', 'username', 'email', 'is_staff', 'is_superuser', 'date_joined']
      read_only_fields = ['id', 'date_joined', 'is_staff', 'is_superuser']