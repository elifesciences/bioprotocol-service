# Generated by Django 2.2.2 on 2019-06-24 05:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("bp", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="articleprotocol",
            name="protocol_status",
            field=models.IntegerField(),
        )
    ]