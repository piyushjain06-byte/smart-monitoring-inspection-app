import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('registry', '0002_flatten_scheme_hierarchy'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SchemeApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('applicant_type', models.CharField(choices=[('NGO', 'NGO'), ('INSTITUTE', 'Institute')], max_length=20)),
                ('organization_name', models.CharField(max_length=255)),
                ('registration_number', models.CharField(blank=True, help_text='NGO registration number — required for NGO applications.', max_length=100)),
                ('contact_person', models.CharField(blank=True, max_length=255)),
                ('contact_phone', models.CharField(blank=True, max_length=15)),
                ('contact_email', models.EmailField(blank=True, max_length=254)),
                ('address', models.TextField(blank=True)),
                ('state', models.CharField(blank=True, max_length=100)),
                ('district', models.CharField(blank=True, max_length=100)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('project_name', models.CharField(max_length=255)),
                ('project_plan', models.TextField()),
                ('proposed_fund_amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('proposed_start_date', models.DateField(blank=True, null=True)),
                ('proposed_end_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING', max_length=10)),
                ('review_notes', models.TextField(blank=True, help_text="Government's notes/reason — shown to the applicant.")),
                ('approved_fund_amount', models.DecimalField(blank=True, decimal_places=2, help_text='Government can adjust the sanctioned amount on approval; defaults to the amount requested.', max_digits=14, null=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('applicant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheme_applications', to=settings.AUTH_USER_MODEL)),
                ('scheme', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='registry.scheme')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('created_ngo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='registry.ngo')),
                ('created_institute', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='registry.institute')),
                ('created_project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='registry.project')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
