"""Authentication routes for user management."""
import logging
from flask import Blueprint, request, jsonify, g

from src.models.user import User
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
        return jsonify({
            'error': 'Email/password login is deprecated. Please use Google OAuth.',
            'oauth_url': '/api/auth/google/login'
        }), 410  # 410 Gone - resource no longer available
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/logout', methods=['POST'])
@require_private_token
def logout():
    """
    Logout endpoint.
    With OAuth, the frontend just needs to clear the token.
    
    Returns:
        {
            "message": "Logout successful"
        }
    """
    try:
        logger.info(f"User logged out: {g.user['email']}")
        return jsonify({'message': 'Logout successful'}), 200
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/change-password', methods=['POST'])
@require_private_token
def change_password():
    """
    DEPRECATED: Not applicable for OAuth users.
    Password changes should be done through Google Account settings.
    """
    try:
        return jsonify({
            'error': 'Password change not supported for OAuth users. Manage your password in your Google Account.',
            'google_account_url': 'https://myaccount.google.com/security'
        }), 410  # 410 Gone
        
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/token/public', methods=['POST'])
@require_private_token
def create_public_token():
    """
    Generate a new public API token for the authenticated user.
    Overwrites any existing public token.
    
    Returns:
        {
            "message": "Token created successfully",
            "token": "..."
        }
    """
    try:
        user_id = g.user_id
        
        token = User.generate_public_token(user_id)
        
        if not token:
            return jsonify({'error': 'Failed to create token'}), 500
        
        logger.info(f"Public token created for user {user_id}")
        
        return jsonify({
            'message': 'Token created successfully',
            'token': token
        }), 201
        
    except Exception as e:
        logger.error(f"Create public token error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/token/public', methods=['GET'])
@require_private_token
def get_public_token():
    """
    Get the current public token for the authenticated user.
    
    Returns:
        {
            "token": "..." or null
        }
    """
    try:
        user_id = g.user_id
        user = User.find_by_id(user_id)
        
        return jsonify({
            'token': user.get('public_token')
        }), 200
        
    except Exception as e:
        logger.error(f"Get public token error: {str(e)}")
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

# Token Refresh

@auth_bp.route('/refresh-token', methods=['POST'])
@require_private_token
def refresh_token():
    """
    Manually refresh Google OAuth access token.
    Requires authentication token in header.
    
    Returns:
        {
            "message": "Token refreshed successfully",
            "access_token": "..."
        }
    """
    try:
        user_id = g.user_id
        
        # Attempt to refresh token
        success, new_access_token = User.refresh_google_token(user_id)
        
        if not success or not new_access_token:
            return jsonify({'error': 'Failed to refresh token'}), 500
        
        return jsonify({
            'message': 'Token refreshed successfully',
            'access_token': new_access_token
        }), 200
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Google OAuth Routes

@auth_bp.route('/google/login', methods=['GET'])
def google_login():
    """
    Initiate Google OAuth login flow.
    """
    from src.config import Config
    
    if not Config.GOOGLE_CLIENT_ID or not Config.GOOGLE_REDIRECT_URI:
        return jsonify({'error': 'Google OAuth not configured'}), 500
        
    import urllib.parse
    
    params = {
        'client_id': Config.GOOGLE_CLIENT_ID,
        'redirect_uri': Config.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join([
            'https://www.googleapis.com/auth/youtube.readonly',
            'https://www.googleapis.com/auth/youtube.force-ssl',
            'https://www.googleapis.com/auth/userinfo.email',
            'openid'
        ]),
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
    Returns the OAuth access token for the frontend to use.
    """
    try:
        from src.config import Config
        
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
        
        # Get user info from Google
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f"Bearer {tokens['access_token']}"}
        )
        
        if user_info_response.status_code != 200:
            return jsonify({'error': 'Failed to get user info'}), 400
            
        user_info = user_info_response.json()
        email = user_info.get('email')
        google_id = user_info.get('id')
        
        if not email or not google_id:
            return jsonify({'error': 'Email or Google ID not provided by Google'}), 400
            
        # Find existing user by Google ID or email
        user = User.find_by_google_id(google_id)
        if not user:
            user = User.find_by_email(email)
        
        user_id = None
        
        if user:
            # Existing user - update OAuth tokens
            user_id = str(user['_id'])
            User.update_google_tokens(user_id, tokens)
            logger.info(f"Existing user logged in via OAuth: {email}")
        else:
            # New user - create with OAuth
            user_id = User.create_oauth_user(email, google_id, tokens)
            if not user_id:
                return jsonify({'error': 'Failed to create user'}), 500
            logger.info(f"New user registered via OAuth: {email}")
        
        # Return the OAuth access token for frontend to use
        return jsonify({
            'message': 'Login successful',
            'token': tokens['access_token'],  # OAuth token, not JWT
            'user': {'email': email, 'id': user_id}
        }), 200

    except Exception as e:
        logger.error(f"Google callback error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
