from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.db.models import Q
import json
import logging
logger = logging.getLogger('accounts.views')
from .models import (
    UserProfile, Field, FieldAttribute,FieldAttributeOption, FieldFixedValue,
    Supplier, RawMaterial, JointType,
    ToolRequest, ToolRequestAttribute, Role, AuditLog
)


# ─────────────────────────────────────────
# LOGIN / LOGOUT
# ─────────────────────────────────────────

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        # Helper to grab IP for the manual logs
        ip_address = request.META.get('REMOTE_ADDR') 
        
        if user is not None:
            if hasattr(user, 'userprofile') and user.userprofile.role:
                if user.userprofile.role.is_deleted:
                    # WRITE WARNING TO DATABASE
                    AuditLog.objects.create(
                        user=user, level='WARNING', path=request.path, method='POST',
                        ip_address=ip_address, message="Blocked login attempt: Role is deleted."
                    )
                    # 🌟 NEW: WRITE TO VS CODE LOG FILE
                    logger.warning(f"BLOCKED LOGIN: User '{username}' attempted login but role is deleted.")
                    
                    return render(request, 'login.html', {
                        'error': 'Your assigned role is currently inactive.'
                    })
            
            login(request, user)
            
            # WRITE SUCCESS TO DATABASE
            AuditLog.objects.create(
                user=user, level='INFO', path=request.path, method='POST',
                ip_address=ip_address, message="User logged in successfully."
            )
            
            # THIS IS THE LINE THAT WRITES TO activity.log!
            logger.info(f"TESTING THE LOG FILE: User '{user.username}' logged in.")
            
            return redirect('dashboard')
            
        else:
            # WRITE FAILED LOGIN TO DATABASE
            AuditLog.objects.create(
                user=None, level='ERROR', path=request.path, method='POST',
                ip_address=ip_address, message=f"Failed login attempt for username: '{username}'."
            )
            # 🌟 NEW: WRITE TO VS CODE LOG FILE
            logger.error(f"FAILED LOGIN: Username '{username}' from {ip_address}")
            
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
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None

    # Check the boolean flag instead of 'admin'/'approver' strings
    base_query = (ToolRequest.objects.exclude(status='Draft') if (role and role.can_approve_requests)
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

    # Check flags for stats display
    if role and role.can_access_master:
        admin_stats = {
            'total_users':     User.objects.count(),
            'total_suppliers': Supplier.objects.count(),
            'total_materials': RawMaterial.objects.count(),
            'field_types':     Field.objects.count(),
        }
    if role and role.can_approve_requests:
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
    data = []
    for a in attrs:
        entry = {
            'id':          a.id,
            'attr_name':   a.attr_name,
            'input_type':  a.input_type,
            'is_required': a.is_required,
            'options':     [],
        }
        if a.input_type == 'select':
            entry['options'] = [
                {'id': o.option_value, 'value': o.option_value}  # use text as both id and value
                for o in a.options.all()
            ]
        data.append(entry)
    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────
# AJAX — get fixed values
# ─────────────────────────────────────────

@login_required
def get_fixed_values(request):
    field_id = request.GET.get('field_id')
    # 🌟 CHANGED: Use _base_manager to get BOTH active and inactive values
    values = FieldFixedValue._base_manager.filter(field_id=field_id)
    # 🌟 CHANGED: Added 'is_deleted' to the dictionary
    data = [{'id': v.id, 'value': v.fixed_value, 'explanation': v.explanation, 'is_deleted': v.is_deleted} for v in values]
    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────
# TOOL CODE  
# ─────────────────────────────────────────

@login_required
def tool_code(request):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None

    #  Table data — users see only their own, approvers/admins see all EXCEPT other people's Drafts
    if request.user.is_superuser or (role and role.can_approve_requests):
        requests = ToolRequest.objects.filter(
            ~Q(status='Draft') | Q(created_by=request.user)
        ).order_by('-created_at')
    else:
        requests = ToolRequest.objects.filter(created_by=request.user).order_by('-created_at')

    fields        = Field.objects.all()
    suppliers     = Supplier.objects.all()
    joint_types   = JointType.objects.all()
    raw_materials = RawMaterial.objects.all()

    # ── CREATE submission ──
    if request.method == 'POST' and request.POST.get('form_action') == 'create':
        
        if not role or not role.can_create_requests:
            messages.error(request, 'You do not have permission to create tool requests.')
            return redirect('tool_code')

        # 1. Check which button the user clicked FIRST
        action_type = request.POST.get('action_type', 'submit')
        req_status = 'Draft' if action_type == 'draft' else 'Pending'

        # 2. Get all IDs
        description_id  = request.POST.get('description')
        supplier1_id    = request.POST.get('supplier1')
        supplier2_id    = request.POST.get('supplier2')
        supplier_code1  = request.POST.get('supplier_code1', '')
        supplier_code2  = request.POST.get('supplier_code2', '')
        raw_material_id = request.POST.get('raw_material')
        joint_type_id   = request.POST.get('joint_type')
        fixed_value_id  = request.POST.get('fixed_value_id')
        remark          = request.POST.get('remark', '')

        # 3. Validation
        if not description_id:
            messages.error(request, 'You must at least select a Primary Description to save a draft.')
            return redirect('tool_code')

        if req_status == 'Pending':
            # Strict Validation for formal submission
            if not all([supplier1_id, raw_material_id, joint_type_id]):
                messages.error(request, 'Please fill in all required fields to submit.')
                return redirect('tool_code')
            
            if supplier2_id and supplier1_id == supplier2_id:
                messages.error(request, 'Supplier 1 and Supplier 2 cannot be the same.')
                return redirect('tool_code')
            
            field_attrs = FieldAttribute.objects.filter(field_id=description_id)
            for attr in field_attrs:
                if attr.is_required and not request.POST.get(f'attr_{attr.id}', '').strip():
                    messages.error(request, f'"{attr.attr_name}" is required to submit.')
                    return redirect('tool_code')

        # 4. Graceful Database Fetching (Allows None for drafts)
        description  = get_object_or_404(Field, id=description_id)
        supplier1    = Supplier.objects.filter(id=supplier1_id).first() if supplier1_id else None
        supplier2    = Supplier.objects.filter(id=supplier2_id).first() if supplier2_id else None
        raw_material = RawMaterial.objects.filter(id=raw_material_id).first() if raw_material_id else None
        joint_type   = JointType.objects.filter(id=joint_type_id).first() if joint_type_id else None
        fixed_value  = FieldFixedValue.objects.filter(id=fixed_value_id).first() if fixed_value_id else None

        # 5. Save Request
        tool_request = ToolRequest.objects.create(
            description=description, fixed_value=fixed_value,
            supplier1=supplier1, supplier2=supplier2,
            supplier_code1=supplier_code1, supplier_code2=supplier_code2,
            raw_material=raw_material, joint_type=joint_type,
            remark=remark, created_by=request.user,
            status=req_status, tool_code='[DRAFT]', # Temporary code
        )

        # 6. Save Attributes
        field_attrs = FieldAttribute.objects.filter(field=description)
        for attr in field_attrs:
            val = request.POST.get(f'attr_{attr.id}', '').strip()
            if val:
                ToolRequestAttribute.objects.create(
                    tool_request=tool_request, field_attribute=attr,
                    attr_name=attr.attr_name, value=val,
                )

        # 7. Generate Code ONLY if submitted
        if req_status == 'Pending':
            tool_request.tool_code = tool_request.generate_tool_code()
            tool_request.save()
            messages.success(request, f'Tool request submitted! Code: {tool_request.tool_code}')
        else:
            messages.success(request, 'Tool request safely saved as a Draft.')
            
        return redirect('tool_code')


    # ── EDIT (resubmit rejected or draft) submission ──
    if request.method == 'POST' and request.POST.get('form_action') == 'edit':

        if not role or not role.can_create_requests:
            messages.error(request, 'You do not have permission to edit tool requests.')
            return redirect('tool_code')

        req_id = request.POST.get('request_id')
        tool_request = get_object_or_404(ToolRequest, id=req_id, created_by=request.user)
        
        if tool_request.status not in ['Rejected', 'Draft']:
            messages.error(request, 'You cannot edit this request.')
            return redirect('tool_code')

        # 1. Check which button the user clicked
        action_type = request.POST.get('action_type', 'submit')
        req_status = 'Draft' if action_type == 'draft' else 'Pending'

        # 2. Get all IDs
        description_id  = request.POST.get('description')
        supplier1_id    = request.POST.get('supplier1')
        supplier2_id    = request.POST.get('supplier2')
        supplier_code1  = request.POST.get('supplier_code1', '')
        supplier_code2  = request.POST.get('supplier_code2', '')
        raw_material_id = request.POST.get('raw_material')
        joint_type_id   = request.POST.get('joint_type')
        fixed_value_id  = request.POST.get('fixed_value_id')
        remark          = request.POST.get('remark', '')

        # 3. Validation
        if not description_id:
            messages.error(request, 'You must at least select a Primary Description.')
            return redirect('tool_code')

        if req_status == 'Pending':
            if not all([supplier1_id, raw_material_id, joint_type_id]):
                messages.error(request, 'Please fill in all required fields to submit.')
                return redirect('tool_code')

        # 4. Update the Request Object
        tool_request.description  = get_object_or_404(Field, id=description_id)
        tool_request.supplier1    = Supplier.objects.filter(id=supplier1_id).first() if supplier1_id else None
        tool_request.supplier2    = Supplier.objects.filter(id=supplier2_id).first() if supplier2_id else None
        tool_request.raw_material = RawMaterial.objects.filter(id=raw_material_id).first() if raw_material_id else None
        tool_request.joint_type   = JointType.objects.filter(id=joint_type_id).first() if joint_type_id else None
        tool_request.fixed_value  = FieldFixedValue.objects.filter(id=fixed_value_id).first() if fixed_value_id else None
        
        tool_request.supplier_code1 = supplier_code1
        tool_request.supplier_code2 = supplier_code2
        tool_request.remark         = remark
        tool_request.status         = req_status  
        tool_request.reject_reason  = ''
        tool_request.tool_code      = '[DRAFT]'
        tool_request.save()

        # 5. Replace attributes
        tool_request.attributes.all().delete()
        field_attrs = FieldAttribute.objects.filter(field=tool_request.description)
        for attr in field_attrs:
            val = request.POST.get(f'attr_{attr.id}', '').strip()
            if val:
                ToolRequestAttribute.objects.create(
                    tool_request=tool_request, field_attribute=attr,
                    attr_name=attr.attr_name, value=val,
                )

        # 6. Generate Code ONLY if submitted
        if req_status == 'Pending':
            tool_request.tool_code = tool_request.generate_tool_code()
            tool_request.save()
            messages.success(request, f'Request resubmitted! Code: {tool_request.tool_code}')
        else:
            messages.success(request, 'Draft updated successfully.')
            
        return redirect('tool_code')

    # Load initial page
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
    if (not role or not role.can_approve_requests) and req.created_by != request.user:
        return redirect('tool_code')

    return render(request, 'review_request.html', {'req': req})


@login_required
def approve_request(request, id):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_approve_requests:
        return redirect('dashboard')
        
    if request.method == 'POST':
        tool = get_object_or_404(ToolRequest, id=id)
        tool.status = 'Approved'
        tool.reviewed_by = request.user 
        tool.reviewed_at = timezone.now() 
        tool.save()
        messages.success(request, f"Tool code '{tool.tool_code}' approved.")
    return redirect('tool_code')


@login_required
def reject_request(request, id):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_approve_requests:
        return redirect('dashboard')
        
    req = get_object_or_404(ToolRequest, id=id)
    if request.method == 'POST':
        req.status        = 'Rejected'
        req.reject_reason = request.POST.get('reject_reason', '')
        req.reviewed_by   = request.user 
        req.reviewed_at   = timezone.now() 
        req.save()
        messages.success(request, f"Tool code '{req.tool_code}' rejected.")
    return redirect('tool_code')


# ─────────────────────────────────────────
# FIELD MASTER
# ─────────────────────────────────────────

@login_required
def create_field_form(request):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
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

    # Fetch ALL fields (both Active and Inactive) for the Master Data table
    fields = Field._base_manager.all().order_by('id')
    return render(request, 'create_field_form.html', {'fields': fields})


@login_required
def toggle_field_status(request, id):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return redirect('dashboard')
        
    if request.method == 'POST':
        # Grab the field even if it is currently marked as deleted
        field = get_object_or_404(Field._base_manager, id=id)
        
        # Toggle the boolean value
        field.is_deleted = not field.is_deleted
        field.save()
        
        status = "deactivated" if field.is_deleted else "activated"
        messages.success(request, f"Field '{field.field_name}' successfully {status}.")
        
    return redirect('create_field_form')


# ─────────────────────────────────────────
# FIELD ATTRIBUTE MASTER 
# ─────────────────────────────────────────

@login_required
def field_attribute_master(request):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return redirect('dashboard')

    fields            = Field.objects.all()
    selected_field_id = request.GET.get('field_id')
    selected_field    = None
    attributes        = []

    if selected_field_id:
        selected_field = Field.objects.filter(id=selected_field_id).first()
        if selected_field:
            
            attributes = FieldAttribute._base_manager.filter(
                field=selected_field).order_by('order', 'id')

    if request.method == 'POST':
        action   = request.POST.get('action')
        field_id = request.POST.get('field_id') or selected_field_id

        if action == 'add':
            attr_name   = request.POST.get('attr_name', '').strip()
            input_type  = request.POST.get('input_type', 'number')
            is_required = request.POST.get('is_required') == 'on'
            order       = request.POST.get('order', 0)

            if field_id and attr_name:
                attr = FieldAttribute.objects.create(
                    field       = get_object_or_404(Field, id=field_id),
                    attr_name   = attr_name,
                    input_type  = input_type,
                    is_required = is_required,
                    order       = order,
                )
                # Save dropdown options submitted with the form
                if input_type == 'select':
                    options = request.POST.getlist('dropdown_options')
                    for i, opt_val in enumerate(options, start=1):
                        opt_val = opt_val.strip()
                        if opt_val:
                            FieldAttributeOption.objects.create(
                                attribute    = attr,
                                option_value = opt_val,
                                order        = i,
                            )
                messages.success(request, f'Attribute "{attr_name}" added.')
            return redirect(f'/field-attributes/?field_id={field_id}')

        elif action == 'toggle':
            attr = get_object_or_404(FieldAttribute._base_manager, id=request.POST.get('attr_id'))
            field_id = attr.field.id
            
            attr.is_deleted = not attr.is_deleted
            attr.save()
            
            status = "deactivated" if attr.is_deleted else "activated"
            messages.success(request, f'Attribute successfully {status}.')
            return redirect(f'/field-attributes/?field_id={field_id}')

        elif action == 'edit':
            
            attr     = get_object_or_404(FieldAttribute._base_manager, id=request.POST.get('attr_id'))
            field_id = attr.field.id
            attr.attr_name   = request.POST.get('attr_name', attr.attr_name).strip()
            attr.input_type  = request.POST.get('input_type', attr.input_type)
            attr.is_required = request.POST.get('is_required') == 'on'
            attr.order       = request.POST.get('order', attr.order)
            attr.save()
            messages.success(request, 'Attribute updated.')
            return redirect(f'/field-attributes/?field_id={field_id}')

        elif action == 'add_option':
            attr_id      = request.POST.get('attr_id')
            option_value = request.POST.get('option_value', '').strip().upper()
            if attr_id and option_value:
                attr = get_object_or_404(FieldAttribute._base_manager, id=attr_id)
                FieldAttributeOption.objects.create(
                    attribute    = attr,
                    option_value = option_value,
                    order        = attr.options.count() + 1,
                )
                messages.success(request, f'Option "{option_value}" added.')
            return redirect(f'/field-attributes/?field_id={field_id}')

        elif action == 'delete_option':
            # SOFT DELETE — not hard delete
            option = get_object_or_404(FieldAttributeOption, id=request.POST.get('option_id'))
            field_id = option.attribute.field.id
            option.soft_delete()
            messages.success(request, 'Option removed.')
            return redirect(f'/field-attributes/?field_id={field_id}')

    return render(request, 'field_attributes.html', {
        'fields':            fields,
        'selected_field':    selected_field,
        'selected_field_id': selected_field_id,
        'attributes':        attributes,
    })





# ─────────────────────────────────────────
# FIELD FIXED VALUE
# ─────────────────────────────────────────

@login_required
def create_field_fixed_value_form(request):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return redirect('dashboard')
    fields = Field.objects.all()
    selected_field  = request.GET.get('field')
    fixed_values    = FieldFixedValue._base_manager.filter(field_id=selected_field) if selected_field else None
    return render(request, 'create_field_fixed_value_form.html', {
        'fields':         fields,
        'fixed_values':   fixed_values,
        'selected_field': selected_field,
    })


@login_required
def add_fixed_value(request):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        data  = json.loads(request.body)
        field = Field.objects.get(id=data.get('field_id'))
        obj   = FieldFixedValue.objects.create(
            field       = field,
            fixed_value = data.get('value'),
            explanation = data.get('explanation'),
        )
        # 🌟 CHANGED: Return is_deleted
        return JsonResponse({'id': obj.id, 'value': obj.fixed_value, 'explanation': obj.explanation, 'is_deleted': obj.is_deleted})


@login_required
def edit_fixed_value(request, id):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    # 🌟 CHANGED: Use _base_manager so inactive items can be edited
    value = get_object_or_404(FieldFixedValue._base_manager, id=id)
    if request.method == 'POST':
        data = json.loads(request.body)
        value.fixed_value = data.get('value')
        value.explanation = data.get('explanation')
        value.save()
        # 🌟 CHANGED: Return is_deleted
        return JsonResponse({'id': value.id, 'value': value.fixed_value, 'explanation': value.explanation, 'is_deleted': value.is_deleted})


# 🌟 CHANGED: Completely replaced delete with toggle logic
@login_required
def toggle_fixed_value(request, id):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        value = get_object_or_404(FieldFixedValue._base_manager, id=id)
        value.is_deleted = not value.is_deleted
        value.save()
        
        return JsonResponse({'id': value.id, 'value': value.fixed_value, 'explanation': value.explanation, 'is_deleted': value.is_deleted})


# ─────────────────────────────────────────
# SUPPLIER MASTER
# ─────────────────────────────────────────

@login_required
def supplier_master(request):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return redirect('dashboard')
        
    if request.method == 'POST':
        Supplier.objects.create(
            supplier_name          = request.POST.get('supplier'),
            supplier_ordering_code = request.POST.get('supplier_code'),
        )
        return redirect('supplier_master')
        
    # 🌟 Fetch ALL suppliers (both Active and Inactive)
    suppliers = Supplier._base_manager.all().order_by('id')
    return render(request, 'supplier_master.html', {'suppliers': suppliers})


@login_required
def toggle_supplier_status(request, id):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return redirect('dashboard')
        
    if request.method == 'POST':
        # Grab the supplier even if it is currently marked as deleted
        supplier = get_object_or_404(Supplier._base_manager, id=id)
        
        # Toggle the boolean value
        supplier.is_deleted = not supplier.is_deleted
        supplier.save()
        
        status = "deactivated" if supplier.is_deleted else "activated"
        messages.success(request, f"Supplier '{supplier.supplier_name}' successfully {status}.")
        
    return redirect('supplier_master')


# ─────────────────────────────────────────
# RAW MATERIAL MASTER
# ─────────────────────────────────────────

@login_required
def raw_material_master(request):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return redirect('dashboard')
        
    if request.method == 'POST':
        RawMaterial.objects.create(raw_material_name=request.POST.get('raw_material'))
        return redirect('raw_material_master')
        
    # 🌟 Fetch ALL materials (both Active and Inactive)
    materials = RawMaterial._base_manager.all().order_by('id')
    return render(request, 'raw_material_master.html', {'materials': materials})


@login_required
def toggle_raw_material_status(request, id):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return redirect('dashboard')
        
    if request.method == 'POST':
        # Grab the material even if it is currently marked as deleted
        material = get_object_or_404(RawMaterial._base_manager, id=id)
        
        # Toggle the boolean value
        material.is_deleted = not material.is_deleted
        material.save()
        
        status = "deactivated" if material.is_deleted else "activated"
        messages.success(request, f"Raw Material '{material.raw_material_name}' successfully {status}.")
        
    return redirect('raw_material_master')


# ─────────────────────────────────────────
# JOINT TYPE MASTER
# ─────────────────────────────────────────

@login_required
def joint_type_master(request):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return redirect('dashboard')
        
    if request.method == 'POST':
        JointType.objects.create(joint_type_name=request.POST.get('joint_type'))
        return redirect('joint_type_master')
        
    # 🌟 Fetch ALL joint types (both Active and Inactive)
    joint_types = JointType._base_manager.all().order_by('id')
    return render(request, 'joint_type_master.html', {'joint_types': joint_types})


@login_required
def toggle_joint_type_status(request, id):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return redirect('dashboard')
        
    if request.method == 'POST':
        # Grab the joint type even if it is currently marked as deleted
        joint = get_object_or_404(JointType._base_manager, id=id)
        
        # Toggle the boolean value
        joint.is_deleted = not joint.is_deleted
        joint.save()
        
        status = "deactivated" if joint.is_deleted else "activated"
        messages.success(request, f"Joint Type '{joint.joint_type_name}' successfully {status}.")
        
    return redirect('joint_type_master')


# ─────────────────────────────────────────
# USER CREATION
# ─────────────────────────────────────────

@login_required
def user_creation(request):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_manage_users:
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
        
        # Fetch the actual Role object
        role_id = request.POST.get('role')
        assigned_role = Role.objects.filter(id=role_id).first()
        
        if assigned_role:
            UserProfile.objects.create(user=user, role=assigned_role)
            messages.success(request, f"User '{username}' created successfully.")
        else:
            # If someone tampered with the role ID, delete the user we just made so we don't have orphan accounts
            user.delete() 
            messages.error(request, 'Invalid role selected. User creation failed.')
            return redirect('user_creation')
            
        return redirect('dashboard')
        
    # Send the dynamic roles to the HTML page so they can be selected
     
    return render(request, 'user_creation.html', {'roles': Role.objects.filter(is_deleted=False)})


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
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_reports:
        messages.error(request, 'You do not have permission to view reports.')
        return redirect('dashboard')

    report_data  = ToolRequest.objects.exclude(status='Draft').order_by('-created_at')
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


# ─────────────────────────────────────────
# ROLE MASTER
# ─────────────────────────────────────────

@login_required
def role_master(request):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_manage_roles:
        messages.error(request, 'You do not have permission to manage roles.')
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            name = request.POST.get('role_name', '').strip()
            # Still use standard objects here so we don't accidentally create duplicates of active roles
            if Role.objects.filter(name__iexact=name, is_deleted=False).exists():
                messages.error(request, f'Role "{name}" already exists.')
            else:
                Role.objects.create(
                    name=name,
                    can_access_tool_code=request.POST.get('can_access_tool_code') == 'on',
                    can_create_requests=request.POST.get('can_create_requests') == 'on',
                    can_approve_requests=request.POST.get('can_approve_requests') == 'on',
                    can_access_master=request.POST.get('can_access_master') == 'on',
                    can_access_reports=request.POST.get('can_access_reports') == 'on',
                    can_manage_users=request.POST.get('can_manage_users') == 'on',
                    can_manage_roles=request.POST.get('can_manage_roles') == 'on',
                )
                messages.success(request, f'Role "{name}" created successfully.')

        elif action == 'edit':
            role_id = request.POST.get('role_id')
            #  Use _base_manager so inactive roles can still be edited
            edit_role = get_object_or_404(Role._base_manager, id=role_id)
            edit_role.name = request.POST.get('role_name', edit_role.name).strip()
            edit_role.can_access_tool_code = request.POST.get('can_access_tool_code') == 'on'
            edit_role.can_create_requests = request.POST.get('can_create_requests') == 'on'
            edit_role.can_approve_requests = request.POST.get('can_approve_requests') == 'on'
            edit_role.can_access_master = request.POST.get('can_access_master') == 'on'
            edit_role.can_access_reports = request.POST.get('can_access_reports') == 'on'
            edit_role.can_manage_users = request.POST.get('can_manage_users') == 'on'
            edit_role.can_manage_roles = request.POST.get('can_manage_roles') == 'on'
            edit_role.save()
            messages.success(request, f'Role "{edit_role.name}" updated.')

        # Replaced 'delete' with 'toggle'
        elif action == 'toggle':
            role_id = request.POST.get('role_id')
            toggle_role = get_object_or_404(Role._base_manager, id=role_id)
            
            # Keep Super Admin protected
            if toggle_role.name == "Super Admin":
                messages.error(request, "Cannot deactivate the Super Admin role.")
            else:
                toggle_role.is_deleted = not toggle_role.is_deleted
                toggle_role.save()
                status = "deactivated" if toggle_role.is_deleted else "activated"
                messages.success(request, f'Role "{toggle_role.name}" successfully {status}.')

        return redirect('role_master')

    #  Fetch ALL roles (both Active and Inactive) to draw the table
    roles = Role._base_manager.all().order_by('id')
    return render(request, 'role_master.html', {'roles': roles})


# ─────────────────────────────────────────
# FORMAT MASTER 
# ─────────────────────────────────────────

@login_required
def format_master(request):
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    if not role or not role.can_access_master:
        return redirect('dashboard')

    from .models import PdfFooterConfig
    config = PdfFooterConfig.get_config()

    if request.method == 'POST':
        config.footer_left   = request.POST.get('footer_left',   '').strip()
        config.footer_center = request.POST.get('footer_center', '').strip()
        config.footer_right  = request.POST.get('footer_right',  '').strip()
        config.updated_by    = request.user
        config.save()
        messages.success(request, 'PDF footer configuration saved successfully.')
        return redirect('format_master')

    return render(request, 'format_master.html', {'config': config})


# ─────────────────────────────────────────
# DOWNLOAD TOOL REQUEST PDF 
# ─────────────────────────────────────────

@login_required
def download_tool_request_pdf(request, id):
    from django.http import HttpResponse
    from .pdf_generator import generate_tool_request_pdf

    req = get_object_or_404(ToolRequest, id=id)

    # Permission check — user can only download their own, admin/approver can download any
    role = request.user.userprofile.role if hasattr(request.user, 'userprofile') else None
    can_approve = role and role.can_approve_requests
    if not can_approve and req.created_by != request.user:
        messages.error(request, 'You do not have permission to download this request.')
        return redirect('tool_code')

    buffer = generate_tool_request_pdf(req)

    filename = f"ToolRequest_{req.tool_code or req.id}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response