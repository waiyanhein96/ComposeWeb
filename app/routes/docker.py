from flask import Blueprint, request, jsonify, session
import os
import subprocess
import threading
import uuid
import time
from app import db, create_app
from app.models.user import DockerComposeFile, DeploymentLog
import json

# Create blueprint
docker_bp = Blueprint('docker', __name__)

# Dictionary to store deployment processes
deployment_processes = {}

@docker_bp.route('/api/docker/deploy', methods=['POST'])
def deploy_compose():
    """Deploy a docker-compose file"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    if not data or not data.get('file_path'):
        return jsonify({'error': 'File path required'}), 400
    
    file_path = data['file_path']
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Determine Docker Compose version to use
    version_info = check_docker_compose_version()
    if version_info['version'] == 'unknown':
        return jsonify({'error': 'Docker Compose not available'}), 500
    
    # Create deployment log
    compose_file = DockerComposeFile.query.filter_by(file_path=file_path).first()
    deployment_id = str(uuid.uuid4())
    
    log_entry = DeploymentLog(
        file_id=compose_file.id if compose_file else 1,  # Default to 1 if not found
        status='pending',
        command=f"{'docker compose' if version_info['version'] == 'v2' else 'docker-compose'} -f {file_path} up -d"
    )
    db.session.add(log_entry)
    db.session.commit()
    
    # Store process info BEFORE starting thread
    deployment_processes[deployment_id] = {
        'log_id': log_entry.id,
        'thread': None,  # Will be set after thread creation
        'status': 'pending',
        'progress': 0,
        'output': ''
    }
    
    # Start deployment in a separate thread
    thread = threading.Thread(
        target=execute_deployment,
        args=(file_path, version_info['version'], log_entry.id, deployment_id)
    )
    thread.daemon = True
    thread.start()
    
    # Update thread reference in process info
    deployment_processes[deployment_id]['thread'] = thread
    
    return jsonify({
        'success': True,
        'deployment_id': deployment_id,
        'message': 'Deployment started',
        'version': version_info['version']
    })

@docker_bp.route('/api/docker/deployment/status/<deployment_id>', methods=['GET'])
def get_deployment_status(deployment_id):
    """Get deployment status"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if deployment_id not in deployment_processes:
        return jsonify({'error': 'Deployment not found'}), 404
    
    process_info = deployment_processes[deployment_id]
    log_entry = DeploymentLog.query.get(process_info['log_id'])
    
    return jsonify({
        'deployment_id': deployment_id,
        'status': log_entry.status if log_entry else process_info['status'],
        'progress': process_info['progress'],
        'output': process_info['output'],
        'completed': process_info['status'] in ['success', 'failed'],
        'created_at': log_entry.created_at.isoformat() if log_entry else None,
        'completed_at': log_entry.completed_at.isoformat() if log_entry and log_entry.completed_at else None
    })

@docker_bp.route('/api/docker/upgrade-compose', methods=['POST'])
def upgrade_docker_compose():
    """Upgrade Docker Compose to v2"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Install Docker Compose v2
        subprocess.run([
            'curl', '-SL', 
            'https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-linux-x86_64', 
            '-o', '/usr/local/bin/docker-compose'
        ], check=True, capture_output=True, text=True)
        
        # Make it executable
        subprocess.run(['chmod', '+x', '/usr/local/bin/docker-compose'], 
                      check=True, capture_output=True, text=True)
        
        # Create symlink if needed
        if not os.path.exists('/usr/local/bin/docker-compose'):
            subprocess.run(['ln', '-sf', '/usr/local/bin/docker-compose', '/usr/bin/docker-compose'], 
                          check=True, capture_output=True, text=True)
        
        return jsonify({'success': True, 'message': 'Docker Compose upgraded to v2 successfully'})
    except Exception as e:
        return jsonify({'error': f'Failed to upgrade Docker Compose: {str(e)}'}), 500

@docker_bp.route('/api/docker/stop/<container_id>', methods=['POST'])
def stop_container(container_id):
    """Stop a container"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        result = subprocess.run(['docker', 'stop', container_id], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return jsonify({'error': result.stderr.strip()}), 500
        return jsonify({'success': True, 'message': 'Container stopped'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@docker_bp.route('/api/docker/start/<container_id>', methods=['POST'])
def start_container(container_id):
    """Start a container"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        result = subprocess.run(['docker', 'start', container_id], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return jsonify({'error': result.stderr.strip()}), 500
        return jsonify({'success': True, 'message': 'Container started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@docker_bp.route('/api/docker/deployments', methods=['GET'])
def get_deployments():
    """Get deployment logs"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get all deployment logs, ordered by created_at descending
    deployments = DeploymentLog.query.order_by(DeploymentLog.created_at.desc()).all()
    
    # Format the response
    result = []
    for deployment in deployments:
        # Try to get file name from DockerComposeFile if available
        file_name = None
        if hasattr(deployment, 'file') and deployment.file:
            file_name = os.path.basename(deployment.file.file_path)
        
        result.append({
            'id': deployment.id,
            'file_name': file_name or 'Unknown file',
            'status': deployment.status,
            'command': deployment.command,
            'output': deployment.output,
            'created_at': deployment.created_at.isoformat() if deployment.created_at else None,
            'completed_at': deployment.completed_at.isoformat() if deployment.completed_at else None
        })
    
    return jsonify(result)

def execute_deployment(file_path, compose_version, log_id, deployment_id):
    """Execute deployment in a separate thread"""
    # Create application context for the thread
    app = create_app()
    with app.app_context():
        process_info = deployment_processes[deployment_id]
        log_entry = DeploymentLog.query.get(log_id)
    
        try:
            # Update status
            log_entry.status = 'deploying'
            db.session.commit()
            process_info['status'] = 'deploying'
            process_info['progress'] = 10
            
            # Build command
            cmd = ['docker', 'compose', '-f', file_path, 'up', '-d'] if compose_version == 'v2' else \
                  ['docker-compose', '-f', file_path, 'up', '-d']
            
            # Execute command
            process_info['progress'] = 30
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Read output
            output_lines = []
            for line in process.stdout:
                output_lines.append(line)
                process_info['output'] = ''.join(output_lines)
                # Update progress
                process_info['progress'] = min(90, process_info['progress'] + 5)
            
            # Wait for process to complete
            process.wait()
            
            # Update status based on exit code
            if process.returncode == 0:
                log_entry.status = 'success'
                process_info['status'] = 'success'
                process_info['progress'] = 100
            else:
                log_entry.status = 'failed'
                process_info['status'] = 'failed'
            
            log_entry.output = ''.join(output_lines)
            log_entry.completed_at = db.func.current_timestamp()
            db.session.commit()
            
        except Exception as e:
            if log_entry:
                log_entry.status = 'failed'
                log_entry.output = f'Error: {str(e)}'
                log_entry.completed_at = db.func.current_timestamp()
                db.session.commit()
            
            process_info['status'] = 'failed'
            process_info['output'] = f'Error: {str(e)}'
            process_info['progress'] = 0
        
        # Clean up after some time
        time.sleep(3600)  # Keep for 1 hour
        if deployment_id in deployment_processes:
            del deployment_processes[deployment_id]

def check_docker_compose_version():
    """Check Docker Compose version"""
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