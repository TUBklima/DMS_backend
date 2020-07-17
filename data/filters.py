import django_filters
from data.models import UC2Observation, Variable


class UC2Filter(django_filters.FilterSet):
    acronym = django_filters.CharFilter(field_name="acronym__acronym")
    file_standard_name = django_filters.CharFilter(field_name='file_standard_name', lookup_expr='icontains')
    upload_date = django_filters.DateFromToRangeFilter()
    creation_time = django_filters.DateFromToRangeFilter()
    origin_time = django_filters.DateFromToRangeFilter()

    class Meta:
        model = UC2Observation
        fields = {
            'data_type': ['exact'],
            'keywords': ['icontains'],
            'uploader': ['exact'],
            'author': ['exact'],
            'source': ['exact'],
            'institution': ['icontains'],
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
