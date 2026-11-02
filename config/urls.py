"""
URL configuration for the Healthcare Management Backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    # Authentication & Accounts API routes
    path('api/auth/', include('accounts.urls')),
    # Patient Management API routes
    path('api/patients/', include('patients.urls')),
    # Doctor Management API routes
    path('api/doctors/', include('doctors.urls')),
    # Patient-Doctor Mapping API routes
    path('api/mappings/', include('mappings.urls')),
    # Future application routes will be registered here:
    # path('api/v1/doctors/', include('doctors.urls')),
    # path('api/v1/mappings/', include('mappings.urls')),
]
