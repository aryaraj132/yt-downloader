"""Main Flask application."""
import logging
from flask import Flask, jsonify
from flask_cors import CORS

from src.config import Config, setup_logging
from src.routes.auth import auth_bp
from src.routes.video import video_bp
from src.routes.encode import encode_bp

logger = logging.getLogger(__name__)


def create_app():
    """
    Flask application factory.
    
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = Config.FLASK_SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # Max upload size
    
    # CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",  # Configure this for production
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(encode_bp)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'service': 'yt-downloader'
        }), 200
    
    @app.route('/', methods=['GET'])
    def index():
        """Root endpoint."""
        return jsonify({
            'service': 'YouTube Video Downloader API',
            'version': '1.0.0',
            'endpoints': {
                'auth': '/api/auth',
                'video': '/api/video',
                'encode': '/api/encode',
                'health': '/health'
            }
        }), 200
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 errors."""
        return jsonify({'error': 'Bad request'}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 errors."""
        return jsonify({'error': 'Unauthorized'}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 errors."""
        return jsonify({'error': 'Forbidden'}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    logger.info("Flask application created successfully")
    return app
