import datetime
import uc2data

from django.db import models
from django.utils import timezone


class DataFile(models.Model):
    input_name = models.CharField(max_length=200)
    file_id = models.CharField(max_length=200)
    keywords = models.CharField(max_length=200)
    user_id = models.PositiveIntegerField()
    author = models.CharField(max_length=200)
    source = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    version = models.PositiveIntegerField(default=1)
    upload_date = models.DateTimeField('upload_date')
    download_count = models.PositiveIntegerField(default=0)
    license = models.CharField(max_length=200, default=" ")

    def __str__(self):
        return self.input_name

    def upload(self):
        self.upload_date = timezone.now()

    class Meta:
        abstract = True


class UC2Observation(DataFile):
    feature_type = models.CharField(max_length=200)
    data_content = models.CharField(max_length=200)

    def upload(self):
        ds = uc2data.Dataset(self.file_id)
        ds.uc2_check()
        if ds.check_result.errors:
            print("File is not compatible with UC2 data standard.")
            print(ds.check_result.errors)


class Variable(models.Model):
    variable_name = models.CharField(max_length=32)
    long_name = models.CharField(max_length=200)
    standard_name = models.CharField(max_length=200)
    data_file = models.ForeignKey('UC2Observation', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.variable_name
