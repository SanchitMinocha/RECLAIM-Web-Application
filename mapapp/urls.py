from django.urls import path
from .views import estimator_view, run_reclaim
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("estimator/", estimator_view, name="estimator"),
    path("run-reclaim/", run_reclaim, name="run_reclaim"),
    path(
        "download_time_series/",
        views.download_time_series,
        name="download_time_series",
    ),
    path(
        "download_sample/<str:folder_name>/",
        views.download_sample_zip,
        name="download_sample_zip",
    ),
]
