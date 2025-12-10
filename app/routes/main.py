from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
import os
import docker
from datetime import datetime
import requests

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page"""
    if 'user_id' not in session:
        return redirect(url_for('main.login_page'))
    return render_template('index.html')

@main_bp.route('/login')
def login_page():
    """Login page"""
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    return render_template('login.html')

@main_bp.route('/api/system-info', methods=['GET'])
def get_system_info():
    """Get system information"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get Docker compose version
    docker_compose_version = check_docker_compose_version()
    
    # Check mirror availability
    mirrors_status = check_mirrors()
    
    # Get app version
    app_version = os.environ.get('APP_VERSION', '1.0.0')
    
    return jsonify({
        'docker_compose_version': docker_compose_version,
        'mirrors_status': mirrors_status,
        'app_version': app_version,
        'current_time': datetime.utcnow().isoformat()
    })

def check_docker_compose_version():
    """Check Docker Compose version"""
    import subprocess
    try:
        # Try v2 first
        result = subprocess.run(['docker', 'compose', 'version'], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return {'version': 'v2', 'details': result.stdout.strip()}
        
        # Try v1
        result = subprocess.run(['docker-compose', 'version'], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return {'version': 'v1', 'details': result.stdout.strip()}
        
        return {'version': 'unknown', 'error': 'Docker Compose not found'}
    except Exception as e:
        return {'version': 'error', 'error': str(e)}

def check_mirrors():
    """Check mirror availability"""
    mirrors = [
        'https://docker.1ms.run',
        'https://docker.1panel.live'
    ]
    status = {}
    
    for mirror in mirrors:
        try:
            response = requests.head(mirror, timeout=3)
            status[mirror] = {'available': response.status_code < 400, 'status_code': response.status_code}
        except Exception as e:
            status[mirror] = {'available': False, 'error': str(e)}
    
    return status

@main_bp.route('/api/docker-stats', methods=['GET'])
def get_docker_stats():
    """Get Docker stats"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
        images = client.images.list()
        
        return jsonify({
            'containers_count': len(containers),
            'running_containers_count': len([c for c in containers if c.status == 'running']),
            'images_count': len(images)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get Docker stats: {str(e)}'}), 500

@main_bp.route('/api/settings/github-token', methods=['GET'])
def get_github_token():
    """Get Github token from session"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    token = session.get('github_token', '')
    return jsonify({
        'success': True,
        'token': token,
        'has_token': bool(token)
    })

@main_bp.route('/api/settings/github-token', methods=['POST'])
def set_github_token():
    """Set Github token in session"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    if not data or 'token' not in data:
        return jsonify({'error': 'Token is required'}), 400
    
    # Validate token format (simple check - Github tokens are alphanumeric strings)
    token = data['token'].strip()
    
    # Store token in session
    session['github_token'] = token
    
    return jsonify({
        'success': True,
        'message': 'Github token saved successfully',
        'has_token': bool(token)
    })

@main_bp.route('/api/settings/github-token', methods=['DELETE'])
def clear_github_token():
    """Clear Github token from session"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Remove token from session
    if 'github_token' in session:
        del session['github_token']
    
    return jsonify({
        'success': True,
        'message': 'Github token cleared successfully',
        'has_token': False
    })