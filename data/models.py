#  import datetime
import uc2data
import pandas as pd
import random
import string
from pathlib import Path

from django.db import models
from django.utils import timezone, dateformat
from django.conf import settings
from django.contrib.auth import get_user_model


def get_sentinel_user():
    return get_user_model().objects.get_or_create(username="deleted")[0]


class DataFile(models.Model):
    data_type = models.CharField(max_length=200)
    file_standard_name = models.CharField(max_length=200, unique=True)
    file = models.FileField(null=False, blank=False)
    keywords = models.CharField(max_length=200, null=True, blank=False)
    #  TODO: Will this work with the custom auth model?
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, default=None, null=True)
    author = models.CharField(max_length=200, default="test")
    source = models.CharField(max_length=200, default="test")
    institution = models.CharField(max_length=200, default="Not specified")
    version = models.PositiveIntegerField(default=1)
    upload_date = models.DateTimeField(default=dateformat.format(timezone.now(), "Y-m-d H:i:s"))
    download_count = models.PositiveIntegerField(default=0)
    licence = models.CharField(max_length=200, default="[UC]2 Open Licence")
    is_invalid = models.BooleanField(null=False, default=False)
    is_old = models.BooleanField(null=False, default=False)
    has_warnings = models.BooleanField(null=False, default=False)
    has_errors = models.BooleanField(null=False, default=False)

    def __str__(self):
        return self.file_standard_name

    def __file_path__(self):
        return self.file_path.value_from_object(self)

    class Meta:
        abstract = True


class Variable(models.Model):
    variable = models.CharField(max_length=32)
    long_name = models.CharField(max_length=200)
    standard_name = models.CharField(max_length=200)

    def __str__(self):
        return self.variable


class UC2Observation(DataFile):
    featureType = models.CharField(max_length=32)
    data_content = models.CharField(max_length=200)
    version = models.PositiveSmallIntegerField(default=1)
    acronym = models.CharField(max_length=10)
    # spatial atts
    location = models.CharField(max_length=3)
    site = models.CharField(max_length=12)
    #  origin_x = models.FloatField()
    #  origin_y = models.FloatField()
    #  origin_z = models.FloatField()
    origin_lon = models.FloatField(default=0.0)
    origin_lat = models.FloatField(default=0.0)
    # time atts
    campaign = models.CharField(max_length=6)
    creation_time = models.CharField(max_length=23)
    origin_time = models.CharField(max_length=23)
    # variables
    variables = models.ManyToManyField(Variable, null=True)


def get_file_info(new_filename):
    f = DataFile()
    base_dir = Path(settings.BASE_DIR)
    to_open = base_dir / f.file_path.field.generate_filename(f.file_path.instance, new_filename)
    opened = uc2data.Dataset(to_open)
    attrs = opened.ds.attrs
    variables = opened.ds.variables
    return attrs, variables


def make_path():
    return "".join(random.choice(string.ascii_lowercase) for i in range(6)) + ".nc"
