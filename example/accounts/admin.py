from django.contrib import admin
from .models import (
    Field, FieldAttribute, FieldFixedValue,
    Supplier, RawMaterial, JointType,
    UserProfile, ToolRequest, ToolRequestAttribute,
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

class FieldAttributeAdmin(admin.ModelAdmin):
    list_display = ['field', 'attr_name', 'input_type', 'is_required', 'order', 'is_deleted']
    actions = ['restore_selected']

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
# Shows dynamic attributes inside ToolRequest admin
# ─────────────────────────────────────────

class ToolRequestAttributeInline(admin.TabularInline):
    model   = ToolRequestAttribute
    extra   = 0
    fields  = ['attr_name', 'value', 'field_attribute']
    readonly_fields = ['attr_name', 'field_attribute']
    can_delete = False


# ─────────────────────────────────────────
# TOOL REQUEST ADMIN  (fixed — removed old hardcoded fields)
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
# REGISTER ALL
# ─────────────────────────────────────────

admin.site.register(Field,           FieldAdmin)
admin.site.register(FieldAttribute,  FieldAttributeAdmin)
admin.site.register(FieldFixedValue, FieldFixedValueAdmin)
admin.site.register(Supplier,        SupplierAdmin)
admin.site.register(RawMaterial,     RawMaterialAdmin)
admin.site.register(JointType,       JointTypeAdmin)
admin.site.register(UserProfile)