# accounts/management/commands/migrate_tool_data.py
#
# Run this ONCE after makemigrations + migrate:
#   python manage.py migrate_tool_data
#
# What it does:
#   1. Creates FieldAttribute rows for Boring Tool Holder and Milling Tool
#      (if they exist in your Field table)
#   2. Copies each ToolRequest's old hardcoded values (bore_size, diameter etc.)
#      into ToolRequestAttribute rows
#   3. Safe to re-run — skips records that already have attributes

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Migrates old hardcoded tool fields to the new dynamic FieldAttribute system'

    def handle(self, *args, **options):
        # Import here so Django app registry is ready
        from accounts.models import Field, FieldAttribute, ToolRequest, ToolRequestAttribute

        self.stdout.write("Starting data migration...\n")

        # ── STEP 1: Create FieldAttribute rows for known tool types ──

        boring_field = Field.all_objects.filter(
            field_name__iexact="BORING TOOL HOLDER"
        ).first()

        milling_field = Field.all_objects.filter(
            field_name__iexact="MILLING TOOL"
        ).first()

        if boring_field:
            boring_attrs = [
                ("Bore Size",    "number", True,  1),
                ("No. of Teeth", "number", True,  2),
                ("O/A Length",   "number", True,  3),
            ]
            for name, itype, required, order in boring_attrs:
                obj, created = FieldAttribute.objects.get_or_create(
                    field=boring_field,
                    attr_name=name,
                    defaults={
                        'input_type':  itype,
                        'is_required': required,
                        'order':       order,
                    }
                )
                status = "created" if created else "already exists"
                self.stdout.write(f"  Boring → {name}: {status}")
        else:
            self.stdout.write("  WARNING: 'BORING TOOL HOLDER' field not found — skipping")

        if milling_field:
            milling_attrs = [
                ("Diameter",       "number", True,  1),
                ("No. of Teeth",   "number", True,  2),
                ("Overall Length", "number", True,  3),
            ]
            for name, itype, required, order in milling_attrs:
                obj, created = FieldAttribute.objects.get_or_create(
                    field=milling_field,
                    attr_name=name,
                    defaults={
                        'input_type':  itype,
                        'is_required': required,
                        'order':       order,
                    }
                )
                status = "created" if created else "already exists"
                self.stdout.write(f"  Milling → {name}: {status}")
        else:
            self.stdout.write("  WARNING: 'MILLING TOOL' field not found — skipping")

        # ── STEP 2: Migrate existing ToolRequest data ──

        self.stdout.write("\nMigrating existing ToolRequest records...")

        # Check if old columns still exist in DB
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(accounts_toolrequest)" if 'sqlite' in connection.settings_dict['ENGINE']
                          else "SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name='accounts_toolrequest'")
            columns = [row[1] if 'sqlite' in connection.settings_dict['ENGINE'] else row[0]
                      for row in cursor.fetchall()]

        has_old_columns = 'bore_size' in columns

        if not has_old_columns:
            self.stdout.write("  Old columns not found — migration already done or not needed.")
        else:
            migrated = 0
            skipped  = 0

            for req in ToolRequest.objects.all():
                # Skip if this request already has attributes
                if req.attributes.exists():
                    skipped += 1
                    continue

                desc_name = req.description.field_name.upper() if req.description else ""

                # Use raw SQL to read old column values safely
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT bore_size, boring_teeth, boring_length, diameter, milling_teeth, milling_length "
                        "FROM accounts_toolrequest WHERE id = %s",
                        [req.id]
                    )
                    row = cursor.fetchone()

                if not row:
                    continue

                bore_size, boring_teeth, boring_length, diameter, milling_teeth, milling_length = row

                if desc_name == "BORING TOOL HOLDER" and boring_field:
                    attr_map = {
                        "Bore Size":    bore_size,
                        "No. of Teeth": boring_teeth,
                        "O/A Length":   boring_length,
                    }
                    for attr_name, value in attr_map.items():
                        if value:
                            fa = FieldAttribute.objects.filter(
                                field=boring_field, attr_name=attr_name
                            ).first()
                            ToolRequestAttribute.objects.create(
                                tool_request    = req,
                                field_attribute = fa,
                                attr_name       = attr_name,
                                value           = str(value),
                            )
                    migrated += 1

                elif desc_name == "MILLING TOOL" and milling_field:
                    attr_map = {
                        "Diameter":       diameter,
                        "No. of Teeth":   milling_teeth,
                        "Overall Length": milling_length,
                    }
                    for attr_name, value in attr_map.items():
                        if value:
                            fa = FieldAttribute.objects.filter(
                                field=milling_field, attr_name=attr_name
                            ).first()
                            ToolRequestAttribute.objects.create(
                                tool_request    = req,
                                field_attribute = fa,
                                attr_name       = attr_name,
                                value           = str(value),
                            )
                    migrated += 1

            self.stdout.write(f"  Migrated: {migrated} records")
            self.stdout.write(f"  Skipped (already done): {skipped} records")

        self.stdout.write("\nMigration complete!")
        self.stdout.write("You can now remove bore_size, diameter etc. from models.py if desired.")