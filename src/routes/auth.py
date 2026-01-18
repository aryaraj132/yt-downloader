"""Authentication routes for user management."""
import logging
from flask import Blueprint, request, jsonify, g

from src.models.user import User
from src.models.session import Session
from src.utils.token import generate_private_token, generate_public_token
from src.utils.validators import validate_email, validate_password
from src.middleware.auth import require_private_token

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user account.
    
    Request body:
        {
            "email": "user@example.com",
            "password": "password123"
        }
    
    Returns:
        {
            "message": "User registered successfully",
            "user_id": "..."
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        # Validate input
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Validate email format
        is_valid_email, email_error = validate_email(email)
        if not is_valid_email:
            return jsonify({'error': email_error}), 400
        
        # Validate password strength
        is_valid_password, password_error = validate_password(password)
        if not is_valid_password:
            return jsonify({'error': password_error}), 400
        
        # Check if email already exists
        if User.email_exists(email):
            return jsonify({'error': 'Email already registered'}), 409
        
        # Create user
        user_id = User.create_user(email, password)
        
        if not user_id:
            return jsonify({'error': 'Failed to create user'}), 500
        
        logger.info(f"New user registered: {email}")
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login and create a new session.
    
    Request body:
        {
            "email": "user@example.com",
            "password": "password123"
        }
    
    Returns:
        {
            "message": "Login successful",
            "token": "...",
            "user": {...}
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find user by email
        user = User.find_by_email(email)
        
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Verify password
        if not User.verify_password(user, password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        user_id = str(user['_id'])
        
        # Generate private token
        token = generate_private_token(user_id, "temp_session_id")
        
        # Create session
        session_id = Session.create_session(user_id, token)
        
        if not session_id:
            return jsonify({'error': 'Failed to create session'}), 500
        
        # Regenerate token with actual session_id
        token = generate_private_token(user_id, session_id)
        
        # Update session with new token
        from src.services.db_service import get_database
        from bson import ObjectId
        db = get_database()
        db.sessions.update_one(
            {'_id': ObjectId(session_id)},
            {'$set': {'token': token}}
        )
        
        logger.info(f"User logged in: {email}")
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user_id,
                'email': user['email']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/logout', methods=['POST'])
@require_private_token
def logout():
    """
    Logout and invalidate current session.
    Requires authentication token in header.
    
    Returns:
        {
            "message": "Logout successful"
        }
    """
    try:
        # Get token from request
        from src.middleware.auth import get_token_from_request
        token = get_token_from_request()
        
        # Find and delete session
        session = Session.find_by_token(token)
        
        if session:
            session_id = str(session['_id'])
            Session.delete_session(session_id)
            logger.info(f"User logged out: {g.user['email']}")
        
        return jsonify({'message': 'Logout successful'}), 200
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/change-password', methods=['POST'])
@require_private_token
def change_password():
    """
    Change user password.
    Requires authentication token in header.
    
    Request body:
        {
            "current_password": "oldpass123",
            "new_password": "newpass123"
        }
    
    Returns:
        {
            "message": "Password changed successfully"
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new passwords are required'}), 400
        
        # Validate new password
        is_valid, error = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': error}), 400
        
        # Get current user
        user = User.find_by_id(g.user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify current password
        if not User.verify_password(user, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        if not User.update_password(g.user_id, new_password):
            return jsonify({'error': 'Failed to update password'}), 500
        
        # Invalidate all existing sessions for security
        Session.delete_user_sessions(g.user_id)
        
        logger.info(f"Password changed for user: {g.user['email']}")
        
        return jsonify({'message': 'Password changed successfully. Please login again.'}), 200
        
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/token/public', methods=['GET'])
def get_public_token():
    """
    Get a public API token for saving video info.
    This endpoint is public and doesn't require authentication.
    
    Returns:
        {
            "token": "..."
        }
    """
    try:
        token = generate_public_token()
        
        return jsonify({
            'token': token,
            'expires_in': 86400  # 24 hours
        }), 200
        
    except Exception as e:
        logger.error(f"Public token generation error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/me', methods=['GET'])
@require_private_token
def get_current_user():
    """
    Get current user information.
    Requires authentication token in header.
    
    Returns:
        {
            "user": {...}
        }
    """
    return jsonify({'user': g.user}), 200

# Google OAuth Routes

@auth_bp.route('/google/login', methods=['GET'])
def google_login():
    """
    Initiate Google OAuth login flow.
    """
    if not Config.GOOGLE_CLIENT_ID or not Config.GOOGLE_REDIRECT_URI:
        return jsonify({'error': 'Google OAuth not configured'}), 500
        
    import urllib.parse
    
    params = {
        'client_id': Config.GOOGLE_CLIENT_ID,
        'redirect_uri': Config.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/userinfo.email openid',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    
    return jsonify({'auth_url': auth_url}), 200


@auth_bp.route('/google/callback', methods=['GET', 'POST'])
def google_callback():
    """
    Handle Google OAuth callback.
    Exchanges code for tokens and logs in/registers user.
    """
    try:
        # Handle both GET (redirect) and POST (manual code submission)
        if request.method == 'POST':
            data = request.get_json()
            code = data.get('code')
        else:
            code = request.args.get('code')
            
        if not code:
            return jsonify({'error': 'Authorization code is required'}), 400
            
        if not Config.GOOGLE_CLIENT_ID or not Config.GOOGLE_CLIENT_SECRET or not Config.GOOGLE_REDIRECT_URI:
            return jsonify({'error': 'Google OAuth not configured'}), 500
            
        # Exchange code for tokens
        import requests
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'code': code,
            'client_id': Config.GOOGLE_CLIENT_ID,
            'client_secret': Config.GOOGLE_CLIENT_SECRET,
            'redirect_uri': Config.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, data=token_data)
        
        if response.status_code != 200:
            logger.error(f"Failed to exchange token: {response.text}")
            return jsonify({'error': 'Failed to exchange authorization code'}), 400
            
        tokens = response.json()
        
        # Get user info
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f"Bearer {tokens['access_token']}"}
        )
        
        if user_info_response.status_code != 200:
            return jsonify({'error': 'Failed to get user info'}), 400
            
        user_info = user_info_response.json()
        email = user_info.get('email')
        
        if not email:
            return jsonify({'error': 'Email not provided by Google'}), 400
            
        # Find or create user
        user = User.find_by_email(email)
        user_id = None
        
        if user:
            user_id = str(user['_id'])
            # Update tokens
            User.update_google_tokens(user_id, tokens)
        else:
            # Create new user with random password (they can reset it later or use google login)
            import uuid
            random_password = str(uuid.uuid4())
            user_id = User.create_user(email, random_password)
            if user_id:
                User.update_google_tokens(user_id, tokens)
        
        if not user_id:
            return jsonify({'error': 'Failed to create/update user'}), 500
            
        # Create session
        # Generate private token
        from src.models.session import Session
        token = generate_private_token(user_id, "temp_session_id")
        session_id = Session.create_session(user_id, token)
        
        # Regenerate token with actual session_id
        token = generate_private_token(user_id, session_id)
        
        # Update session with new token
        from src.services.db_service import get_database
        from bson import ObjectId
        db = get_database()
        db.sessions.update_one(
            {'_id': ObjectId(session_id)},
            {'$set': {'token': token}}
        )
        
        return jsonify({
            'message': 'Login successful',
            'token': token, 
            'user': {'email': email, 'id': user_id}
        }), 200

    except Exception as e:
        logger.error(f"Google callback error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
