import django_filters
from data.models import UC2Observation, Variable


class UC2Filter(django_filters.FilterSet):
    # upload_year = django_filters.NumberFilter(field_name='upload_date', lookup_expr='year')
    # upload_year__gt = django_filters.NumberFilter(field_name='upload_date', lookup_expr='year__gt')
    # upload_year__lt = django_filters.NumberFilter(field_name='upload_date', lookup_expr='year__lt')
    #
    # manufacturer__name = django_filters.CharFilter(lookup_expr='icontains')
    class Meta:
        model = UC2Observation
        fields = {
            'data_type': ['exact'],
            'file_standard_name': ['icontains'],
            'keywords': ['icontains'],
            'uploader': ['exact'],
            'author': ['exact'],
            'source': ['exact'],
            'institution': ['exact'],
            'upload_date': ['exact', 'year__gt', 'year__lt'],
            'is_invalid': ['exact'],
            'is_old': ['exact'],
            'version': ['exact', 'gt', 'lt'],
            'featureType': ['exact'],
            'data_content': ['exact'],
            'location': ['icontains'],
            'site': ['icontains'],
            'origin_lon': ['exact'],
            'origin_lat': ['exact'],
            'campaign': ['exact'],
            # FIXME: These should refer to datetime fields
            'creation_time': ['exact'], # 'year__gt', 'year__lt'],
            'origin_time': ['exact'], # 'year__gt', 'year__lt'],
            'variables__variable': ['exact'],
            'variables__long_name': ['icontains'],
            'variables__standard_name': ['icontains'],
        }
