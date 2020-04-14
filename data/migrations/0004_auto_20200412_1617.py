# Generated by Django 3.0.3 on 2020-04-12 16:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0003_auto_20200412_1606'),
    ]

    operations = [
        migrations.AddField(
            model_name='variable',
            name='in_datasets',
            field=models.ManyToManyField(to='data.UC2Observation'),
        ),
        migrations.AlterField(
            model_name='uc2observation',
            name='upload_date',
            field=models.DateTimeField(default='2020-04-12 16:17:38'),
        ),
        migrations.RemoveField(
            model_name='variable',
            name='variable',
        ),
        migrations.AddField(
            model_name='variable',
            name='variable',
            field=models.CharField(default=1, max_length=32),
            preserve_default=False,
        ),
    ]
