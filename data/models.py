# models.py django python file
from django.db import models
from django.utils import timezone, dateformat
from django.conf import settings


class DataFile(models.Model):
    data_type = models.CharField(max_length=200)
    file_standard_name = models.CharField(max_length=200, unique=True)
    file = models.FileField(null=False, blank=False)
    keywords = models.CharField(max_length=200, null=True, blank=False)
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
    origin_lon = models.FloatField(default=0.0)
    origin_lat = models.FloatField(default=0.0)
    # time atts
    campaign = models.CharField(max_length=6)
    # FIXME: These should be to datetime fields
    creation_time = models.CharField(max_length=23)
    origin_time = models.CharField(max_length=23)

    ll_lon = models.FloatField(null=False, help_text="longitude of lower left corner of bounding rectangle")
    ll_lat = models.FloatField(null=False, help_text="latitude of lower left corner of bounding rectangle")
    ur_lon = models.FloatField(null=False, help_text="longitude of upper right corner of bounding rectangle")
    ur_lat = models.FloatField(null=False, help_text="latitude of upper right corner of bounding rectangle")
    lat_lon_epsg = models.CharField(max_length=16, help_text="epsg code for lon / lat coordinates")
    ll_n_utm = models.FloatField(null=False, help_text="north utm of lower left corner of bounding rectangle")
    ll_e_utm = models.FloatField(null=False, help_text="eastern utm of lower left corner of bounding rectangle")
    ur_n_utm = models.FloatField(null=False, help_text="north utm of upper right corner of bounding rectangle")
    ur_e_utm = models.FloatField(null=False, help_text="eastern utm of upper right corner of bounding rectangle")
    utm_epsg = models.CharField(max_length=16, help_text="epsg code for utm coordinates")

    # variables
    variables = models.ManyToManyField(Variable, related_name='datasets')
