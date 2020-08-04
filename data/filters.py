import django_filters as drf_filter
from data.models import UC2Observation, Variable


class ListFilter(drf_filter.BaseCSVFilter, drf_filter.CharFilter):
    def filter(self, qs, value):
        if not value:
            return qs
        base = None
        for v in value:
            if not base:
                base = super().filter(qs, v)
            else:
                base.union(super().filter(qs, v))
        return base


class UC2Filter(drf_filter.FilterSet):
    acronym = ListFilter(field_name="acronym__acronym", lookup_expr='icontains')

    file_standard_name = drf_filter.CharFilter(field_name='file_standard_name', lookup_expr='icontains')
    upload_date = drf_filter.DateFromToRangeFilter()
    creation_time = drf_filter.DateFromToRangeFilter()
    origin_time = drf_filter.DateFromToRangeFilter()

    class Meta:
        model = UC2Observation
        fields = {
            'data_type': ['exact'],
            'keywords': ['icontains'],
            'uploader': ['exact'],
            'author': ['exact'],
            'source': ['exact'],
            'institution': ['exact'],
            'is_invalid': ['exact'],
            'is_old': ['exact'],
            'version': ['exact', 'gt', 'lt'],
            'featureType': ['exact'],
            'data_content': ['exact'],
            'location': ['icontains'],
            'site__site': ['icontains'],
            'site__id': ['exact'],
            'origin_lon': ['exact'],
            'origin_lat': ['exact'],
            'campaign': ['exact'],
            'variables__id': ['exact'],
            'variables__variable': ['exact'],
            'variables__long_name': ['icontains'],
            'variables__standard_name': ['icontains'],
        }
