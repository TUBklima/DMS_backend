#  import datetime
import uc2data
import pandas as pd
import random
import string
from pathlib import Path

from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

tab01 = pd.read_csv('http://www.uc2-program.org/uc2_table_A1.csv', sep="\t").reset_index()
tab02 = pd.read_csv('http://www.uc2-program.org/uc2_table_A2.csv', sep="\t").reset_index()
tab03 = pd.read_csv('http://www.uc2-program.org/uc2_table_A3.csv', sep="\t").reset_index()
tab04 = pd.read_csv('http://www.uc2-program.org/uc2_table_A4.csv', sep="\t").reset_index()

VARIABLE = [vari for vari in zip(tab01.iloc[:, 0], tab01.loc[:, 'variable'])]
DATA_CONTENT = [daco for daco in zip(tab02.iloc[:, 0], tab02.loc[:, 'data_content'])]
INSTITUTION = [inst for inst in zip(tab03.iloc[:, 0], tab03.loc[:, 'institution'])]
SITE = [site for site in zip(tab04.iloc[:, 0], tab04.loc[:, 'site'])]
LICENCE = [("test", "Choose a License"), ("UC2", "[UC]2 Open Licence")]
DATA_TYPE = [
    ("", "What data type do you want to upload?"),
    ("UC2Obs", "UC2Observation"),
    ("UC2Mod", "UC2Model"),
    ("sta_dr", "Static Driver"),
    ("dyn_in", "Dynamic Driver"),
]


def get_sentinel_user():
    return get_user_model().objects.get_or_create(username='deleted')[0]


class DataFile(models.Model):
    data_type = models.CharField(max_length=200, choices=DATA_TYPE, default="trajectory")
    input_name = models.CharField(max_length=200, default="test")
    file_id = models.CharField(max_length=200, default="0")
    file_path = models.FileField(max_length=200, null=False, unique=True, upload_to='files/', default=settings.BASE_DIR)
    keywords = models.CharField(max_length=200, default="None")
    #  TODO: Will this work with the custom auth model?
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, default=None, null=True)
    author = models.CharField(max_length=200, default="test")
    source = models.CharField(max_length=200, default="test")
    institution = models.CharField(max_length=200, default="Not specified")
    version = models.PositiveIntegerField(default=1)
    upload_date = models.DateTimeField('upload_date', default=timezone.now)
    download_count = models.PositiveIntegerField(default=0)
    licence = models.CharField(max_length=200, default="[UC]2 Open Licence")
    is_invalid = models.BooleanField(null=False, default=False)
    is_old = models.BooleanField(null=False, default=False)

    def __str__(self):
        return self.input_name

    def __file_path__(self):
        return self.file_path.value_from_object(self)

    def cf_check(self):
        return {'ok': True}

    def upload(self):
        self.upload_date = timezone.now()

    def download(self):
        self.download_count += 1

    class Meta:
        abstract = True


class UC2Observation(DataFile):
    FEATURE_TYPE = [
        (None, "Not set (only allowed for multidimensional data)"),
        ("timeSeries", "timeSeries"),
        ("timeSeriesProfile", "timeSeriesProfile"),
        ("trajectory", "trajectory"),
    ]
    CAMPAIGN = [
        ("IOP01", "IOP01"),
        ("IOP02", "IOP02"),
        ("IOP03", "IOP03"),
        ("IOP04", "IOP04"),
        ("VALR01", "VALR01"),
    ]
    feature_type = models.CharField(max_length=32, default="Not set")
    data_content = models.CharField(max_length=200, default="test")
    version = models.PositiveSmallIntegerField(default=1)
    acronym = models.CharField(max_length=10, default="Ups")
    # spatial atts
    location = models.CharField(max_length=3, default="B")
    site = models.CharField(max_length=12, default="Not set")
    #  origin_x = models.FloatField()
    #  origin_y = models.FloatField()
    #  origin_z = models.FloatField()
    origin_lon = models.FloatField(default=0.)
    origin_lat = models.FloatField(default=0.)
    # time atts
    campaign = models.CharField(max_length=6, choices=CAMPAIGN, default=CAMPAIGN[0])
    creation_time = models.CharField('creation_time', max_length=23, default=timezone.now)
    origin_time = models.CharField(max_length=23, default=timezone.now)

    def uc2_check(self):
        ds = uc2data.Dataset(self.file_id)
        ds.uc2_check()
        if ds.check_result.errors:
            print("File is not compatible with UC2 data standard.")
            print(ds.check_result.errors)
            return False


class Variable(models.Model):
    variable_name = models.CharField(max_length=32)
    long_name = models.CharField(max_length=200)
    standard_name = models.CharField(max_length=200)
    data_file = models.ForeignKey(UC2Observation, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.variable_name


def get_file_info(new_filename):
    f = DataFile()
    base_dir = Path(settings.BASE_DIR)
    to_open = base_dir / f.file_path.field.generate_filename(f.file_path.instance, new_filename)
    opened = uc2data.Dataset(to_open)
    attrs = opened.ds.attrs
    variables = opened.ds.variables
    return attrs, variables


def make_path():
    return ''.join(random.choice(string.ascii_lowercase) for i in range(6))+'.nc'
