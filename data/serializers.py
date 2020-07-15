
from collections import OrderedDict
from collections.abc import Mapping

import csv

from rest_framework import serializers

from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings
from rest_framework.utils import  model_meta
from data.models import *
from auth.models import User

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from django.core.files.uploadhandler import TemporaryUploadedFile


class LicenceSerializer(serializers.ModelSerializer):
    # TODO nicer serialisation of groups
    class Meta:
        model = License
        fields = "__all__"


class UC2Serializer(serializers.ModelSerializer):
    site = serializers.SlugRelatedField(slug_field='site', queryset=Site.objects.all())
    acronym = serializers.SlugRelatedField(slug_field='acronym', queryset=Institution.objects.all())
    variables = serializers.SlugRelatedField(slug_field='variable', queryset=Variable.objects.all(), many=True)
    uploader = serializers.SlugRelatedField(slug_field='username', queryset=User.objects.all())
    licence = serializers.SlugRelatedField(slug_field='short_name', queryset=License.objects.all())

    class Meta:
        model = UC2Observation
        fields = "__all__"


class VariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variable
        fields = "__all__"


class BaseListCsvSerializer(serializers.ListSerializer):

    def to_internal_value(self, data):
        '''
        Read a line from csv file -> split according to child definition
        + nice error recording
        :return:
        '''
        ret = []
        errors = []
        child_meta = self.child.Meta

        if 'file' not in data:
            raise ValidationError({'file': ['Field can not be empty']}, 'required')
        if not isinstance(data['file'], TemporaryUploadedFile):
            raise ValidationError({
                'file': ['File was not uploaded. '
                         'Are you using multipart/form-data as Content-Type in your request?']
            }, 'type')

        try:
            with open(data['file'].temporary_file_path(), 'r', encoding=child_meta.encoding) as csvfile:
                # read and compare header lines
                if child_meta.header:
                    if isinstance(child_meta.header, str):
                        header = [child_meta.header]
                    else:
                        header = child_meta.header

                    c = 0
                    for line in header:
                        file_line = csvfile.readline()
                        if line.strip() != file_line.strip():
                            message = "Error in Header line %s. " \
                                      "Expected line:'%s' but found:'%s'" % (c, line, file_line)
                            errors.append({api_settings.NON_FIELD_ERRORS_KEY: [message]})
                        c += 1

                if any(errors):
                    # if the Header is wrong we should not continue reading the file
                    raise ValidationError(errors)

                csvreader = csv.reader(csvfile, *child_meta.reader_args, **child_meta.reader_kwargs)
                c = 0

                for row in csvreader:
                    c += 1
                    new_elm = {}
                    ok = True
                    for key, value in child_meta.mapping.items():
                        try:
                            raw_val = row[value]
                        except IndexError:
                            ok = False
                            message = "Wrong number of separators in line %s" % c
                            errors.append({api_settings.NON_FIELD_ERRORS_KEY: [message]})
                            break

                        new_elm[key] = raw_val

                    if not ok:
                        continue  # we cannot run child validation if the line has wrong number of separators

                    try:
                        validated = self.child.run_validation(new_elm)
                    except ValidationError as exc:
                        errors.append({'line_%s' % c: exc.detail})
                    else:
                        ret.append(validated)

                if any(errors):
                    raise ValidationError(errors)
                return ret

        except UnicodeDecodeError:
            raise ValidationError({
                'file': ["The file is not encoded in %s" % child_meta.encoding]
            })
        except IOError:
            raise ValidationError({
                'file': ["An IOError occurred during file read"]
            })

        return ret


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
        many_to_many = {}
        identificator = []

    def __init__(self, *args, **kwargs):
        assert self.Meta.mapping, (
            "Mapping must be defined"
        )
        assert set(self.Meta.many_to_many.keys()).issubset(self.Meta.mapping.keys()), (
            "For all key in many to many a mapping must be defined"
        )
        super().__init__(*args, **kwargs)

    def _many_to_many(self, key, value):
        '''
        Parse a given string into a list of primary keys
        :return:
        '''
        mapping = self.Meta.many_to_many[key]
        if 'separator' in mapping:
            sep = mapping['separator']
        else:
            sep = ','

        if not isinstance(value, str):
            raise ValidationError(
                {key: ['Must be given as string']},
                'type')

        model = mapping['model']
        field = mapping['field']
        ret = []
        errors = []

        for elm in value.split(sep):
            if elm == '':
                continue
            try:
                query = {field: elm.strip()}
                obj = model.objects.get(**query)  # use dict + splash separator to dynamically query the model
                ret.append(obj.pk)
            except ObjectDoesNotExist:
                errors.append('Can not find %s ' % elm)
            except MultipleObjectsReturned:
                errors.append('%s is not a foreign key' % elm)
        return ret, errors

    def to_internal_value(self, data):
        many_mapping = self.Meta.many_to_many
        errors = []
        if many_mapping:
            for key in many_mapping:
                if key in data and isinstance(data[key], str):
                    val, err = self._many_to_many(key, data[key])
                    data[key] = val
                    if err:
                        errors.append(err)
        if errors:
            raise ValidationError(errors)
        return super().to_internal_value(data)


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
        fields = ["long_name", "standard_name", "units", "variable", "institution", "AMIP", "deprecated", "remarks"]
        header = "long_name	standard_name	units	variable	acronym	AMIP	deprecated	remarks"
        mapping = {
            'long_name': 0,
            'standard_name': 1,
            'units': 2,
            'variable': 3,
            'institution': 4,
            'AMIP': 5,
            'deprecated': 6,
            'remarks': 7
        }
        many_to_many = {
            'institution': {
                'model': Institution,
                'field': 'acronym'
            }
        }

    def create(self, validated_data):

        # does a variable with this long name exists ?
        obj = list(Variable.objects.filter(long_name=validated_data['long_name']).order_by('introduced_at'))
        if not obj:
            # No -> create the variable
            return super().create(validated_data)
        # matches the most recent variable and the variable we ar currently inserting
        current_obj = obj[0]
        validated_data['institution'] = [x.pk for x in validated_data['institution']]
        current_data = VariableCsvSerializer(current_obj).data

        # Do the foreign keys match ?
        if current_data == validated_data:
            # yes -> nothing to do
            return current_obj
        else:
            # set the old variables as deprecated and create a new one
            for old_obj in obj:
                old_obj.deprecated = True
                old_obj.save()
            return super().create(validated_data)
