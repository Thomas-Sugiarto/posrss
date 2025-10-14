from datetime import datetime
from flask import render_template, request, flash, redirect, url_for, jsonify, abort
from flask_login import login_required, current_user
from app.settings import bp
from app.models import Tenant, db, User
from app.services.printer_service import PrinterService
import json
from .forms import UserForm
from functools import wraps
import uuid
from wtforms.validators import DataRequired
def tenant_admin_required(f):
    """
    Decorator untuk memastikan hanya tenant_admin yang bisa mengakses suatu halaman.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'tenant_admin':
            abort(403) # Tampilkan halaman Forbidden jika bukan admin
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
def index():
    tenant = Tenant.query.get(current_user.tenant_id)
    return render_template('settings/index.html', tenant=tenant)

@bp.route('/users')
@login_required
@tenant_admin_required # Hanya tenant admin yang bisa akses
def user_management():
    """Menampilkan daftar semua pengguna dalam satu tenant."""
    users = User.query.filter_by(tenant_id=current_user.tenant_id).order_by(User.username).all()
    return render_template('settings/users.html', users=users, title="User Management")


@bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@tenant_admin_required
def create_user():
    """Halaman untuk membuat pengguna (kasir) baru."""
    form = UserForm()
    # Ganti validasi password menjadi wajib saat membuat user baru
    form.password.validators.insert(0, DataRequired())
    
    if form.validate_on_submit():
        new_user = User(
            id=str(uuid.uuid4()),
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            tenant_id=current_user.tenant_id
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash(f'User "{new_user.username}" has been created successfully.', 'success')
        return redirect(url_for('settings.user_management'))
    return render_template('settings/create_edit_user.html', form=form, title="Create New User", legend="New User")


@bp.route('/users/edit/<string:user_id>', methods=['GET', 'POST'])
@login_required
@tenant_admin_required
def edit_user(user_id):
    """Halaman untuk mengedit pengguna yang sudah ada."""
    user_to_edit = User.query.get_or_404(user_id)
    if user_to_edit.tenant_id != current_user.tenant_id:
        abort(403) # Pastikan admin hanya bisa mengedit user di tenantnya sendiri

    form = UserForm(obj=user_to_edit, original_email=user_to_edit.email)
    if form.validate_on_submit():
        user_to_edit.username = form.username.data
        user_to_edit.email = form.email.data
        user_to_edit.role = form.role.data
        if form.password.data:
            user_to_edit.set_password(form.password.data)
        db.session.commit()
        flash(f'User "{user_to_edit.username}" has been updated.', 'success')
        return redirect(url_for('settings.user_management'))
    return render_template('settings/create_edit_user.html', form=form, title="Edit User", legend=f"Edit User: {user_to_edit.username}")


@bp.route('/users/delete/<string:user_id>', methods=['POST'])
@login_required
@tenant_admin_required
def delete_user(user_id):
    """Logika untuk menghapus pengguna."""
    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('settings.user_management'))
    if user_to_delete.tenant_id != current_user.tenant_id:
        abort(403)
    
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'User "{user_to_delete.username}" has been deleted.', 'success')
    return redirect(url_for('settings.user_management'))

@bp.route('/tenant-info', methods=['GET', 'POST'])
@login_required
def tenant_info():
    tenant = Tenant.query.get(current_user.tenant_id)
    
    if request.method == 'POST':
        tenant.name = request.form.get('name')
        tenant.email = request.form.get('email')
        tenant.phone = request.form.get('phone')
        tenant.address = request.form.get('address')
        
        db.session.commit()
        flash('Tenant information updated successfully!', 'success')
        return redirect(url_for('settings.tenant_info'))
    
    return render_template('settings/tenant_info.html', tenant=tenant)

@bp.route('/printer-setup', methods=['GET', 'POST'])
@login_required
def printer_setup():
    tenant = Tenant.query.get(current_user.tenant_id)
    
    if request.method == 'POST':
        printer_type = request.form.get('printer_type')
        printer_host = request.form.get('printer_host')
        printer_port = request.form.get('printer_port', 9100)
        
        printer_settings = {
            'type': printer_type,
            'host': printer_host,
            'port': int(printer_port)
        }
        
        # Test printer connection
        printer_service = PrinterService()
        if printer_service.initialize_printer(printer_settings):
            tenant.printer_settings = printer_settings
            tenant.printer_type = printer_type
            db.session.commit()
            flash('Printer setup completed successfully!', 'success')
        else:
            flash('Failed to connect to printer. Please check settings.', 'danger')
    
    return render_template('settings/printer_setup.html', tenant=tenant, now=datetime.now())

@bp.route('/test-printer', methods=['POST'])
@login_required
def test_printer():
    """Test printer connection"""
    tenant = Tenant.query.get(current_user.tenant_id)
    
    printer_service = PrinterService()
    if printer_service.initialize_printer(tenant.printer_settings):
        try:
            # Print test receipt
            printer_service.printer.set(align='center')
            printer_service.printer.text("TEST PRINT\n")
            printer_service.printer.text("==========\n")
            printer_service.printer.text("Printer test successful!\n")
            printer_service.printer.text(f"Tenant: {tenant.name}\n")
            printer_service.printer.text(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            printer_service.printer.cut()
            
            return jsonify({'success': True, 'message': 'Test print successful!'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Print failed: {str(e)}'})
    
    return jsonify({'success': False, 'message': 'Printer connection failed'})

@bp.route('/barcode-scanner', methods=['GET', 'POST'])
@login_required
def barcode_scanner():
    tenant = Tenant.query.get(current_user.tenant_id)
    
    if request.method == 'POST':
        scanner_type = request.form.get('scanner_type', 'keyboard')
        tenant.barcode_scanner_type = scanner_type
        db.session.commit()
        flash('Barcode scanner settings updated!', 'success')
    
    return render_template('settings/barcode_scanner.html', tenant=tenant)

