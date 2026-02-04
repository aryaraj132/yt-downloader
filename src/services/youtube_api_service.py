"""YouTube Data API service for accessing live chat and stream data using OAuth."""
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List

logger = logging.getLogger(__name__)


class YouTubeAPIService:
    """Service for interacting with YouTube Data API v3 using OAuth tokens or API Key."""
    
    API_BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    @staticmethod
    def get_chat_message_by_id(
        chat_id: str,
        access_token: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get chat message details by message ID using YouTube Data API.
        
        Args:
            chat_id: YouTube chat message ID
            access_token: User's OAuth access token (optional if api_key provided)
            api_key: YouTube API Key (optional)
            
        Returns:
            Dictionary with message details or None
        """
        try:
            # YouTube API endpoint for liveChatMessages
            url = f"{YouTubeAPIService.API_BASE_URL}/liveChat/messages"
            
            params = {
                'part': 'id,snippet,authorDetails',
                'id': chat_id
            }
            
            headers = {}
            if api_key:
                params['key'] = api_key
            elif access_token:
                headers['Authorization'] = f'Bearer {access_token}'
            else:
                logger.error("No authentication provided (api_key or access_token required)")
                return None
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            
            if not data.get('items'):
                logger.warning(f"Chat message not found: {chat_id}")
                return None
            
            message = data['items'][0]
            
            # Extract message details
            snippet = message.get('snippet', {})
            author_details = message.get('authorDetails', {})
            
            # Parse published timestamp
            published_at_str = snippet.get('publishedAt')
            published_at = None
            if published_at_str:
                try:
                    published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                except ValueError as e:
                    logger.error(f"Failed to parse timestamp: {e}")
            
            return {
                'id': message.get('id'),
                'message_text': snippet.get('displayMessage', ''),
                'author_display_name': author_details.get('displayName', 'Unknown'),
                'author_channel_id': author_details.get('channelId', ''),
                'published_at': published_at,
                'live_chat_id': snippet.get('liveChatId', '')
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch chat message {chat_id}: {str(e)}")
            return None
    
    @staticmethod
    def get_video_id_from_live_chat(
        live_chat_id: str,
        access_token: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Optional[str]:
        """
        Get video ID from live chat ID.
        
        Args:
            live_chat_id: YouTube live chat ID
            access_token: User's OAuth access token (optional)
            api_key: YouTube API Key (optional)
            
        Returns:
            Video ID as string, or None if not found
        """
        try:
            headers = {}
            auth_params = {}
            
            if api_key:
                auth_params['key'] = api_key
            elif access_token:
                headers['Authorization'] = f'Bearer {access_token}'
            else:
                logger.error("No authentication provided")
                return None

            # Search for the video using liveBroadcasts endpoint
            url = f"{YouTubeAPIService.API_BASE_URL}/liveBroadcasts"
            
            params = {
                'part': 'id,snippet',
                'id': live_chat_id,
                'maxResults': 1,
                **auth_params
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            # If liveBroadcasts doesn't work, try searching through videos
            if response.status_code != 200 or not response.json().get('items'):
                # Alternative: search through active live streams
                url = f"{YouTubeAPIService.API_BASE_URL}/search"
                params = {
                    'part': 'id',
                    'eventType': 'live',
                    'type': 'video',
                    'maxResults': 50,
                    **auth_params
                }
                
                response = requests.get(url, params=params, headers=headers)
                
                if response.status_code != 200:
                    logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                    return None
                
                data = response.json()
                
                # Check each live video for matching liveChatId
                for item in data.get('items', []):
                    video_id = item['id'].get('videoId')
                    if not video_id:
                        continue
                    
                    # Get full details for this video
                    video_url = f"{YouTubeAPIService.API_BASE_URL}/videos"
                    video_params = {
                        'part': 'liveStreamingDetails',
                        'id': video_id
                    }
                    
                    video_response = requests.get(video_url, params=video_params, headers=headers)
                    
                    if video_response.status_code == 200:
                        video_data = video_response.json()
                        items = video_data.get('items', [])
                        
                        if items:
                            video_live_chat_id = items[0].get('liveStreamingDetails', {}).get('activeLiveChatId')
                            if video_live_chat_id == live_chat_id:
                                logger.info(f"Found video {video_id} for live chat {live_chat_id}")
                                return video_id
                
                logger.warning(f"No video found for live chat ID: {live_chat_id}")
                return None
            
            data = response.json()
            items = data.get('items', [])
            
            if items:
                # Get the video ID from the broadcast
                return items[0].get('id')
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get video ID from live chat: {str(e)}")
            return None
    
    @staticmethod
    def get_chat_message(chat_id: str, access_token: str) -> Optional[Dict]:
        """
        Fetch chat message details from YouTube API.
        
        Note: YouTube Data API doesn't support fetching a single chat message by ID directly.
        This method attempts to retrieve recent chat messages and find the matching one.
        
        Args:
            chat_id: YouTube chat message ID
            access_token: OAuth access token with youtube.force-ssl scope
            
        Returns:
            Dict containing chat message details or None if not found
            {
                'id': str,
                'author_channel_id': str,
                'author_display_name': str,  
                'message_text': str,
                'published_at': datetime,
                'video_id': str
            }
        """
        try:
            # Unfortunately, YouTube API doesn't provide a direct endpoint to fetch a message by ID
            # The chat_id would need to come from live streaming context
            # For now, we'll return a mock implementation framework
            
            # In real implementation, you would:
            # 1. First get the live chat ID for the video
            # 2. List messages from that chat
            # 3. Find the specific message by ID
            
            logger.warning("get_chat_message is a simplified implementation - see comments for full flow")
            
            # Placeholder return - this would be populated from actual API call
            return None
            
        except Exception as e:
            logger.error(f"Failed to get chat message: {str(e)}")
            return None
    
    @staticmethod
    def get_chat_messages_for_stream(video_id: str, access_token: str, max_results: int = 200) -> Optional[List[Dict]]:
        """
        Get live chat messages for a video/stream.
        
        Args:
            video_id: YouTube video ID
            access_token: OAuth access token
            max_results: Maximum messages to retrieve
            
        Returns:
            List of chat message dicts or None
        """
        try:
            # First, get the live chat ID for the video
            live_chat_id = YouTubeAPIService.get_live_chat_id(video_id, access_token)
            
            if not live_chat_id:
                logger.error(f"No live chat ID found for video {video_id}")
                return None
            
            # Fetch chat messages
            url = f"{YouTubeAPIService.API_BASE_URL}/liveChat/messages"
            params = {
                'liveChatId': live_chat_id,
                'part': 'id,snippet,authorDetails',
                'maxResults': max_results
            }
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            messages = []
            
            for item in data.get('items', []):
                messages.append({
                    'id': item['id'],
                    'author_channel_id': item['authorDetails']['channelId'],
                    'author_display_name': item['authorDetails']['displayName'],
                    'message_text': item['snippet']['displayMessage'],
                    'published_at': datetime.fromisoformat(item['snippet']['publishedAt'].replace('Z', '+00:00')),
                    'video_id': video_id
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get chat messages: {str(e)}")
            return None
    
    @staticmethod
    def get_live_chat_id(video_id: str, access_token: str) -> Optional[str]:
        """
        Get the live chat ID for a video.
        
        Args:
            video_id: YouTube video ID
            access_token: OAuth access token
            
        Returns:
            Live chat ID or None
        """
        try:
            url = f"{YouTubeAPIService.API_BASE_URL}/videos"
            params = {
                'id': video_id,
                'part': 'liveStreamingDetails'
            }
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                logger.error(f"No video found with ID {video_id}")
                return None
            
            live_chat_id = items[0].get('liveStreamingDetails', {}).get('activeLiveChatId')
            return live_chat_id
            
        except Exception as e:
            logger.error(f"Failed to get live chat ID: {str(e)}")
            return None
    
    @staticmethod
    def get_video_stream_details(
        video_id: str, 
        access_token: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get livestream details including start time for a video.
        
        Args:
            video_id: YouTube video ID
            access_token: OAuth access token (optional)
            api_key: YouTube API Key (optional)
            
        Returns:
            Dict containing stream details or None
        """
        try:
            url = f"{YouTubeAPIService.API_BASE_URL}/videos"
            
            params = {
                'id': video_id,
                'part': 'snippet,liveStreamingDetails,status'
            }
            
            headers = {}
            if api_key:
                params['key'] = api_key
            elif access_token:
                headers['Authorization'] = f'Bearer {access_token}'
            else:
                logger.error("No authentication provided")
                return None
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                logger.error(f"No video found with ID {video_id}")
                return None
            
            video = items[0]
            snippet = video.get('snippet', {})
            live_details = video.get('liveStreamingDetails', {})
            
            actual_start = live_details.get('actualStartTime')
            actual_end = live_details.get('actualEndTime')
            scheduled_start = live_details.get('scheduledStartTime')
            
            return {
                'video_id': video_id,
                'title': snippet.get('title'),
                'actual_start_time': datetime.fromisoformat(actual_start.replace('Z', '+00:00')) if actual_start else None,
                'actual_end_time': datetime.fromisoformat(actual_end.replace('Z', '+00:00')) if actual_end else None,
                'scheduled_start_time': datetime.fromisoformat(scheduled_start.replace('Z', '+00:00')) if scheduled_start else None,
                'is_live': actual_start and not actual_end
            }
            
        except Exception as e:
            logger.error(f"Failed to get video stream details: {str(e)}")
            return None
    
    @staticmethod
    def calculate_clip_time(stream_start: datetime, chat_time: datetime, offset: int, duration: int) -> Tuple[int, int]:
        """
        Calculate clip start and end times in seconds from video start.
        
        Args:
            stream_start: When the livestream started
            chat_time: When the chat message was sent
            offset: Seconds to capture before the chat message (e.g., 30 = clip starts 30s before chat)
            duration: Total clip duration in seconds
            
        Returns:
            Tuple of (start_time_seconds, end_time_seconds)
        """
        try:
            # Calculate seconds from stream start to chat message
            time_diff = (chat_time - stream_start).total_seconds()
            
            # Calculate clip start time (offset seconds before the chat)
            clip_start = max(0, time_diff - offset)
            
            # Calculate clip end time
            clip_end = clip_start + duration
            
            return int(clip_start), int(clip_end)
            
        except Exception as e:
            logger.error(f"Failed to calculate clip time: {str(e)}")
            return 0, duration
    
    @staticmethod
    def is_user_channel(author_channel_id: str, access_token: str) -> bool:
        """
        Check if the chat author is the authenticated user.
        
        Args:
            author_channel_id: Channel ID of the chat message author
            access_token: OAuth access token
            
        Returns:
            True if the author is the authenticated user, False otherwise
        """
        try:
            # Get the authenticated user's channel
            url = f"{YouTubeAPIService.API_BASE_URL}/channels"
            params = {
                'part': 'id',
                'mine': 'true'
            }
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                return False
            
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                return False
            
            user_channel_id = items[0]['id']
            return user_channel_id == author_channel_id
            
        except Exception as e:
            logger.error(f"Failed to check user channel: {str(e)}")
            return False
    
    @staticmethod
    def find_chat_message_by_text(video_id: str, message_text: str, access_token: str, time_window_minutes: int = 5) -> Optional[Dict]:
        """
        Find a recent chat message by its text content.
        Useful for finding a message when we only have the message content.
        
        Args:
            video_id: YouTube video ID
            message_text: The text to search for
            access_token: OAuth access token
            time_window_minutes: How far back to search (default 5 minutes)
            
        Returns:
            Chat message dict or None
        """
        try:
            messages = YouTubeAPIService.get_chat_messages_for_stream(video_id, access_token, max_results=200)
            
            if not messages:
                return None
            
            # Filter messages by time window and text match
            cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
            
            for msg in messages:
                if msg['published_at'] >= cutoff_time and message_text in msg['message_text']:
                    return msg
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find chat message by text: {str(e)}")
            return None
