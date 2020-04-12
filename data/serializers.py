#  from collections.abc import Iterable

from rest_framework import serializers

from data.models import DataFile, UC2Observation, Variable


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


class UC2Serializer(BaseSerializer):
    class Meta:
        model = UC2Observation
        # fields = ("file", "campaign", "creation_time")
        fields = "__all__"


class VariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variable
        fields = "__all__"
