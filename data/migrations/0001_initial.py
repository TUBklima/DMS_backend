# Generated by Django 3.0.3 on 2020-02-27 17:49

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UC2Observation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('input_name', models.CharField(max_length=200)),
                ('file_id', models.CharField(max_length=200)),
                ('keywords', models.CharField(max_length=200)),
                ('author', models.CharField(max_length=200)),
                ('source', models.CharField(max_length=200)),
                ('institution', models.CharField(choices=[(0, 'Amt für Umweltschutz Stuttgart, Abteilung Stadtklimatologie'), (1, 'Climate Service Center Germany GERICS am Helmholtz-Zentrum Geesthacht'), (2, 'BKR Aachen Noky & Simon'), (3, 'Deutscher Wetterdienst'), (4, 'Deutscher Wetterdienst, Geschäftsbereich Klima und Umwelt, Abteilung Klima- und Umweltberatung'), (5, 'Deutscher Wetterdienst, Geschäftsbereich Klima und Umwelt, Abteilung Klima- und Umweltberatung, Regionales Klimabüro Essen'), (6, 'Deutscher Wetterdienst, Geschäftsbereich Klima und Umwelt, Abteilung Klima- und Umweltberatung, Zentrum für Medizin-Meteorologische Forschung'), (7, 'Deutscher Wetterdienst, Geschäftsbereich Klima und Umwelt, Abteilung Klima- und Umweltberatung, Zentrales Klimabüro'), (8, 'Deutscher Wetterdienst, Geschäftsbereich Forschung und Entwicklung, Meteorologisches Observatorium Lindenberg'), (9, 'Deutsches Institut für Urbanistik Köln'), (10, 'Deutsches Zentrum für Luft- und Raumfahrt'), (11, 'Deutsches Zentrum für Luft- und Raumfahrt, Deutsches Fernerkundungsdatenzentrum'), (12, 'Deutsches Zentrum für Luft- und Raumfahrt, Institut für Physik der Atmosphäre'), (13, 'Forschungsinstitut für Wasser- und Abfallwirtschaft an der RWTH Aachen'), (14, 'Forschungszentrum Jülich GmbH'), (15, 'Forschungszentrum Jülich GmbH, Institut für Energie- und Klimaforschung, IEK-8: Troposphäre'), (16, 'Fraunhofer-Institut für Bauphysik'), (17, 'Fraunhofer-Institut für Bauphysik, Hygrothermik'), (18, 'Freie Universität Berlin'), (19, 'Freie Universität Berlin, Institut für Meteorologie'), (20, 'GEO-NET Umweltconsulting GmbH'), (21, 'Hochschule Offenburg'), (22, 'Humboldt-Universität zu Berlin'), (23, 'Humboldt-Universität zu Berlin, Geographisches Institut'), (24, 'Ingenieursgesellschaft Prof. Sieker mbH'), (25, 'Institut für transformative Nachhaltigkeitsforschung'), (26, 'Karlsruher Institut für Technologie'), (27, 'Karlsruher Institut für Technologie, Institut für Meteorologie und Klimaforschung'), (28, 'Karlsruher Institut für Technologie, Institut für Meteorologie und Klimaforschung, Atmosphärische Aerosolforschung'), (29, 'Karlsruher Institut für Technologie, Institut für Meteorologie und Klimaforschung, Institut für Atmosphärische Umweltforschung'), (30, 'Karlsruher Institut für Technologie, Institut für Meteorologie und Klimaforschung, Troposphärenforschung'), (31, 'Leibniz Universität Hannover'), (32, 'Leibniz Universität Hannover, Institut für Meteorologie und Klimatologie'), (33, 'Senatsverwaltung für Stadtentwicklung und Wohnen Berlin'), (34, 'Senatsverwaltung für Umwelt, Verkehr und Klimaschutz Berlin'), (35, 'Technische Universität Berlin'), (36, 'Technische Universität Berlin, Fachgebiet Klimatologie'), (37, 'Technische Universität Braunschweig'), (38, 'Technische Universität Braunschweig, Institut für Geoökologie, Klimatologie und Umweltmeteorologie'), (39, 'Technische Universität Dortmund'), (40, 'Technische Universität Dortmund, Sozialforschungsstelle'), (41, 'Technische Universität Dresden'), (42, 'Technische Universität Dresden, Professur für Meteorologie'), (43, 'Universität Augsburg'), (44, 'Universität Augsburg, Institut für Geographie'), (45, 'Universität Hamburg'), (46, 'Universität Hamburg, Meteorologisches Institut'), (47, 'Universität Stuttgart'), (48, 'Universität Stuttgart, Institut für Feuerungs- und Kraftwerkstechnik')], default=None, max_length=200)),
                ('upload_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='upload_date')),
                ('download_count', models.PositiveIntegerField(default=0)),
                ('licence', models.CharField(default='[UC]2 Open Licence', max_length=200)),
                ('feature_type', models.CharField(choices=[(None, 'Not set (only allowed for multidimensional data)'), ('timeSeries', 'timeSeries'), ('timeSeriesProfile', 'timeSeriesProfile'), ('trajectory', 'trajectory')], default=None, max_length=32)),
                ('data_content', models.CharField(max_length=200)),
                ('version', models.PositiveSmallIntegerField(default=1)),
                ('acronym', models.CharField(default='Ups', max_length=10)),
                ('location', models.CharField(default='B', max_length=3)),
                ('site', models.CharField(default=None, max_length=12)),
                ('origin_lon', models.FloatField(default=None)),
                ('origin_lat', models.FloatField(default=None)),
                ('campaign', models.CharField(choices=[('IOP01', 'IOP01'), ('IOP02', 'IOP02'), ('IOP03', 'IOP03'), ('IOP04', 'IOP04'), ('VALR01', 'VALR01')], default=('IOP01', 'IOP01'), max_length=6)),
                ('creation_time', models.CharField(default=django.utils.timezone.now, max_length=23, verbose_name='creation_time')),
                ('origin_time', models.CharField(default=django.utils.timezone.now, max_length=23)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Variable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variable_name', models.CharField(max_length=32)),
                ('long_name', models.CharField(max_length=200)),
                ('standard_name', models.CharField(max_length=200)),
                ('data_file', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='data.UC2Observation')),
            ],
        ),
    ]