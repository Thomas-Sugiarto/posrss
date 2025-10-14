from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import uuid
import os

from . import bp
from .forms import MarketplaceItemForm
from ..models import MarketplaceItem, Product, db
from ..superadmin.routes import superadmin_required
from app.services.s3_service import S3Service  # Import S3Service

# --- Rute untuk Tenant ---
@bp.route('/')
@login_required
def index():
    """Halaman Marketplace untuk dilihat oleh Tenant."""
    items = MarketplaceItem.query.filter(MarketplaceItem.stock > 0).order_by(MarketplaceItem.created_at.desc()).all()
    return render_template('marketplace/index.html', items=items, title="Marketplace")

@bp.route('/restock/<string:item_id>', methods=['POST'])
@login_required
def restock_item(item_id):
    """Menambahkan item dari marketplace ke daftar produk tenant."""
    item_to_restock = MarketplaceItem.query.get_or_404(item_id)
    
    # Ambil jumlah dari form, default 1
    quantity_to_add = int(request.form.get('quantity', 1))

    if quantity_to_add <= 0:
        flash('Invalid quantity.', 'danger')
        return redirect(url_for('marketplace.index'))

    existing_product = Product.query.filter_by(tenant_id=current_user.tenant_id, name=item_to_restock.name).first()
    
    if existing_product:
        existing_product.stock += quantity_to_add
        flash(f'Stock for "{existing_product.name}" has been increased by {quantity_to_add}.', 'success')
    else:
        new_product = Product(
            id=str(uuid.uuid4()),
            name=item_to_restock.name,
            description=item_to_restock.description,
            price=item_to_restock.price,
            stock=quantity_to_add,
            sku=item_to_restock.sku,
            tenant_id=current_user.tenant_id
        )
        db.session.add(new_product)
        flash(f'"{item_to_restock.name}" has been added to your products.', 'success')
        
    db.session.commit()
    return redirect(url_for('products.index'))

# --- Rute untuk Superadmin ---

@bp.route('/manage')
@login_required
@superadmin_required
def manage():
    """Halaman Superadmin untuk mengelola semua item marketplace."""
    items = MarketplaceItem.query.order_by(MarketplaceItem.name).all()
    return render_template('marketplace/manage.html', items=items, title="Manage Marketplace")

@bp.route('/manage/new', methods=['GET', 'POST'])
@login_required
@superadmin_required
def create_item():
    """Form untuk membuat item marketplace baru."""
    form = MarketplaceItemForm()
    
    if form.validate_on_submit():
        try:
            new_item = MarketplaceItem(
                id=str(uuid.uuid4()),
                name=form.name.data,
                description=form.description.data,
                price=form.price.data,
                stock=form.stock.data,
                sku=form.sku.data
            )
            
            # Handle image upload - SAMA PERSIS seperti di products routes
            if form.image.data:
                s3_service = S3Service()  # Inisialisasi di dalam function
                image_url = s3_service.upload_product_image(form.image.data, f"marketplace_{new_item.id}")
                new_item.image_url = image_url
            
            db.session.add(new_item)
            db.session.commit()
            
            flash(f'Item "{new_item.name}" has been created.', 'success')
            return redirect(url_for('marketplace.manage'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating marketplace item: {str(e)}")
            flash(f'Error creating item: {str(e)}', 'danger')
        
    return render_template('marketplace/create_edit_item.html', form=form, title="Create Marketplace Item", legend="New Marketplace Item")

@bp.route('/manage/edit/<string:item_id>', methods=['GET', 'POST'])
@login_required
@superadmin_required
def edit_item(item_id):
    """Form untuk mengedit item marketplace yang ada."""
    item = MarketplaceItem.query.get_or_404(item_id)
    form = MarketplaceItemForm(obj=item)
    
    if form.validate_on_submit():
        try:
            item.name = form.name.data
            item.description = form.description.data
            item.price = form.price.data
            item.stock = form.stock.data
            item.sku = form.sku.data

            # Handle image upload - SAMA PERSIS seperti di products routes
            if form.image.data:
                s3_service = S3Service()  # Inisialisasi di dalam function
                image_url = s3_service.upload_product_image(form.image.data, f"marketplace_{item.id}")
                
                # Hapus gambar lama jika ada
                if item.image_url:
                    try:
                        # Extract object name dari URL
                        old_image_url = item.image_url
                        if 'amazonaws.com/' in old_image_url:
                            object_name = old_image_url.split('amazonaws.com/')[1]
                            s3_service.delete_file(object_name)
                    except Exception as e:
                        current_app.logger.warning(f"Could not delete old image: {str(e)}")
                
                item.image_url = image_url

            db.session.commit()
            flash(f'Item "{item.name}" has been updated.', 'success')
            return redirect(url_for('marketplace.manage'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating marketplace item: {str(e)}")
            flash(f'Error updating item: {str(e)}', 'danger')

    return render_template('marketplace/create_edit_item.html', form=form, title="Edit Marketplace Item", legend=f"Edit {item.name}")


@bp.route('/manage/delete/<string:item_id>', methods=['POST'])
@login_required
@superadmin_required
def delete_item(item_id):
    """Menghapus item dari marketplace."""
    item = MarketplaceItem.query.get_or_404(item_id)
    
    try:
        # Hapus gambar dari S3 jika ada
        if item.image_url:
            try:
                s3_service = S3Service()  # Inisialisasi di dalam function
                # Extract object name dari URL
                if 'amazonaws.com/' in item.image_url:
                    object_name = item.image_url.split('amazonaws.com/')[1]
                    s3_service.delete_file(object_name)
            except Exception as e:
                current_app.logger.warning(f"Could not delete image from S3: {str(e)}")
        
        # Hapus item dari database
        db.session.delete(item)
        db.session.commit()
        flash(f'Item "{item.name}" has been deleted.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting marketplace item: {str(e)}")
        flash(f'Error deleting item: {str(e)}', 'danger')
    
    return redirect(url_for('marketplace.manage'))