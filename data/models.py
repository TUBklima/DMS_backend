#  import datetime
import uc2data
import pandas as pd

from django.db import models
from django.utils import timezone
#  from auth.serializers import UserSerializer

tab01 = pd.read_csv('http://www.uc2-program.org/uc2_table_A1.csv', sep="\t").reset_index()
tab02 = pd.read_csv('http://www.uc2-program.org/uc2_table_A2.csv', sep="\t").reset_index()
tab03 = pd.read_csv('http://www.uc2-program.org/uc2_table_A3.csv', sep="\t").reset_index()
tab04 = pd.read_csv('http://www.uc2-program.org/uc2_table_A4.csv', sep="\t").reset_index()

VARIABLE = [vari for vari in zip(tab01.iloc[:, 0], tab01.loc[:, 'variable'])]
DATA_CONTENT = [daco for daco in zip(tab02.iloc[:, 0], tab02.loc[:, 'data_content'])]
INSTITUTION = [inst for inst in zip(tab03.iloc[:, 0], tab03.loc[:, 'institution'])]
SITE = [site for site in zip(tab04.iloc[:, 0], tab04.loc[:, 'site'])]
LICENCE = [("test", "Choose a License"), ("UC2", "[UC]2 Open Licence")]


class DataFile(models.Model):
    input_name = models.CharField(max_length=200)
    file_id = models.CharField(max_length=200)
    file_path = models.FileField(max_length=200, null=False, unique=True, upload_to='files/')
    keywords = models.CharField(max_length=200)
    uploader = models.ManyToManyField("User")
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

    def upload(self):
        self.upload_date = timezone.now()

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
    acronym = models.CharField(max_length=10, default="Ups")
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
    dependencies = models.ForeignKey("DataFile", )

    def __str__(self):
        return self.variable_name
