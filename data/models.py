# models.py django python file
from django.db import models
from django.utils import timezone, dateformat
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_save, pre_save


class License(models.Model):

    @staticmethod
    def pre_create(sender, instance, *args, **kwargs):
        Group.objects.get_or_create(name=instance.short_name)

    short_name = models.CharField(max_length=128, unique=True)
    full_text = models.CharField(max_length=256, unique=True)
    public = models.BooleanField(default=False)
    view_groups = models.ManyToManyField(Group)  # groups that get the view permission aka groups that are allowed to downlaod / view the file
    view_permission = models.ForeignKey(Permission, on_delete=models.PROTECT)

    def __str__(self):
        return self.short_name


pre_save.connect(License.pre_create, sender=License)


class InstitutionManager(models.Manager):
    def get_by_natural_key(self, acronym=None):
        return self.get(acronym=acronym)


class Institution(models.Model):

    objects = InstitutionManager()

    @staticmethod
    def post_create(sender, instance, created, *args, **kwargs):
        if not created:
            return
        Group.objects.get_or_create(name=instance.acronym)

    ge_title = models.CharField(max_length=256, unique=True)
    en_title = models.CharField(max_length=256, unique=True)
    acronym = models.CharField(max_length=64, unique=True)

    def natural_key(self):
        return [self.acronym]


post_save.connect(Institution.post_create, sender=Institution)


class DataFile(models.Model):
    data_type = models.CharField(max_length=200)
    file_standard_name = models.CharField(max_length=200, unique=True)
    file = models.FileField()
    keywords = models.CharField(max_length=200, blank=True, default='')
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    author = models.CharField(max_length=200)
    source = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    acronym = models.ForeignKey(Institution, on_delete=models.PROTECT, to_field='acronym')

    licence = models.ForeignKey(License, on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)
    upload_date = models.DateTimeField(auto_now_add=True)
    download_count = models.PositiveIntegerField(default=0)
    is_invalid = models.BooleanField(default=False)
    is_old = models.BooleanField(default=False)
    has_warnings = models.BooleanField(default=False)
    has_errors = models.BooleanField(default=False)

    def __str__(self):
        return self.file_standard_name

    def __file_path__(self):
        return self.file_path.value_from_object(self)

    class Meta:
        abstract = True


class VariableManger(models.Manager):

    def get_by_natural_key(self, long_name):
        return self.get(long_name=long_name)


class Variable(models.Model):

    objects = VariableManger()

    variable = models.CharField(max_length=32)  # Is not unique because deprecate var can exist
    institution = models.ManyToManyField(Institution, blank=True)  # The institutions for which this was introduced
    long_name = models.CharField(max_length=200)
    standard_name = models.CharField(max_length=200, blank=True, default='')
    units = models.CharField(max_length=32)
    AMIP = models.BooleanField()
    deprecated = models.BooleanField()
    remarks = models.CharField(max_length=200, blank=True, default='')
    introduced_at = models.DateField(auto_now_add=True)
    deprecated_at = models.DateField(auto_now=True)

    def natural_key(self):
        return [self.long_name]

    def __str__(self):
        return self.variable


class Site(models.Model):
    IOP = "IOP"
    LTO = "LTO"
    WT = 'WT'
    IOP_LTO = "LTO, IOP"

    location = models.CharField(max_length=32)
    site = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    institution = models.ManyToManyField(Institution)
    campaign = models.CharField(max_length=10, choices=[
        (IOP, "intensive observation period"),
        (LTO, "long term observation"),
        (WT, 'wind'),
        (IOP_LTO, "intensive observation period, long term observation")
    ])
    remarks = models.CharField(max_length=200, blank=True, default='')


class UC2Observation(DataFile):
    featureType = models.CharField(max_length=32)
    data_content = models.CharField(max_length=200)
    # spatial atts
    location = models.CharField(max_length=3)
    site = models.ForeignKey(Site, to_field='site', on_delete=models.PROTECT)
    origin_lon = models.FloatField()
    origin_lat = models.FloatField()
    # time atts
    campaign = models.CharField(max_length=6)

    creation_time = models.DateTimeField()
    origin_time = models.DateTimeField()

    ll_lon = models.FloatField(help_text="longitude of lower left corner of bounding rectangle")
    ll_lat = models.FloatField(help_text="latitude of lower left corner of bounding rectangle")
    ur_lon = models.FloatField(help_text="longitude of upper right corner of bounding rectangle")
    ur_lat = models.FloatField(help_text="latitude of upper right corner of bounding rectangle")
    lat_lon_epsg = models.CharField(max_length=16, help_text="epsg code for lon / lat coordinates")
    ll_n_utm = models.FloatField(help_text="north utm of lower left corner of bounding rectangle")
    ll_e_utm = models.FloatField(help_text="eastern utm of lower left corner of bounding rectangle")
    ur_n_utm = models.FloatField(help_text="north utm of upper right corner of bounding rectangle")
    ur_e_utm = models.FloatField(help_text="eastern utm of upper right corner of bounding rectangle")
    utm_epsg = models.CharField(max_length=16, help_text="epsg code for utm coordinates")

    # variables
    variables = models.ManyToManyField(Variable, related_name='datasets')
