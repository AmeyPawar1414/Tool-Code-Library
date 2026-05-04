from django.db import models
from django.contrib.auth.models import User


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
# DYNAMIC ROLE MASTER
# ─────────────────────────────────────────

class Role(SoftDeleteModel):
    name = models.CharField(max_length=50, unique=True)
    
    #  TAB ACCESS CHECKBOXES 
    can_access_tool_code = models.BooleanField(default=True, verbose_name="Tool Code Tab")
    can_create_requests  = models.BooleanField(default=True)
    can_approve_requests = models.BooleanField(default=False, verbose_name="Can Approve Tool Codes")
    can_access_master    = models.BooleanField(default=False, verbose_name="Master Data Tab")
    can_access_reports   = models.BooleanField(default=False, verbose_name="Reports Tab")
    can_manage_users     = models.BooleanField(default=False, verbose_name="User Creation Tab")
    can_manage_roles     = models.BooleanField(default=False, verbose_name="Role Master Tab")

    def __str__(self):
        return self.name


# ─────────────────────────────────────────
# USER PROFILE
# ─────────────────────────────────────────

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # This now links to the new Role table instead of the hardcoded text!
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username



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

class FieldAttributeOption(SoftDeleteModel):
    attribute   = models.ForeignKey(FieldAttribute, on_delete=models.CASCADE,
                                    related_name='options')
    option_value = models.CharField(max_length=200)
    order        = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.attribute.attr_name} → {self.option_value}"
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
    

class PdfFooterConfig(models.Model):
    """
    Stores the three footer texts for downloaded tool request PDFs.
    Only one row should exist — admin edits it in Format Master.
    """
    footer_left   = models.CharField(max_length=300, blank=True, default='')
    footer_center = models.CharField(max_length=300, blank=True, default='')
    footer_right  = models.CharField(max_length=300, blank=True, default='')
    updated_at    = models.DateTimeField(auto_now=True)
    updated_by    = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'PDF Footer Configuration'

    def __str__(self):
        return f"Footer config (updated {self.updated_at:%Y-%m-%d})"

    @classmethod
    def get_config(cls):
        """Always returns a config object — creates default if none exists."""
        obj, _ = cls.objects.get_or_create(id=1)
        return obj    


# ─────────────────────────────────────────
# TOOL REQUEST
# ─────────────────────────────────────────

class ToolRequest(models.Model):
    tool_code = models.CharField(max_length=200, blank=True)

    # 1. Primary description IS required for drafts (so we know what we are building)
    description    = models.ForeignKey(Field,           on_delete=models.CASCADE)
    fixed_value    = models.ForeignKey(FieldFixedValue,  on_delete=models.SET_NULL,
                                       null=True, blank=True)
                                       
    # 🌟 CHANGED: Added null=True, blank=True to allow empty Drafts
    supplier1      = models.ForeignKey(Supplier, on_delete=models.SET_NULL,
                                       null=True, blank=True,
                                       related_name='request_supplier1')
    supplier2      = models.ForeignKey(Supplier, on_delete=models.SET_NULL,
                                       null=True, blank=True,
                                       related_name='request_supplier2')
                                       
    supplier_code1 = models.CharField(max_length=100, blank=True)
    supplier_code2 = models.CharField(max_length=100, blank=True)
    
    # 🌟 CHANGED: Added null=True, blank=True to allow empty Drafts
    raw_material   = models.ForeignKey(RawMaterial, on_delete=models.SET_NULL, 
                                       null=True, blank=True)
                                       
    # 🌟 CHANGED: Added null=True, blank=True to allow empty Drafts
    joint_type     = models.ForeignKey(JointType,   on_delete=models.SET_NULL, 
                                       null=True, blank=True)
                                       
    remark         = models.TextField(blank=True, null=True)
    created_by     = models.ForeignKey(User, on_delete=models.CASCADE)
    reviewed_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_tool_requests')
    status         = models.CharField(max_length=20, default='Pending')
    reject_reason  = models.TextField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    reviewed_at    = models.DateTimeField(null=True, blank=True)

    def _build_code_from_values(self, attr_values):
        """
        Dynamic internal logic — builds the tool code string up to a strict 40 character limit.
        Format: SHORT_CODE-FIXED-attr1Xattr2-attr3-attrN-JOINT[0]-MATERIAL[0:2]
        """
        primary  = self.description.short_code.upper() if self.description else ''
        fixed    = self.fixed_value.fixed_value.upper() if self.fixed_value else ''
        joint    = self.joint_type.joint_type_name[0].upper() if self.joint_type else ''
        material = self.raw_material.raw_material_name[:2].upper() if self.raw_material else ''

        # 1. Process Attributes: Text -> 2 letters. Numbers -> Keep full value.
        processed_attrs = []
        for v in attr_values:
            if not v: continue
            v_str = str(v).strip()
            
            # Check if the value contains any letters (e.g. "Steel", "Standard", "T20")
            if any(char.isalpha() for char in v_str):
                processed_attrs.append(v_str[:2].upper()) # Keep only 2 letters
            else:
                processed_attrs.append(v_str) # Keep numbers/fractions (e.g. "14", "1.5", "1/2")

        # 2. Build the dynamic attributes section safely
        attr_part_str = ""
        for i, attr in enumerate(processed_attrs):
            # First two get an 'X', everything else gets a '-'
            if i == 0:
                separator = ""
            elif i == 1:
                separator = "X"
            else:
                separator = "-"
                
            proposed_attr_str = attr_part_str + separator + attr
            
            # 🛑 THE 40-CHAR LOCK: Test the full length before applying!
            # We check > 37 to perfectly reserve 3 characters for the uniqueness counter (e.g., "-01")
            test_parts = [p for p in [primary, fixed, proposed_attr_str, joint, material] if p]
            if len('-'.join(test_parts)) > 37:
                break # Stop adding attributes, we hit the maximum safe length!
                
            attr_part_str = proposed_attr_str

        # 3. Assemble the final base code
        parts     = [p for p in [primary, fixed, attr_part_str, joint, material] if p]
        base_code = '-'.join(parts)

        # 4. Guarantee uniqueness by appending -01, -02 etc. (Making it exactly 40 chars max)
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
            # 🌟 CHANGED: Safely handle if it's a Draft that shouldn't generate a code yet
            if self.status == 'Draft':
                self.tool_code = '[DRAFT]'
            else:
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
    
from django.db import models
from django.contrib.auth.models import User

class AuditLog(models.Model):
    LEVEL_CHOICES = [
        ('INFO', 'Information / Activity'),
        ('WARNING', 'Warning / Blocked Action'),
        ('ERROR', 'System Error'),
    ]
    
    # If the user isn't logged in, this will be null
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField(null=True, blank=True)
    message = models.TextField() # For specific details like "Tool Code Approved"
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        return f"{self.level} | {username} | {self.path} | {self.timestamp}"