# Generated by Django 4.1.4 on 2022-12-15 10:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('django_nordigen', '0003_account'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('nordigen_id', models.CharField(max_length=32, unique=True)),
                ('api_data', models.JSONField()),
                ('booking_date', models.DateField(null=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='django_nordigen.account')),
            ],
            options={
                'abstract': False,
                'ordering': ['-booking_date'],
            },
        ),
    ]
