from django.contrib import admin
from django.urls import path, include  # include is needed to add your app's URLs

urlpatterns = [
    path('admin/', admin.site.urls),  # Django admin
    path('', include('mapapp.urls')),  # 👈 Include your mapapp URLs for the homepage
]
