from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import (
    Field, FieldAttribute, FieldAttributeOption, FieldFixedValue,
    Supplier, RawMaterial, JointType,
    UserProfile, ToolRequest, ToolRequestAttribute, Role,
    AuditLog, PdfFooterConfig
)


# ─────────────────────────────────────────
# FIELD ADMIN
# ─────────────────────────────────────────

class FieldAdmin(admin.ModelAdmin):
    list_display = ['field_name', 'short_code', 'field_size_type', 'field_size', 'is_deleted']
    actions = ['restore_selected']

    def get_queryset(self, request):
        return Field.all_objects.all()

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
    restore_selected.short_description = "Restore selected fields"


# ─────────────────────────────────────────
# FIELD ATTRIBUTE ADMIN
# ─────────────────────────────────────────

class FieldAttributeOptionInline(admin.TabularInline):
    model = FieldAttributeOption
    extra = 1
    fields = ['option_value', 'order']

class FieldAttributeAdmin(admin.ModelAdmin):
    list_display  = ['field', 'attr_name', 'input_type', 'is_required', 'order', 'is_deleted']
    inlines       = [FieldAttributeOptionInline]
    actions       = ['restore_selected']

    def get_queryset(self, request):
        return FieldAttribute.all_objects.all()

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
    restore_selected.short_description = "Restore selected attributes"


# ─────────────────────────────────────────
# FIELD FIXED VALUE ADMIN
# ─────────────────────────────────────────

class FieldFixedValueAdmin(admin.ModelAdmin):
    list_display = ['field', 'fixed_value', 'explanation', 'is_deleted']
    actions = ['restore_selected']

    def get_queryset(self, request):
        return FieldFixedValue.all_objects.all()

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
    restore_selected.short_description = "Restore selected fixed values"


# ─────────────────────────────────────────
# SUPPLIER ADMIN
# ─────────────────────────────────────────

class SupplierAdmin(admin.ModelAdmin):
    list_display = ['supplier_name', 'supplier_ordering_code', 'is_deleted']
    actions = ['restore_selected']

    def get_queryset(self, request):
        return Supplier.all_objects.all()

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
    restore_selected.short_description = "Restore selected suppliers"


# ─────────────────────────────────────────
# RAW MATERIAL ADMIN
# ─────────────────────────────────────────

class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ['raw_material_name', 'is_deleted']
    actions = ['restore_selected']

    def get_queryset(self, request):
        return RawMaterial.all_objects.all()

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
    restore_selected.short_description = "Restore selected raw materials"


# ─────────────────────────────────────────
# JOINT TYPE ADMIN
# ─────────────────────────────────────────

class JointTypeAdmin(admin.ModelAdmin):
    list_display = ['joint_type_name', 'is_deleted']
    actions = ['restore_selected']

    def get_queryset(self, request):
        return JointType.all_objects.all()

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
    restore_selected.short_description = "Restore selected joint types"


# ─────────────────────────────────────────
# TOOL REQUEST ATTRIBUTE INLINE
# 
# ─────────────────────────────────────────

class ToolRequestAttributeInline(admin.TabularInline):
    model   = ToolRequestAttribute
    extra   = 0
    fields  = ['attr_name', 'value', 'field_attribute']
    readonly_fields = ['attr_name', 'field_attribute']
    can_delete = False


# ─────────────────────────────────────────
# TOOL REQUEST ADMIN 
# ─────────────────────────────────────────

@admin.register(ToolRequest)
class ToolRequestAdmin(admin.ModelAdmin):

    list_display  = ('id', 'tool_code', 'description', 'fixed_value',
                     'created_by', 'status', 'created_at')
    list_filter   = ('status', 'description')
    search_fields = ('tool_code', 'created_by__username')
    readonly_fields = ('tool_code', 'created_at')

    inlines = [ToolRequestAttributeInline]

    fieldsets = (
        ("Tool Information", {
            "fields": (
                "tool_code",
                "description",
                "fixed_value",
                "joint_type",
                "raw_material",
                "remark",
            )
        }),
        ("Supplier Details", {
            "fields": (
                "supplier1",
                "supplier_code1",
                "supplier2",
                "supplier_code2",
            )
        }),
        ("Approval", {
            "fields": (
                "status",
                "reject_reason",
                "created_by",
                "created_at",
            )
        }),
    )

# ─────────────────────────────────────────
# ROLE ADMIN
# ─────────────────────────────────────────

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'can_access_tool_code',
        'can_create_requests',
        'can_approve_requests', 
        'can_access_master', 
        'can_manage_users', 
        'is_deleted'
    )
    search_fields = ('name',)
    list_filter = ('is_deleted',)
    actions = ['restore_selected']

    def get_queryset(self, request):
        return Role._base_manager.all()

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
    restore_selected.short_description = "Restore selected roles"

# ─────────────────────────────────────────
# USER PROFILE ADMIN
# ─────────────────────────────────────────

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    search_fields = ('user__username', 'role__name')
    list_filter = ('role',)

# ─────────────────────────────────────────
# REGISTER ALL
# ─────────────────────────────────────────

admin.site.register(Field,           FieldAdmin)
admin.site.register(FieldAttribute,  FieldAttributeAdmin)
admin.site.register(FieldAttributeOption)
admin.site.register(FieldFixedValue, FieldFixedValueAdmin)
admin.site.register(Supplier,        SupplierAdmin)
admin.site.register(RawMaterial,     RawMaterialAdmin)
admin.site.register(JointType,       JointTypeAdmin)

# ─────────────────────────────────────────
# CUSTOM USER ADMIN
# ─────────────────────────────────────────

# 1. Unregister the default Django User admin
admin.site.unregister(User)

# 2. Register our new, customized User admin
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # This controls exactly what columns show up in the main table
    list_display = (
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'is_staff', 
        'is_active'
    )
    
    # This adds a search bar so you can quickly find users by name or email
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    # Optional: Adds a filter sidebar
    list_filter = ('is_staff', 'is_superuser', 'is_active')


# ─────────────────────────────────────────
# AUDIT LOG ADMIN 
# ─────────────────────────────────────────

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    # What columns show up in the table
    list_display = ('timestamp', 'level', 'user', 'method', 'path', 'status_code', 'ip_address')
    
    # Creates a filter sidebar on the right side of the screen
    list_filter = ('level', 'method', 'status_code', 'timestamp')
    
    # Adds a search bar at the top
    search_fields = ('user__username', 'path', 'message', 'ip_address')
    
    # Make all fields read-only so logs cannot be tampered with
    readonly_fields = ('user', 'level', 'ip_address', 'path', 'method', 'status_code', 'message', 'timestamp')

    # Security: Prevent anyone from manually creating a fake log
    def has_add_permission(self, request):
        return False

    # Security: Prevent anyone from editing an existing log
    def has_change_permission(self, request, obj=None):
        return False
    

# ─────────────────────────────────────────
# FORMAT MASTER (PDF FOOTER) ADMIN
# ─────────────────────────────────────────

@admin.register(PdfFooterConfig)
class PdfFooterConfigAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'footer_left', 'footer_center', 'footer_right', 'updated_at', 'updated_by')
    readonly_fields = ('updated_at', 'updated_by')

    # 🌟 ENTERPRISE TRICK: Prevent multiple footer rows!
    # Because this is a settings table, there should only ever be 1 row.
    def has_add_permission(self, request):
        if self.model.objects.count() >= 1:
            return False # Hide the "Add" button if a config already exists
        return super().has_add_permission(request)