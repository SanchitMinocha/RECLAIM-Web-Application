from django.contrib import admin
from .models import Reservoir
from .models import FileCleanupSettings


@admin.register(Reservoir)
class ReservoirAdmin(admin.ModelAdmin):
    list_display = ("name", "latitude", "longitude")
    search_fields = ("name",)


@admin.register(FileCleanupSettings)
class FileCleanupSettingsAdmin(admin.ModelAdmin):
    list_display = ("delete_uploaded_files",)
