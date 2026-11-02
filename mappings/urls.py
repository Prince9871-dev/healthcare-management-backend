from django.urls import path
from .views import MappingDetailView, MappingListCreateView

app_name = "mappings"

urlpatterns = [
    path("", MappingListCreateView.as_view(), name="mapping-list-create"),
    path("<uuid:id>/", MappingDetailView.as_view(), name="mapping-detail"),
]
