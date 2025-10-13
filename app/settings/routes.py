from datetime import datetime
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.settings import bp
from app.models import Tenant, db
from app.services.printer_service import PrinterService
import json

@bp.route('/')
@login_required
def index():
    tenant = Tenant.query.get(current_user.tenant_id)
    return render_template('settings/index.html', tenant=tenant)

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