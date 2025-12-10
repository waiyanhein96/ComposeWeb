from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import logging
from dotenv import load_dotenv
import bcrypt
import secrets

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize extensions
db = SQLAlchemy()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure the app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///./docker_compose_file.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions with the app
    db.init_app(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.docker import docker_bp
    #from app.routes.gitee import gitee_bp
    from app.routes.github import github_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(docker_bp)
    #app.register_blueprint(gitee_bp)
    app.register_blueprint(github_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Initialize admin user if not exists
        from app.models.user import User
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        
        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            # Generate a 16-character strong password with special characters
            import string
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            admin_password = ''.join(secrets.choice(alphabet) for i in range(16))
            
            # Log the generated password at INFO level
            logger.info(f'Generated admin password: {admin_password}')
            
            # Hash the password
            hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
            admin = User(
                username=admin_username,
                password=hashed_password.decode('utf-8'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}
    
    return app