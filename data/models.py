#  import datetime
import uc2data
import pandas as pd
import random
import string
from pathlib import Path

from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User

tab01 = pd.read_csv('http://www.uc2-program.org/uc2_table_A1.csv', sep="\t").reset_index()
tab02 = pd.read_csv('http://www.uc2-program.org/uc2_table_A2.csv', sep="\t").reset_index()
tab03 = pd.read_csv('http://www.uc2-program.org/uc2_table_A3.csv', sep="\t").reset_index()
tab04 = pd.read_csv('http://www.uc2-program.org/uc2_table_A4.csv', sep="\t").reset_index()

VARIABLE = [vari for vari in zip(tab01.iloc[:, 0], tab01.loc[:, 'variable'])]
DATA_CONTENT = [daco for daco in zip(tab02.iloc[:, 0], tab02.loc[:, 'data_content'])]
INSTITUTION = [inst for inst in zip(tab03.loc[:, 'institution'], tab03.loc[:, 'institution'])]
SITE = [site for site in zip(tab04.iloc[:, 0], tab04.loc[:, 'site'])]
LICENCE = [("test", "Choose a License"), ("UC2", "[UC]2 Open Licence")]
DATA_TYPE = [
    ("", "What data type do you want to upload?"),
    ("UC2Obs", "UC2Observation"),
    ("UC2Mod", "UC2Model"),
    ("sta_dr", "Static Driver"),
    ("dyn_in", "Dynamic Driver"),
]


class DataFile(models.Model):
    data_type = models.CharField(max_length=200, choices=DATA_TYPE, default=None)
    input_name = models.CharField(max_length=200)
    file_id = models.CharField(max_length=200)
    file_path = models.FileField(max_length=200, null=False, unique=True, upload_to='files/', default=settings.BASE_DIR)
    keywords = models.CharField(max_length=200)
    uploader = models.ManyToManyField(User)
    author = models.CharField(max_length=200)
    source = models.CharField(max_length=200)
    institution = models.CharField(max_length=200, choices=INSTITUTION, default=None)
    version = models.PositiveIntegerField(default=1)
    upload_date = models.DateTimeField('upload_date', default=timezone.now)
    download_count = models.PositiveIntegerField(default=0)
    licence = models.CharField(max_length=200, default="[UC]2 Open Licence")
    is_invalid = models.BooleanField(null=False, default=False)
    is_old = models.BooleanField(null=False, default=False)

    def __str__(self):
        return self.input_name

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
    feature_type = models.CharField(max_length=32, choices=FEATURE_TYPE, default=None)
    data_content = models.CharField(max_length=200)
    version = models.PositiveSmallIntegerField(default=1)
    acronym = models.CharField(max_length=10, default=None)
    # spatial atts
    location = models.CharField(max_length=3, default="B")
    site = models.CharField(max_length=12, default=None)
    #  origin_x = models.FloatField()
    #  origin_y = models.FloatField()
    #  origin_z = models.FloatField()
    origin_lon = models.FloatField(default=None)
    origin_lat = models.FloatField(default=None)
    # time atts
    campaign = models.CharField(max_length=6, choices=CAMPAIGN, default=CAMPAIGN[0])
    creation_time = models.CharField('creation_time', max_length=23, default=timezone.now)
    origin_time = models.CharField(max_length=23, default=timezone.now)

    def __str__(self):
        # TODO remove version from def __str__ as it will be part of filename_autogen
        return self.file_id + '_' + str(self.version)


class Variable(models.Model):
    variable_name = models.CharField(max_length=32)
    long_name = models.CharField(max_length=200)
    standard_name = models.CharField(max_length=200)
    data_file = models.ForeignKey(UC2Observation, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.variable_name


def make_path():
    return ''.join(random.choice(string.ascii_lowercase) for i in range(6))+'.nc'


def get_file_info(new_filename):
    base_dir = Path(settings.BASE_DIR)
    to_open = base_dir / DataFile.file_path.field.generate_filename(DataFile.file_path.instance, new_filename)
    with uc2data.Dataset(to_open) as f:
        if "UC2" in DataFile.data_type:
            f.uc2_check()
            if len(f.check_result.warnings):
                has_warning = True
            if len(f.check_result.errors):
                raise Exception(f.ds.check_result.errors)
        return f.ds.attrs, f.ds.data_vars, has_warning


