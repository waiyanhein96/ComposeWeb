from app import db
from datetime import datetime

class User(db.Model):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class DockerComposeFile(db.Model):
    """Model to track docker-compose files"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    system_type = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(50), nullable=False)  # 'local' or 'gitee'
    file_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DockerComposeFile {self.filename} ({self.system_type})>'

class DeploymentLog(db.Model):
    """Model to track deployment logs"""
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('docker_compose_file.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # 'pending', 'deploying', 'success', 'failed'
    command = db.Column(db.String(500), nullable=False)
    output = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    file = db.relationship('DockerComposeFile', backref='deployment_logs')
    
    def __repr__(self):
        return f'<DeploymentLog {self.id} - {self.status}>'