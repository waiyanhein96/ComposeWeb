from flask import Blueprint, request, jsonify, session
import os
import requests
import json
from app import db
from app.models.user import DockerComposeFile
import yaml
from app.services.gitee_service import GiteeService

# Create blueprint
gitee_bp = Blueprint('gitee', __name__)

# System types mapping
system_types = {
    'fnOS': '飞牛系统',
    'QNAP': '威联通系统',
    'Synology': '群晖系统',
    'TrueNAS': 'True系统',
    'UgreenNew': '绿联系统',
    'Ugreen': '绿联旧系统',
    'ZSpace': '极空间系统',
    'ZimaOS': 'Zima系统'
}

@gitee_bp.route('/api/gitee/files/<system_type>', methods=['GET'])
def get_gitee_files(system_type):
    """Get files from Gitee repository for a specific system type"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Validate system type
    if system_type not in system_types:
        return jsonify({'error': f'Invalid system type. Available: {list(system_types.keys())}'}), 400
    
    # Get Gitee token from session
    gitee_token = session.get('gitee_token', '')
    
    try:
        # Create GiteeService instance with token
        gitee_service = GiteeService(token=gitee_token)
        
        # Get files list
        success, data = gitee_service.get_files_list(system_type)
        
        if not success:
            error_msg = data.get('error', 'Unknown error')
            return jsonify({'error': error_msg}), 500
        
        # Ensure files data is valid
        if not isinstance(data, dict) or 'files' not in data:
            return jsonify({'error': 'Invalid data format from Gitee API'}), 500
        
        yml_files = data.get('files', [])
        
        # Prepare response data
        result = []
        try:
            for file in yml_files:
                # Check if file is valid
                if not isinstance(file, dict) or 'name' not in file:
                    continue
                
                # Check if file already exists in database
                existing_file = DockerComposeFile.query.filter_by(
                    filename=file['name'],
                    system_type=system_type,
                    source='gitee'
                ).first()
                
                result.append({
                    'name': file.get('name', 'Unknown'),
                    'download_url': file.get('download_url', ''),
                    'size': file.get('size', 0),
                    'updated_at': file.get('updated_at', ''),
                    'exists_locally': file.get('exists_locally', False) or (existing_file is not None)
                })
        except Exception:
            # Continue with the files we have so far
            pass
        
        return jsonify({
            'success': True,
            'system_type': system_type,
            'system_name': system_types[system_type],
            'files': result,
            'total': len(result)
        })
    
    except Exception as e:
        return jsonify({'error': f'Error fetching Gitee files: {str(e)}'}), 500

@gitee_bp.route('/api/gitee/download', methods=['POST'])
def download_gitee_file():
    """Download a file from Gitee"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    if not data or not data.get('download_url') or not data.get('system_type') or not data.get('filename'):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    download_url = data['download_url']
    system_type = data['system_type']
    filename = data['filename']
    
    # Validate system type
    if system_type not in system_types:
        return jsonify({'error': 'Invalid system type'}), 400
    
    # Get Gitee token from session
    gitee_token = session.get('gitee_token', '')
    
    try:
        # Create GiteeService instance with token
        gitee_service = GiteeService(token=gitee_token)
        success, data = gitee_service.download_file(download_url, system_type, filename)
        
        if not success:
            return jsonify(data), 500
        
        file_path = data.get('file_path')
        
        # Update database
        existing_file = DockerComposeFile.query.filter_by(
            filename=filename,
            system_type=system_type,
            source='gitee'
        ).first()
        
        if existing_file:
            existing_file.file_path = file_path
            db.session.commit()
        else:
            new_file = DockerComposeFile(
                filename=filename,
                system_type=system_type,
                source='gitee',
                file_path=file_path
            )
            db.session.add(new_file)
            db.session.commit()
        
        # Get file size
        size = os.path.getsize(file_path)
        
        return jsonify({
            'success': True,
            'message': 'File downloaded successfully',
            'file_path': file_path,
            'size': size
        })
    
    except Exception as e:
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500

@gitee_bp.route('/api/gitee/system-types', methods=['GET'])
def get_system_types():
    """Get all available system types"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get Gitee token from session
    gitee_token = session.get('gitee_token', '')
    
    try:
        # Check which system directories exist in Gitee
        api_url = os.environ.get('GITEE_API_URL', 'https://gitee.com/api/v5')
        repo = os.environ.get('GITEE_REPO', 'DoubleStackWorkShop/Docker-Compose-File')
        
        url = f"{api_url}/repos/{repo}/contents/"
        
        # 使用查询参数传递token
        params = {}
        if gitee_token:
            params['access_token'] = gitee_token
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # Handle different status codes
            if response.status_code == 200:
                try:
                    contents = response.json()
                    # Validate response format
                    if not isinstance(contents, list):
                        raise ValueError("Invalid response format")
                    
                    available_systems = []
                    for item in contents:
                        if isinstance(item, dict) and item.get('type') == 'dir' and item.get('name') in system_types:
                            available_systems.append({
                                'key': item['name'],
                                'name': system_types[item['name']]
                            })
                    
                    return jsonify({
                        'success': True,
                        'system_types': available_systems
                    })
                except (ValueError, KeyError, TypeError):
                    # Fall through to default system types
                    pass
                except Exception:
                    # Fall through to default system types
                    pass
            else:
                # Fall through to default system types
                pass
        except requests.exceptions.RequestException:
            # Fall through to default system types
            pass
        except Exception:
            # Fall through to default system types
            pass
        
        # Return all system types as a fallback
        default_systems = [{'key': k, 'name': v} for k, v in system_types.items()]
        return jsonify({
            'success': True,
            'system_types': default_systems
        })
    
    except Exception:
        # Return all system types as a fallback
        return jsonify({
            'success': True,
            'system_types': [{'key': k, 'name': v} for k, v in system_types.items()]
        })

@gitee_bp.route('/api/gitee/file-content', methods=['POST'])
def get_file_content():
    """Get file content from Gitee or locally"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    if not data or not data.get('file_path'):
        return jsonify({'error': 'File path required'}), 400
    
    file_path = data['file_path']
    
    try:
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse YAML for structured editing
        try:
            yaml_data = yaml.safe_load(content)
            return jsonify({
                'success': True,
                'content': content,
                'parsed': True,
                'yaml_data': yaml_data
            })
        except Exception as e:
            # Return raw content if parsing fails
            return jsonify({
                'success': True,
                'content': content,
                'parsed': False,
                'error': str(e)
            })
    
    except Exception as e:
        return jsonify({'error': f'Error reading file: {str(e)}'}), 500

@gitee_bp.route('/api/gitee/update-file', methods=['POST'])
def update_file_content():
    """Update file content"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    if not data or not data.get('file_path') or not data.get('content'):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    file_path = data['file_path']
    content = data['content']
    
    try:
        # Write file content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            'success': True,
            'message': 'File updated successfully'
        })
    
    except Exception as e:
        return jsonify({'error': f'Error updating file: {str(e)}'}), 500

@gitee_bp.route('/api/local/files', methods=['GET'])
def get_local_files():
    """Get local docker-compose files"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Check all system directories
        all_files = []
        for system_type in system_types.keys():
            # Check system directory
            system_dir = os.path.join('/app/data', system_type)
            if os.path.exists(system_dir):
                for filename in os.listdir(system_dir):
                    if filename.endswith('.yml') or filename.endswith('.yaml'):
                        file_path = os.path.join(system_dir, filename)
                        stat = os.stat(file_path)
                        all_files.append({
                            'filename': filename,
                            'system_type': system_type,
                            'system_name': system_types[system_type],
                            'file_path': file_path,
                            'size': stat.st_size,
                            'mtime': stat.st_mtime,
                            'source': 'gitee'
                        })
        
        # Check local directory
        local_dir = os.path.join('/app/data', 'local')
        if os.path.exists(local_dir):
            for filename in os.listdir(local_dir):
                if filename.endswith('.yml') or filename.endswith('.yaml'):
                    file_path = os.path.join(local_dir, filename)
                    stat = os.stat(file_path)
                    all_files.append({
                        'filename': filename,
                        'system_type': 'local',
                        'system_name': '本地文件',
                        'file_path': file_path,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime,
                        'source': 'local'
                    })
        
        # Sort by modification time (newest first)
        all_files.sort(key=lambda x: x['mtime'], reverse=True)
        
        return jsonify({
            'success': True,
            'files': all_files,
            'total': len(all_files)
        })
    
    except Exception as e:
        return jsonify({'error': f'Error fetching local files: {str(e)}'}), 500

@gitee_bp.route('/api/local/upload', methods=['POST'])
def upload_local_file():
    """Upload a local docker-compose file"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '' or not (file.filename.endswith('.yml') or file.filename.endswith('.yaml')):
        return jsonify({'error': 'Invalid file format. Please upload a .yml or .yaml file'}), 400
    
    try:
        # Create local directory if not exists
        local_dir = os.path.join('/app/data', 'local')
        os.makedirs(local_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(local_dir, file.filename)
        file.save(file_path)
        
        # Update database
        existing_file = DockerComposeFile.query.filter_by(
            filename=file.filename,
            system_type='local',
            source='local'
        ).first()
        
        if existing_file:
            existing_file.file_path = file_path
            db.session.commit()
        else:
            new_file = DockerComposeFile(
                filename=file.filename,
                system_type='local',
                source='local',
                file_path=file_path
            )
            db.session.add(new_file)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file_path': file_path
        })
    
    except Exception as e:
        return jsonify({'error': f'Error uploading file: {str(e)}'}), 500