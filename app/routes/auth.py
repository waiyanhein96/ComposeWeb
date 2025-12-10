from flask import Blueprint, request, jsonify, session, redirect, url_for
from app import db
from app.models.user import User
import bcrypt
from datetime import datetime
import jwt
import os

# Create blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.json
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    if not user:
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Check password
    if not bcrypt.checkpw(data['password'].encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Create session
    session['user_id'] = user.id
    session['username'] = user.username
    session['is_admin'] = user.is_admin
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user': {
            'username': user.username,
            'is_admin': user.is_admin
        }
    }), 200

@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

@auth_bp.route('/api/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'username': session.get('username'),
                'is_admin': session.get('is_admin')
            }
        }), 200
    return jsonify({'authenticated': False}), 401

@auth_bp.route('/api/change-password', methods=['POST'])
def change_password():
    """Change admin password"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    if not data or not data.get('old_password') or not data.get('new_password'):
        return jsonify({'error': 'All fields required'}), 400
    
    user = User.query.get(session['user_id'])
    
    # Check old password
    if not bcrypt.checkpw(data['old_password'].encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({'error': 'Old password is incorrect'}), 400
    
    # Update password
    hashed_password = bcrypt.hashpw(data['new_password'].encode('utf-8'), bcrypt.gensalt())
    user.password = hashed_password.decode('utf-8')
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Password changed successfully'}), 200