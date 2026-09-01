# Hand-written to match what `manage.py makemigrations analytics` would
# produce for the models below (no network access to run Django itself in
# the environment this was written in). Run `makemigrations analytics`
# yourself after pulling this in — Django will either say "No changes
# detected" or generate a tiny follow-up migration if anything here doesn't
# match exactly (e.g. the auto-generated index name).
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('registry', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RiskSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.PositiveSmallIntegerField(help_text='0-100, see apps.analytics.services.risk_engine')),
                ('severity', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')], max_length=10)),
                ('factors', models.JSONField(blank=True, default=list)),
                ('features', models.JSONField(blank=True, default=dict)),
                ('is_anomaly', models.BooleanField(default=False, help_text='Flagged by the Isolation Forest model (Part 23) as unusual vs. other institutes.')),
                ('anomaly_score', models.FloatField(blank=True, help_text='Raw Isolation Forest decision_function score; lower = more anomalous.', null=True)),
                ('computed_at', models.DateTimeField(auto_now_add=True)),
                ('institute', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='risk_snapshots', to='registry.institute')),
            ],
            options={
                'ordering': ['-computed_at'],
            },
        ),
        migrations.CreateModel(
            name='AIAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alert_type', models.CharField(choices=[('ATTENDANCE_MISMATCH', 'Attendance mismatch'), ('CCTV_OFFLINE', 'CCTV offline'), ('FAILED_INSPECTION', 'Failed inspection'), ('UNUSUAL_ATTENDANCE', 'Unusual attendance pattern'), ('REPEATED_ISSUES', 'Repeated issues')], max_length=30)),
                ('description', models.CharField(max_length=255)),
                ('risk_score', models.PositiveSmallIntegerField(help_text="Institute's overall score at the time this fired")),
                ('severity', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')], max_length=10)),
                ('status', models.CharField(choices=[('OPEN', 'Open'), ('ACKNOWLEDGED', 'Acknowledged'), ('RESOLVED', 'Resolved')], default='OPEN', max_length=15)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('institute', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_alerts', to='registry.institute')),
                ('snapshot', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='analytics.risksnapshot')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='risksnapshot',
            index=models.Index(fields=['institute', '-computed_at'], name='analytics_r_institu_1c9d0a_idx'),
        ),
    ]
