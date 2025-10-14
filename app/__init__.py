import datetime
from flask import Flask, jsonify, redirect, render_template, request, g, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
import redis
import os
from config import config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()
cache = Cache()

def register_error_handlers(app):
    """Register custom error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html', error=error, debug=app.debug), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return render_template('errors/401.html', error=error, debug=app.debug), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', error=error, debug=app.debug), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html', error=error, debug=app.debug), 404
    
    @app.errorhandler(429)
    def too_many_requests(error):
        return render_template('errors/429.html', error=error, debug=app.debug), 429
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('errors/500.html', error=error, debug=app.debug), 500
    
    # Generic error handler for any unhandled exceptions
    @app.errorhandler(Exception)
    def handle_exception(error):
        # Pass through HTTP errors
        if hasattr(error, 'code'):
            return error
        
        # For non-HTTP exceptions, return a 500 error
        app.logger.error(f"Unhandled exception: {str(error)}")
        return render_template('errors/500.html', error=error, debug=app.debug), 500

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)
    
    # Redis configuration
    app.redis = redis.from_url(app.config['REDIS_URL'])
    
    # Cache configuration
    cache.init_app(app, config={
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': app.config['REDIS_URL'],
        'CACHE_DEFAULT_TIMEOUT': 300
    })
    
    # Login configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = "strong"
    
    # Register middleware
    from app.middleware.tenant_middleware import tenant_middleware
    app.before_request(tenant_middleware)
    
    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    
    from app.products import bp as products_bp
    app.register_blueprint(products_bp, url_prefix='/products')
    
    from app.sales import bp as sales_bp
    app.register_blueprint(sales_bp, url_prefix='/sales')
    
    from app.customers import bp as customers_bp
    app.register_blueprint(customers_bp, url_prefix='/customers')
    
    from app.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')
    
    from app.settings import bp as settings_bp
    app.register_blueprint(settings_bp, url_prefix='/settings')

    from .superadmin import bp as superadmin_bp
    app.register_blueprint(superadmin_bp, url_prefix='/superadmin')

    from .marketplace import bp as marketplace_bp
    app.register_blueprint(marketplace_bp, url_prefix='/marketplace')

    register_error_handlers(app)
    
    # Main index route
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.index'))
    @app.route('/favicon.ico')
    def favicon():
        from flask import send_from_directory
        import os
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                'favicon.ico', mimetype='image/vnd.microsoft.icon')
    
    # Health check route for deployment
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})
    
    @app.context_processor
    def inject_debug():
        """Inject debug status into all templates"""
        return dict(debug=app.debug)

# Handle template rendering errors specifically
    @app.errorhandler(500)
    def internal_server_error(error):
        # Log the error with more context
        app.logger.error(f"""
        Internal Server Error:
        Path: {request.path}
        Method: {request.method}
        User: {getattr(current_user, 'username', 'Anonymous')}
        IP: {request.remote_addr}
        Error: {str(error)}
        """)
        
        return render_template('errors/500.html', error=error, debug=app.debug), 500
    
    return app