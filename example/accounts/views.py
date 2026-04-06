from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from django.utils.dateparse import parse_date
import json

from .models import (
    UserProfile, Field, FieldAttribute, FieldFixedValue,
    Supplier, RawMaterial, JointType,
    ToolRequest, ToolRequestAttribute,
)


# ─────────────────────────────────────────
# LOGIN / LOGOUT
# ─────────────────────────────────────────

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        return render(request, 'login.html', {'error': 'Invalid username or password'})
    return render(request, 'login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────

@login_required
def dashboard(request):
    if hasattr(request.user, 'userprofile'):
        role = request.user.userprofile.role
    else:
        role = 'admin' if request.user.is_superuser else 'user'
        UserProfile.objects.get_or_create(user=request.user, defaults={'role': role})

    base_query = (ToolRequest.objects.all() if role in ['admin', 'approver']
                  else ToolRequest.objects.filter(created_by=request.user))

    total_reqs    = base_query.count()
    pending_reqs  = base_query.filter(status='Pending').count()
    approved_reqs = base_query.filter(status='Approved').count()
    rejected_reqs = base_query.filter(status='Rejected').count()
    recent_requests = base_query.order_by('-created_at')[:5]

    status_data = [pending_reqs, approved_reqs, rejected_reqs]
    tool_counts = base_query.values('description__field_name').annotate(count=Count('id'))
    tool_labels = [i['description__field_name'] for i in tool_counts if i['description__field_name']]
    tool_data   = [i['count'] for i in tool_counts]

    admin_stats    = None
    approver_focus = None

    if role == 'admin':
        admin_stats = {
            'total_users':     User.objects.count(),
            'total_suppliers': Supplier.objects.count(),
            'total_materials': RawMaterial.objects.count(),
            'field_types':     Field.objects.count(),
        }
    elif role == 'approver':
        approver_focus = {
            'urgent_count':   pending_reqs,
            'my_actions_url': '/tool-code/',
        }

    return render(request, 'dashboard.html', {
        'role':            role,
        'total_reqs':      total_reqs,
        'pending_reqs':    pending_reqs,
        'approved_reqs':   approved_reqs,
        'rejected_reqs':   rejected_reqs,
        'recent_requests': recent_requests,
        'admin_stats':     admin_stats,
        'approver_focus':  approver_focus,
        'status_data':     json.dumps(status_data),
        'tool_labels':     json.dumps(tool_labels),
        'tool_data':       json.dumps(tool_data),
    })



# ─────────────────────────────────────────
# AJAX — get field attributes
# ─────────────────────────────────────────

@login_required
def get_field_attributes(request):
    field_id = request.GET.get('field_id')
    attrs = FieldAttribute.objects.filter(field_id=field_id) 
    data = [
        {
            'id':          a.id,
            'attr_name':   a.attr_name,
            'input_type':  a.input_type,
            'is_required': a.is_required,
        }
        for a in attrs
    ]
    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────
# AJAX — get fixed values
# ─────────────────────────────────────────

@login_required
def get_fixed_values(request):
    field_id = request.GET.get('field_id')
    values = FieldFixedValue.objects.filter(field_id=field_id, is_deleted=False)
    data = [{'id': v.id, 'value': v.fixed_value, 'explanation': v.explanation} for v in values]
    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────
# TOOL CODE  (unified page — replaces create_code + approval)
# ─────────────────────────────────────────

@login_required
def tool_code(request):
    role = request.user.userprofile.role

    # Table data — users see only their own, admin/approver see all
    if role in ['admin', 'approver']:
        requests = ToolRequest.objects.all().order_by('-created_at')
    else:
        requests = ToolRequest.objects.filter(
            created_by=request.user).order_by('-created_at')

    fields        = Field.objects.all()
    suppliers     = Supplier.objects.all()
    joint_types   = JointType.objects.all()
    raw_materials = RawMaterial.objects.all()

    # ── CREATE submission ──
    if request.method == 'POST' and request.POST.get('form_action') == 'create':

        description_id  = request.POST.get('description')
        supplier1_id    = request.POST.get('supplier1')
        supplier2_id    = request.POST.get('supplier2')
        supplier_code1  = request.POST.get('supplier_code1', '')
        supplier_code2  = request.POST.get('supplier_code2', '')
        raw_material_id = request.POST.get('raw_material')
        joint_type_id   = request.POST.get('joint_type')
        fixed_value_id  = request.POST.get('fixed_value_id')
        remark          = request.POST.get('remark', '')

        if not all([description_id, supplier1_id, raw_material_id, joint_type_id]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('tool_code')

        description  = get_object_or_404(Field,       id=description_id)
        supplier1    = get_object_or_404(Supplier,    id=supplier1_id)
        supplier2    = Supplier.objects.filter(id=supplier2_id).first() if supplier2_id else None
        raw_material = get_object_or_404(RawMaterial, id=raw_material_id)
        joint_type   = get_object_or_404(JointType,   id=joint_type_id)
        fixed_value  = FieldFixedValue.objects.filter(id=fixed_value_id).first() if fixed_value_id else None

        if supplier2 and supplier1 == supplier2:
            messages.error(request, 'Supplier 1 and Supplier 2 cannot be the same.')
            return redirect('tool_code')

        field_attrs = FieldAttribute.objects.filter(field=description)
        for attr in field_attrs:
            if attr.is_required and not request.POST.get(f'attr_{attr.id}', '').strip():
                messages.error(request, f'"{attr.attr_name}" is required.')
                return redirect('tool_code')

        # Step 1: Save request with empty tool_code
        tool_request = ToolRequest(
            description=description, fixed_value=fixed_value,
            supplier1=supplier1, supplier2=supplier2,
            supplier_code1=supplier_code1, supplier_code2=supplier_code2,
            raw_material=raw_material, joint_type=joint_type,
            remark=remark, created_by=request.user,
            status='Pending', tool_code='',
        )
        tool_request.save()

        # Step 2: Save attributes
        for attr in field_attrs:
            val = request.POST.get(f'attr_{attr.id}', '').strip()
            if val:
                ToolRequestAttribute.objects.create(
                    tool_request=tool_request, field_attribute=attr,
                    attr_name=attr.attr_name, value=val,
                )

        # Step 3: Generate and save tool code
        tool_request.tool_code = tool_request.generate_tool_code()
        tool_request.save()

        messages.success(request,
            f'Tool request submitted! Code: {tool_request.tool_code}')
        return redirect('tool_code')

    # ── EDIT (resubmit rejected) submission ──
    if request.method == 'POST' and request.POST.get('form_action') == 'edit':

        req_id = request.POST.get('request_id')
        tool_request = get_object_or_404(
            ToolRequest, id=req_id, created_by=request.user, status='Rejected')

        description_id  = request.POST.get('description')
        supplier1_id    = request.POST.get('supplier1')
        supplier2_id    = request.POST.get('supplier2')
        supplier_code1  = request.POST.get('supplier_code1', '')
        supplier_code2  = request.POST.get('supplier_code2', '')
        raw_material_id = request.POST.get('raw_material')
        joint_type_id   = request.POST.get('joint_type')
        fixed_value_id  = request.POST.get('fixed_value_id')
        remark          = request.POST.get('remark', '')

        if not all([description_id, supplier1_id, raw_material_id, joint_type_id]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('tool_code')

        tool_request.description  = get_object_or_404(Field,       id=description_id)
        tool_request.supplier1    = get_object_or_404(Supplier,    id=supplier1_id)
        tool_request.supplier2    = Supplier.objects.filter(id=supplier2_id).first() if supplier2_id else None
        tool_request.raw_material = get_object_or_404(RawMaterial, id=raw_material_id)
        tool_request.joint_type   = get_object_or_404(JointType,   id=joint_type_id)
        tool_request.fixed_value  = FieldFixedValue.objects.filter(id=fixed_value_id).first() if fixed_value_id else None
        tool_request.supplier_code1 = supplier_code1
        tool_request.supplier_code2 = supplier_code2
        tool_request.remark         = remark
        tool_request.status         = 'Pending'   # reset to pending on resubmit
        tool_request.reject_reason  = ''
        tool_request.tool_code      = ''          # will be regenerated

        tool_request.save()

        # Replace attributes
        tool_request.attributes.all().delete()
        field_attrs = FieldAttribute.objects.filter(field=tool_request.description)
        for attr in field_attrs:
            val = request.POST.get(f'attr_{attr.id}', '').strip()
            if val:
                ToolRequestAttribute.objects.create(
                    tool_request=tool_request, field_attribute=attr,
                    attr_name=attr.attr_name, value=val,
                )

        tool_request.tool_code = tool_request.generate_tool_code()
        tool_request.save()

        messages.success(request,
            f'Request resubmitted successfully! New Code: {tool_request.tool_code}')
        return redirect('tool_code')

    return render(request, 'tool_code.html', {
        'requests':     requests,
        'fields':       fields,
        'suppliers':    suppliers,
        'joint_types':  joint_types,
        'raw_materials': raw_materials,
        'role':         role,
    })


# ─────────────────────────────────────────
# AJAX — get single request data for edit modal pre-fill
# ─────────────────────────────────────────

@login_required
def get_request_data(request):
    req_id = request.GET.get('id')
    req    = get_object_or_404(ToolRequest, id=req_id, created_by=request.user)

    attrs = [
        {
            'field_attribute_id': a.field_attribute_id,
            'attr_name':          a.attr_name,
            'value':              a.value,
        }
        for a in req.attributes.all()
    ]

    return JsonResponse({
        'description_id':  req.description_id,
        'supplier1_id':    req.supplier1_id,
        'supplier2_id':    req.supplier2_id or '',
        'supplier_code1':  req.supplier_code1,
        'supplier_code2':  req.supplier_code2,
        'raw_material_id': req.raw_material_id,
        'joint_type_id':   req.joint_type_id,
        'fixed_value_id':  req.fixed_value_id or '',
        'remark':          req.remark or '',
        'reject_reason':   req.reject_reason or '',
        'attributes':      attrs,
    })



@login_required
def review_request(request, id):
    role = request.user.userprofile.role
    req  = get_object_or_404(ToolRequest, id=id)

    # Users can only view their own requests
    if role not in ['admin', 'approver'] and req.created_by != request.user:
        return redirect('tool_code')

    return render(request, 'review_request.html', {'req': req})


@login_required
def approve_request(request, id):
    if request.user.userprofile.role not in ['admin', 'approver']:
        return redirect('dashboard')
    if request.method == 'POST':
        tool = get_object_or_404(ToolRequest, id=id)
        tool.status = 'Approved'
        tool.save()
        messages.success(request, f"Tool code '{tool.tool_code}' approved.")
    return redirect('tool_code')


@login_required
def reject_request(request, id):
    if request.user.userprofile.role not in ['admin', 'approver']:
        return redirect('dashboard')
    req = get_object_or_404(ToolRequest, id=id)
    if request.method == 'POST':
        req.status        = 'Rejected'
        req.reject_reason = request.POST.get('reject_reason', '')
        req.save()
        messages.success(request, f"Tool code '{req.tool_code}' rejected.")
    return redirect('tool_code')


# ─────────────────────────────────────────
# FIELD ATTRIBUTE MASTER 
# ─────────────────────────────────────────

@login_required
def field_attribute_master(request):
    if request.user.userprofile.role != 'admin':
        return redirect('dashboard')

    fields = Field.objects.all()
    selected_field_id = request.GET.get('field_id')
    selected_field    = None
    attributes        = []

    if selected_field_id:
        selected_field = Field.objects.filter(id=selected_field_id).first()
        if selected_field:
            attributes = FieldAttribute.objects.filter(field=selected_field).order_by('order', 'id')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            field_id   = request.POST.get('field_id')
            attr_name  = request.POST.get('attr_name', '').strip()
            input_type = request.POST.get('input_type', 'number')
            is_required = request.POST.get('is_required') == 'on'
            order      = request.POST.get('order', 0)

            if field_id and attr_name:
                FieldAttribute.objects.create(
                    field       = get_object_or_404(Field, id=field_id),
                    attr_name   = attr_name,
                    input_type  = input_type,
                    is_required = is_required,
                    order       = order,
                )
                messages.success(request, f'Attribute "{attr_name}" added.')
            return redirect(f'/field-attributes/?field_id={field_id}')

        elif action == 'delete':
            attr = get_object_or_404(FieldAttribute, id=request.POST.get('attr_id'))
            field_id = attr.field.id
            attr.soft_delete()   
            messages.success(request, 'Attribute deleted.')
            return redirect(f'/field-attributes/?field_id={field_id}')

        elif action == 'edit':
            attr_id    = request.POST.get('attr_id')
            attr       = get_object_or_404(FieldAttribute, id=attr_id)
            field_id   = attr.field.id
            attr.attr_name   = request.POST.get('attr_name', attr.attr_name).strip()
            attr.input_type  = request.POST.get('input_type', attr.input_type)
            attr.is_required = request.POST.get('is_required') == 'on'
            attr.order       = request.POST.get('order', attr.order)
            attr.save()
            messages.success(request, 'Attribute updated.')
            return redirect(f'/field-attributes/?field_id={field_id}')

    return render(request, 'field_attributes.html', {
        'fields':           fields,
        'selected_field':   selected_field,
        'selected_field_id': selected_field_id,
        'attributes':       attributes,
    })


# ─────────────────────────────────────────
# FIELD MASTER
# ─────────────────────────────────────────

@login_required
def create_field_form(request):
    if request.user.userprofile.role != 'admin':
        return redirect('dashboard')

    if request.method == 'POST':
        Field.objects.create(
            field_name      = request.POST.get('field_name'),
            short_code      = request.POST.get('short_code', ''),
            field_size_type = request.POST.get('field_size_type'),
            field_size      = request.POST.get('field_size'),
            field_message   = request.POST.get('field_message', ''),
        )
        return redirect('create_field_form')

    return render(request, 'create_field_form.html', {'fields': Field.objects.all()})


@login_required
def delete_field(request, id):
    if request.user.userprofile.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        get_object_or_404(Field, id=id).soft_delete()
    return redirect('create_field_form')


# ─────────────────────────────────────────
# FIELD FIXED VALUE
# ─────────────────────────────────────────

@login_required
def create_field_fixed_value_form(request):
    if request.user.userprofile.role != 'admin':
        return redirect('dashboard')
    fields = Field.objects.all()
    selected_field  = request.GET.get('field')
    fixed_values    = FieldFixedValue.objects.filter(field_id=selected_field) if selected_field else None
    return render(request, 'create_field_fixed_value_form.html', {
        'fields':         fields,
        'fixed_values':   fixed_values,
        'selected_field': selected_field,
    })


@login_required
def add_fixed_value(request):
    if request.user.userprofile.role != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    if request.method == 'POST':
        data  = json.loads(request.body)
        field = Field.objects.get(id=data.get('field_id'))
        obj   = FieldFixedValue.objects.create(
            field       = field,
            fixed_value = data.get('value'),
            explanation = data.get('explanation'),
        )
        return JsonResponse({'id': obj.id, 'value': obj.fixed_value, 'explanation': obj.explanation})


@login_required
def edit_fixed_value(request, id):
    if request.user.userprofile.role != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    value = get_object_or_404(FieldFixedValue, id=id)
    if request.method == 'POST':
        data = json.loads(request.body)
        value.fixed_value = data.get('value')
        value.explanation = data.get('explanation')
        value.save()
        return JsonResponse({'id': value.id, 'value': value.fixed_value, 'explanation': value.explanation})


@login_required
def delete_fixed_value(request, id):
    if request.user.userprofile.role != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    get_object_or_404(FieldFixedValue, id=id).soft_delete()
    return JsonResponse({'status': 'deleted'})


# ─────────────────────────────────────────
# SUPPLIER MASTER
# ─────────────────────────────────────────

@login_required
def supplier_master(request):
    if request.user.userprofile.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        Supplier.objects.create(
            supplier_name          = request.POST.get('supplier'),
            supplier_ordering_code = request.POST.get('supplier_code'),
        )
        return redirect('supplier_master')
    return render(request, 'supplier_master.html', {'suppliers': Supplier.objects.all()})


@login_required
def delete_supplier(request, id):
    if request.user.userprofile.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        get_object_or_404(Supplier, id=id).soft_delete()
    return redirect('supplier_master')


# ─────────────────────────────────────────
# RAW MATERIAL MASTER
# ─────────────────────────────────────────

@login_required
def raw_material_master(request):
    if request.user.userprofile.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        RawMaterial.objects.create(raw_material_name=request.POST.get('raw_material'))
        return redirect('raw_material_master')
    return render(request, 'raw_material_master.html', {'materials': RawMaterial.objects.all()})


@login_required
def delete_raw_material(request, id):
    if request.user.userprofile.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        get_object_or_404(RawMaterial, id=id).soft_delete()
    return redirect('raw_material_master')


# ─────────────────────────────────────────
# JOINT TYPE MASTER
# ─────────────────────────────────────────

@login_required
def joint_type_master(request):
    if request.user.userprofile.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        JointType.objects.create(joint_type_name=request.POST.get('joint_type'))
        return redirect('joint_type_master')
    return render(request, 'joint_type_master.html', {'joint_types': JointType.objects.all()})


@login_required
def delete_joint_type(request, id):
    if request.user.userprofile.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        get_object_or_404(JointType, id=id).soft_delete()
    return redirect('joint_type_master')


# ─────────────────────────────────────────
# USER CREATION
# ─────────────────────────────────────────

@login_required
def user_creation(request):
    if request.user.userprofile.role != 'admin':
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('user_creation')
        user = User.objects.create_user(
            username   = username,
            email      = request.POST.get('email'),
            password   = request.POST.get('password'),
            first_name = request.POST.get('fullname'),
        )
        UserProfile.objects.create(user=user, role=request.POST.get('role'))
        messages.success(request, f"User '{username}' created successfully.")
        return redirect('dashboard')
    return render(request, 'user_creation.html')


# ─────────────────────────────────────────
# CHANGE PASSWORD
# ─────────────────────────────────────────

@login_required
def change_password(request):
    if request.method == 'POST':
        old_password     = request.POST.get('old_password')
        new_password     = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(old_password):
            messages.error(request, 'Old password is incorrect.')
            return redirect('change_password')
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('change_password')
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return redirect('change_password')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Password updated successfully.')
        return redirect('dashboard')

    return render(request, 'change_password.html')


# ─────────────────────────────────────────
# MASTER REPORT
# ─────────────────────────────────────────

@login_required
def master_report(request):
    if request.user.userprofile.role not in ['admin', 'approver']:
        messages.error(request, 'You do not have permission to view reports.')
        return redirect('dashboard')

    report_data  = ToolRequest.objects.all().order_by('-created_at')
    from_date_str = request.GET.get('from_date')
    to_date_str   = request.GET.get('to_date')

    if from_date_str:
        from_date = parse_date(from_date_str)
        if from_date:
            report_data = report_data.filter(created_at__date__gte=from_date)
    if to_date_str:
        to_date = parse_date(to_date_str)
        if to_date:
            report_data = report_data.filter(created_at__date__lte=to_date)

    return render(request, 'master_report.html', {
        'requests':  report_data,
        'from_date': from_date_str,
        'to_date':   to_date_str,
    })