import boto3
from flask import current_app
import uuid
import os
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.s3_client = None
        self.bucket_name = current_app.config.get('S3_BUCKET_NAME')
        self.region = current_app.config.get('S3_REGION', 'us-east-1')  # Pastikan ini di-set
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize S3 client dengan credentials"""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=current_app.config.get('S3_ACCESS_KEY'),
                aws_secret_access_key=current_app.config.get('S3_SECRET_KEY'),
                region_name=self.region  # Gunakan self.region di sini
            )
            
            # Verify bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 client initialized successfully for bucket: {self.bucket_name} in region: {self.region}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 client initialization failed: {error_code} - {str(e)}")
            return False
        except Exception as e:
            logger.error(f"S3 configuration error: {str(e)}")
            return False
    
    def upload_product_image(self, file, product_id=None):
        """Upload gambar produk ke S3"""
        try:
            if not self.s3_client:
                if not self.initialize_client():
                    raise Exception("S3 client not available")
            
            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1].lower()
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
            
            if file_extension not in allowed_extensions:
                raise ValueError(f"File type {file_extension} not allowed")
            
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            if product_id:
                s3_key = f"products/{product_id}/{unique_filename}"
            else:
                s3_key = f"products/{unique_filename}"
            
            # Upload file ke S3 - TANPA ACL
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': file.content_type
                    # HAPUS: 'ACL': 'public-read'
                }
            )
            
            # Generate public URL - GUNAKAN self.region
            if self.region == 'us-east-1':
                url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            else:
                url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            logger.info(f"✅ Image uploaded successfully: {s3_key}")
            logger.info(f"✅ Public URL: {url}")
            
            return url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"❌ S3 upload error {error_code}: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"❌ Image upload error: {str(e)}")
            raise e
    
    def check_file_public_access(self, object_name):
        """Check if a file is publicly accessible"""
        try:
            # Try to access without credentials
            public_s3 = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))
            response = public_s3.head_object(
                Bucket=self.bucket_name,
                Key=object_name
            )
            return True
        except ClientError as e:
            logger.error(f"File not publicly accessible: {str(e)}")
            return False
    
    def generate_presigned_url(self, object_name, expiration=3600):
        """Generate presigned URL untuk akses private files"""
        try:
            if not self.s3_client:
                self.initialize_client()
            
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name, 
                    'Key': object_name
                },
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"S3 presigned URL error: {str(e)}")
            return None
    
    def delete_file(self, object_name):
        """Delete file dari S3"""
        try:
            if not self.s3_client:
                self.initialize_client()
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_name
            )
            logger.info(f"File deleted from S3: {object_name}")
            return True
        except ClientError as e:
            logger.error(f"S3 delete error: {str(e)}")
            return False
    
    def list_files(self, prefix=''):
        """List files dalam S3 bucket"""
        try:
            if not self.s3_client:
                self.initialize_client()
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'url': f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{obj['Key']}"
                    })
            
            return files
        except ClientError as e:
            logger.error(f"S3 list files error: {str(e)}")
            return []