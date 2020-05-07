#  from collections.abc import Iterable
from collections import OrderedDict
import csv

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from data.models import *


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
        for elm in initial_data:
            obj = self.child.__class__(data=elm)
            try:
                # try to serialize a line -> should only give unique Errors for lines we already know about
                obj.is_valid(raise_exception=True)
                new_objs.append(elm)
            except ValidationError as exc:
                # it is not an error when the only occurring errors are unique errors for all mapping keys
                # this just means the object is already there
                needed_keys = set(self.child.Meta.mapping.keys())
                all_new = True
                some_seen = False
                for key in self.child.Meta.mapping:
                    if key in exc.detail:
                        key_errors = exc.detail[key]
                        for e in key_errors:
                            if e.code == 'unique':
                                all_new = False
                                some_seen = True
                                exc.detail[key].remove(e)
                                needed_keys.remove(key)
                        if not exc.detail[key]:
                            exc.detail.pop(key)
                if not all_new and some_seen and needed_keys:
                    exc.detail['wrong_csv_entry'+str(c)] = \
                        "A entry matches partly an existing entry " \
                        "but differs in some fields the offending entry is in line " + str(c)
                if exc.detail:
                    for key, item in exc.detail.items():
                        self._errors[key] = item
            c += 1

        if self._raise_exception(raise_exception):
            return False

        self.initial_data = new_objs
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
        reader_kwargs = {}
        mapping = None


class InstitutionSerializer(BaseCsvSerializer):
    class Meta(BaseCsvSerializer.Meta):
        model = Institution
        fields = '__all__'
        header = 'institution	acronym	offical English title'
        reader_kwargs = {
            'delimiter': '\t',
            'quotechar': '"'
        }
        mapping = {
            'ge_title': 0,
            'en_title': 2,
            'acronym': 1
        }

