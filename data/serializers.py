#  from collections.abc import Iterable
from collections import OrderedDict
import csv

from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework.exceptions import ValidationError

from data.models import *

from django.core.exceptions import ObjectDoesNotExist

class BaseSerializer(serializers.ModelSerializer):
    #  @classmethod
    #  def many_init(cls, *args, **kwargs):
    #      return cls(*args, **kwargs)

    #  def to_representation(self, instance):
    #      if isinstance(instance, Iterable):
    #          res = {}
    #          for i in instance:
    #              rep = super().to_representation(i)
    #              res[rep.pop("id")] = rep
    #      else:
    #          rep = super().to_representation(instance)
    #          res = {rep.pop("id"): rep}

    #      # key = self.Meta.model._meta.verbose_name_plural.title().lower()
    #      return res

    class Meta:
        model = DataFile
        fields = (
            "data_type",
            "file",
            "version",
        )


class LicenceSerializer(serializers.ModelSerializer):
    # TODO nicer serialisation of groups
    class Meta:
        model = License
        fields = "__all__"


class UC2Serializer(BaseSerializer):
    site = serializers.SlugRelatedField(slug_field='site', queryset=Site.objects.all())
    acronym = serializers.SlugRelatedField(slug_field='acronym', queryset=Institution.objects.all())
    variables = serializers.SlugRelatedField(slug_field='variable', queryset=Variable.objects.all(), many=True)

    class Meta:
        model = UC2Observation
        fields = "__all__"


class VariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variable
        fields = "__all__"


class BaseListCsvSerializer(serializers.ListSerializer):

    def _raise_exception(self, raise_exception):
        if self._errors and raise_exception:
            raise ValidationError(self.errors)
        elif self._errors:
            return True
        else:
            return False

    def is_valid(self, raise_exception=False):

        self._errors = {}
        if 'file' not in self.initial_data:
            self._errors['missing_file_field'] = 'A field named file must be present in the request'

        if self._raise_exception(raise_exception):
            return False

        # read the csv file
        initial_data = self.to_initial_data()

        # find new lines from csv
        new_objs = []
        c = 0
        # find fields with a unique validator
        unique_keys = set()
        for key, field in self.child.fields.items():
            if hasattr(field, 'validators'):
                if any([isinstance(x, UniqueValidator) for x in field.validators]):
                    unique_keys.add(key)

        for elm in initial_data:
            obj = self.child.__class__(data=elm)
            try:
                # try to serialize a line -> should only give unique Errors for lines we already know about
                obj.is_valid(raise_exception=True)
                new_objs.append(elm)
            except ValidationError as exc:
                # it is not an error when the only occurring errors are unique errors for ALL unique validators
                # this just means the object is already there
                unique_errors = set()
                other_errors = False
                entry_exist_error = False
                for key in exc.detail:
                    if not type(key) == str:
                        other_errors = True
                        continue
                    key_errors = exc.detail[key]
                    for e in key_errors:
                        if e.code == 'unique':
                            unique_errors.add(key)
                        else:
                            other_errors = True

                if unique_errors and not unique_keys == unique_errors:
                    entry_exist_error = True
                    exc.detail['wrong_csv_entry_'+str(c)] = \
                        "A entry matches partly an existing entry " \
                        "but differs in some fields the offending entry is in line " + str(c)

                if other_errors or entry_exist_error:
                    if type(exc.detail) == list:
                        if 'list' not in self._errors:
                            self._errors['list'] = []
                        self._errors['list'].extend(exc.detail)
                    else:
                        for key, item in exc.detail.items():
                            self._errors[key] = item
            c += 1

        if self._raise_exception(raise_exception):
            return False

        self.initial_data = new_objs

        if not self._errors:
            delattr(self, '_errors')

        return super().is_valid(raise_exception=raise_exception)

    def to_initial_data(self):
        read_data = None
        child_meta = self.child.Meta
        try:
            with open(self.initial_data['file'].temporary_file_path(), 'r', encoding=child_meta.encoding) as csvfile:
                errors = OrderedDict()
                if child_meta.header:
                    if isinstance(child_meta.header, str):
                        header = [self.child.Meta.header]
                    else:
                        header = self.child.Meta.header

                    c = 0
                    for line in header:
                        file_line = csvfile.readline()
                        if line != file_line:
                            errors['header_line'+str(c)] = "Expected line:'"+line+"' but found:'"+file_line
                        c += 1

                read_data = []
                csvreader = csv.reader(csvfile, *child_meta.reader_args, **child_meta.reader_kwargs)
                c = 0
                for row in csvreader:
                    new_elm = {}
                    try:
                        for key, value in child_meta.mapping.items():
                            new_elm[key] = row[value]
                        read_data.append(new_elm)
                    except IndexError:
                            self.errors['wrong_column_count_'+str(c)] = "Wrong number of separators in line "+str(c)
                    c += 1
        except UnicodeDecodeError:
            self._errors['wrong_encoding'] = "The expected encoding is "+child_meta.encoding
            return None
        except IOError:
            self._errors["can_not_read"] = "The uploaded stream is not readable."
            return None
        return read_data


class BaseCsvSerializer(serializers.ModelSerializer):

    class Meta:
        list_serializer_class = BaseListCsvSerializer
        encoding = 'utf-8'
        header = None
        reader_args = []
        reader_kwargs = {
            'delimiter': '\t',
            'quotechar': '"'
        }
        mapping = None
        many_to_many = []

    def is_valid(self, raise_exception=False):
        for key in self.Meta.many_to_many:
            if key not in self.initial_data:
                raise ValidationError(key + ' field can not be empty', 'required')
            if not isinstance(self.initial_data[key], str):
                raise ValidationError(key + ' must be given as string', 'type')

            # Handle many to many relationship
            orig_str = self.initial_data.pop(key)
            self.initial_data[key] = []
            if 'separator' in self.Meta.many_to_many[key]:
                sep = self.Meta.many_to_many[key]['separator']
            else:
                sep = ','

            missing_elms = []
            model = self.Meta.many_to_many[key]['model']
            field = self.Meta.many_to_many[key]['field']

            for elm in orig_str.split(sep):
                if elm == '':
                    continue
                try:
                    query = {field: elm.strip()}
                    obj = model.objects.get(**query)  # use dict + splash separator to dynamically query the model

                    self.initial_data[key].append(obj.pk)
                except ObjectDoesNotExist:
                    missing_elms.append(elm)

            if missing_elms:
                raise ValidationError(
                    'The field "' + field + '" has the following missing elements : ' + ", ".join(missing_elms))

        return super().is_valid(raise_exception=raise_exception)


class InstitutionSerializer(BaseCsvSerializer):
    class Meta(BaseCsvSerializer.Meta):
        model = Institution
        fields = '__all__'
        header = 'institution	acronym	offical English title'
        mapping = {
            'ge_title': 0,
            'en_title': 2,
            'acronym': 1
        }


class SiteSerializer(BaseCsvSerializer):

    class Meta(BaseCsvSerializer.Meta):
        model = Site
        fields = '__all__'
        header = "location	site	description	address	acronym	campaign	remarks"
        mapping = {
            'location': 0,
            'site': 1,
            'description': 2,
            'address': 3,
            'institution': 4,
            'campaign': 5,
            'remarks': 6
        }
        many_to_many = {
            'institution': {
                'model': Institution,
                'field': 'acronym'
            }
        }


class VariableCsvSerializer(BaseCsvSerializer):
    class Meta(BaseCsvSerializer.Meta):
        model = Variable
        fields = '__all__'
        header = "long_name	standard_name	units	variable	acronym	AMIP	remarks"
        mapping = {
            'long_name': 0,
            'standard_name': 1,
            'units': 2,
            'variable': 3,
            'institution': 4,
            'AMIP': 5,
            'remarks': 6
        }
        many_to_many = {
            'institution': {
                'model': Institution,
                'field': 'acronym'
            }
        }
