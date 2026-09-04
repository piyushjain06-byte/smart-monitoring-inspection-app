# Hand-written migration for the architecture fix:
#   Scheme -> NGO -> Institute -> Project   (wrong)
#   Scheme -> { NGO, Institute, Project }   (correct)
#
# Drops Institute.ngo and Project.institute; adds NGO.scheme and
# Project.scheme (Institute.scheme already existed).
#
# NOTE ON EXISTING DATA: this repo runs on local SQLite dev data (see
# README.md / .gitignore — db.sqlite3 is not committed). The `default=1`
# below is only a placeholder so Django can add the new NOT NULL columns
# on ANY existing rows; if you have real NGO/Project rows you care about,
# either back them up and reassign scheme_id by hand afterwards, or —
# simplest for a dev DB — delete db.sqlite3 and re-run `migrate` from a
# clean slate (this migration will then just run against empty tables).
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0001_initial'),
    ]

    operations = [
        # --- Drop the old (wrong) nested links ---
        migrations.RemoveField(model_name='institute', name='ngo'),
        migrations.RemoveField(model_name='historicalinstitute', name='ngo'),
        migrations.RemoveField(model_name='project', name='institute'),
        migrations.RemoveField(model_name='historicalproject', name='institute'),

        # --- Add the new flattened links: NGO and Project reference Scheme directly ---
        migrations.AddField(
            model_name='ngo',
            name='scheme',
            field=models.ForeignKey(
                default=1, on_delete=django.db.models.deletion.CASCADE,
                related_name='ngos', to='registry.scheme',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalngo',
            name='scheme',
            field=models.ForeignKey(
                blank=True, db_constraint=False, default=1, null=True,
                on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='registry.scheme',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='project',
            name='scheme',
            field=models.ForeignKey(
                default=1, on_delete=django.db.models.deletion.CASCADE,
                related_name='projects', to='registry.scheme',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalproject',
            name='scheme',
            field=models.ForeignKey(
                blank=True, db_constraint=False, default=1, null=True,
                on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='registry.scheme',
            ),
            preserve_default=False,
        ),
    ]
