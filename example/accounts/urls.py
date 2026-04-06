from django.urls import path
from . import views

urlpatterns = [

    # ── AUTH ──────────────────────────────────────────
    path('',         views.login_view,  name='login'),
    path('logout/',  views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # ── TOOL CODE (unified page) ───────────────────────
    path('tool-code/', views.tool_code, name='tool_code'),

    # ── APPROVAL ACTIONS ──────────────────────────────
    path('review-request/<int:id>/',   views.review_request,  name='review_request'),
    path('approval/approve/<int:id>/', views.approve_request, name='approve_request'),
    path('approval/reject/<int:id>/',  views.reject_request,  name='reject_request'),

    # ── AJAX ──────────────────────────────────────────
    path('get-field-attributes/', views.get_field_attributes, name='get_field_attributes'),
    path('get-fixed-values/',     views.get_fixed_values,     name='get_fixed_values'),
    path('get-request-data/',     views.get_request_data,     name='get_request_data'),

    # ── USER ──────────────────────────────────────────
    path('user-creation/',   views.user_creation,   name='user_creation'),
    path('change-password/', views.change_password, name='change_password'),

    # ── FIELD MASTER ──────────────────────────────────
    path('create-field-form/',     views.create_field_form, name='create_field_form'),
    path('delete-field/<int:id>/', views.delete_field,      name='delete_field'),

    # ── FIELD ATTRIBUTES MASTER ───────────────────────
    path('field-attributes/', views.field_attribute_master, name='field_attribute_master'),

    # ── FIELD FIXED VALUE ─────────────────────────────
    path('create-field-fixed-value/',    views.create_field_fixed_value_form, name='create_field_fixed_value_form'),
    path('add-fixed-value/',             views.add_fixed_value,               name='add_fixed_value'),
    path('edit-fixed-value/<int:id>/',   views.edit_fixed_value,              name='edit_fixed_value'),
    path('delete-fixed-value/<int:id>/', views.delete_fixed_value,            name='delete_fixed_value'),

    # ── SUPPLIER MASTER ───────────────────────────────
    path('supplier-master/',             views.supplier_master,  name='supplier_master'),
    path('delete-supplier/<int:id>/',    views.delete_supplier,  name='delete_supplier'),

    # ── RAW MATERIAL MASTER ───────────────────────────
    path('raw-material-master/',          views.raw_material_master,  name='raw_material_master'),
    path('delete-raw-material/<int:id>/', views.delete_raw_material,  name='delete_raw_material'),

    # ── JOINT TYPE MASTER ─────────────────────────────
    path('joint-type-master/',            views.joint_type_master,  name='joint_type_master'),
    path('delete-joint-type/<int:id>/',   views.delete_joint_type,  name='delete_joint_type'),

    # ── REPORTS ───────────────────────────────────────
    path('master-report/', views.master_report, name='master_report'),
]