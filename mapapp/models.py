from django.db import models


class Reservoir(models.Model):
    name = models.CharField(max_length=200, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name


class FileCleanupSettings(models.Model):
    """
    Singleton-style model to control whether uploaded files
    should be deleted after processing.
    """

    delete_uploaded_files = models.BooleanField(
        default=False,
        help_text="If enabled, uploaded files will be deleted after each RECLAIM run.",
    )

    def __str__(self):
        return "File Cleanup Settings"

    class Meta:
        verbose_name = "File Cleanup Settings"
        verbose_name_plural = "File Cleanup Settings"
