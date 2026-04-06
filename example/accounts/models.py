from django.db import models
from django.contrib.auth.models import User


# ─────────────────────────────────────────
# USER PROFILE
# ─────────────────────────────────────────

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin',    'Admin'),
        ('approver', 'Approver'),
        ('user',     'User'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return self.user.username


# ─────────────────────────────────────────
# SOFT DELETE
# ─────────────────────────────────────────

class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    is_deleted  = models.BooleanField(default=False)
    objects     = ActiveManager()
    all_objects = models.Manager()

    def soft_delete(self):
        self.is_deleted = True
        self.save()

    def restore(self):
        self.is_deleted = False
        self.save()

    class Meta:
        abstract = True


# ─────────────────────────────────────────
# FIELD MASTER
# ─────────────────────────────────────────

class Field(SoftDeleteModel):
    field_name      = models.CharField(max_length=200)
    short_code      = models.CharField(max_length=10)
    field_size_type = models.CharField(max_length=50)
    field_size      = models.IntegerField()
    field_message   = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.field_name


# ─────────────────────────────────────────
# FIELD ATTRIBUTE
# ─────────────────────────────────────────

class FieldAttribute(SoftDeleteModel):
    INPUT_TYPES = (
        ('number', 'Number'),
        ('text',   'Text'),
        ('select', 'Select (Fixed Values)'),
    )
    field       = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='attributes')
    attr_name   = models.CharField(max_length=100)
    input_type  = models.CharField(max_length=20, choices=INPUT_TYPES, default='number')
    is_required = models.BooleanField(default=True)
    order       = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.field.field_name} -> {self.attr_name}"


# ─────────────────────────────────────────
# FIELD FIXED VALUE
# ─────────────────────────────────────────

class FieldFixedValue(SoftDeleteModel):
    field       = models.ForeignKey(Field, on_delete=models.CASCADE)
    fixed_value = models.CharField(max_length=200)
    explanation = models.CharField(max_length=300)

    def __str__(self):
        return self.fixed_value


# ─────────────────────────────────────────
# MASTER DATA
# ─────────────────────────────────────────

class Supplier(SoftDeleteModel):
    supplier_name          = models.CharField(max_length=100)
    supplier_ordering_code = models.CharField(max_length=50)

    def __str__(self):
        return self.supplier_name


class RawMaterial(SoftDeleteModel):
    raw_material_name = models.CharField(max_length=100)

    def __str__(self):
        return self.raw_material_name


class JointType(SoftDeleteModel):
    joint_type_name = models.CharField(max_length=100)

    def __str__(self):
        return self.joint_type_name


# ─────────────────────────────────────────
# TOOL REQUEST
# ─────────────────────────────────────────

class ToolRequest(models.Model):
    tool_code = models.CharField(max_length=200, blank=True)

    description    = models.ForeignKey(Field,           on_delete=models.CASCADE)
    fixed_value    = models.ForeignKey(FieldFixedValue,  on_delete=models.SET_NULL,
                                       null=True, blank=True)
    supplier1      = models.ForeignKey(Supplier, on_delete=models.CASCADE,
                                       related_name='request_supplier1')
    supplier2      = models.ForeignKey(Supplier, on_delete=models.SET_NULL,
                                       null=True, blank=True,
                                       related_name='request_supplier2')
    supplier_code1 = models.CharField(max_length=100, blank=True)
    supplier_code2 = models.CharField(max_length=100, blank=True)
    raw_material   = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    joint_type     = models.ForeignKey(JointType,   on_delete=models.CASCADE)
    remark         = models.TextField(blank=True, null=True)
    created_by     = models.ForeignKey(User, on_delete=models.CASCADE)
    status         = models.CharField(max_length=20, default='Pending')
    reject_reason  = models.TextField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def _build_code_from_values(self, attr_values):
        """
        Shared internal logic — builds the tool code string from a list of values.
        Format: SHORT_CODE-FIXED-attr1Xattr2-attr3-JOINT[0]-MATERIAL
        Example: BTH-A-125X40-200-S-STEEL
        """
        primary  = self.description.short_code.upper() if self.description else ''
        fixed    = self.fixed_value.fixed_value.upper() if self.fixed_value else ''
        joint    = self.joint_type.joint_type_name[0].upper() if self.joint_type else ''
        material = self.raw_material.raw_material_name.upper() if self.raw_material else ''

        values = [str(v) for v in attr_values if v]

        if len(values) >= 2:
            attr_part = values[0] + 'X' + values[1]
            if len(values) > 2:
                attr_part += '-' + '-'.join(values[2:])
        elif len(values) == 1:
            attr_part = values[0]
        else:
            attr_part = ''

        parts     = [p for p in [primary, fixed, attr_part, joint, material] if p]
        base_code = '-'.join(parts)

        # Guarantee uniqueness by appending -01, -02 etc. if needed
        unique_code = base_code
        counter     = 1
        while ToolRequest.objects.filter(
                tool_code=unique_code).exclude(pk=self.pk).exists():
            unique_code = f"{base_code}-{counter:02d}"
            counter    += 1

        return unique_code

    def generate_tool_code(self):
        """
        Called from views.py AFTER ToolRequestAttribute rows have been saved.
        Reads attribute values directly from the database.
        """
        attr_values = list(
            self.attributes
                .order_by('field_attribute__order', 'field_attribute__id')
                .values_list('value', flat=True)
        )
        return self._build_code_from_values(attr_values)

    def save(self, *args, **kwargs):
        if not self.tool_code:
            if hasattr(self, '_pending_attributes'):
                attr_values = self._pending_attributes
            elif self.pk:  # only query DB if record already exists
                attr_values = list(
                    self.attributes
                        .order_by('field_attribute__order', 'field_attribute__id')
                        .values_list('value', flat=True)
                )
            else:
                attr_values = []  # new record, no attributes yet — code built after save
            self.tool_code = self._build_code_from_values(attr_values)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tool_code} ({self.status})"


# ─────────────────────────────────────────
# TOOL REQUEST ATTRIBUTE
# ─────────────────────────────────────────

class ToolRequestAttribute(models.Model):
    tool_request    = models.ForeignKey(ToolRequest,    on_delete=models.CASCADE,
                                        related_name='attributes')
    field_attribute = models.ForeignKey(FieldAttribute, on_delete=models.SET_NULL,
                                        null=True, blank=True)
    attr_name       = models.CharField(max_length=100)
    value           = models.CharField(max_length=500)

    class Meta:
        ordering = ['field_attribute__order', 'field_attribute__id', 'id']

    def __str__(self):
        return f"{self.attr_name}: {self.value}"