"""ntfy.sh notification client with retry logic.

Implements the ntfy.sh HTTP API contract as defined in contracts/ntfy-api.md.
Includes exponential backoff for rate limits and transient errors.
"""

import requests
import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class NtfyClient:
    """Client for sending notifications via ntfy.sh with error handling and retry logic."""

    def __init__(self, base_url: str = "https://ntfy.sh", max_retries: int = 3):
        """Initialize the ntfy client.

        Args:
            base_url: Base URL for ntfy server (default: https://ntfy.sh)
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.session = requests.Session()

    def send_notification(
        self,
        topic: str,
        message: str,
        title: Optional[str] = None,
        priority: int = 3,
        tags: Optional[str] = None,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """Send a notification to an ntfy topic with retry logic.

        Args:
            topic: Topic name (acts as channel/password for public topics)
            message: The notification message body
            title: Optional notification title
            priority: Priority level 1-5 (1=min, 3=default, 5=urgent)
            tags: Comma-separated emoji tags (e.g., 'droplet,warning')
            timeout: Request timeout in seconds

        Returns:
            Dict with 'success' boolean, 'status_code', and optional 'error' message
        """
        # Validate priority
        if not 1 <= priority <= 5:
            return {
                'success': False,
                'status_code': None,
                'error': f'Invalid priority {priority}. Must be 1-5.'
            }

        # Build headers
        headers = {
            'Priority': str(priority),
        }

        if title:
            headers['Title'] = title

        if tags:
            headers['Tags'] = tags

        # Prepare request
        url = f"{self.base_url}/{topic}"
        data = message.encode('utf-8')

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    url,
                    data=data,
                    headers=headers,
                    timeout=timeout
                )

                # Check response status
                if response.status_code == 200:
                    return {
                        'success': True,
                        'status_code': 200,
                        'message': 'Notification sent successfully'
                    }
                elif response.status_code == 400:
                    # Bad request - don't retry
                    return {
                        'success': False,
                        'status_code': 400,
                        'error': f'Bad request: {response.text}'
                    }
                elif response.status_code == 401:
                    # Unauthorized - don't retry
                    return {
                        'success': False,
                        'status_code': 401,
                        'error': 'Authentication failed. Check credentials.'
                    }
                elif response.status_code == 404:
                    # Not found - don't retry
                    return {
                        'success': False,
                        'status_code': 404,
                        'error': f'Topic not found: {topic}'
                    }
                elif response.status_code == 429:
                    # Rate limited - retry with longer backoff
                    wait_time = min(5 * (2 ** attempt), 60)  # 5s, 10s, 20s, max 60s
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                    if attempt < self.max_retries - 1:
                        time.sleep(wait_time)
                        continue
                    return {
                        'success': False,
                        'status_code': 429,
                        'error': 'Rate limit exceeded. Maximum retries reached.'
                    }
                elif response.status_code == 507:
                    # Insufficient storage (UnifiedPush-specific)
                    return {
                        'success': False,
                        'status_code': 507,
                        'error': 'Insufficient storage or topic not subscribed (UnifiedPush)'
                    }
                elif response.status_code >= 500:
                    # Server error - retry with standard backoff
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(f"Server error {response.status_code}. Retrying in {wait_time}s... ({attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        time.sleep(wait_time)
                        continue
                    return {
                        'success': False,
                        'status_code': response.status_code,
                        'error': f'Server error after {self.max_retries} attempts: {response.text}'
                    }
                else:
                    # Unexpected status code
                    return {
                        'success': False,
                        'status_code': response.status_code,
                        'error': f'Unexpected response: {response.text}'
                    }

            except requests.exceptions.Timeout:
                last_error = 'Request timeout'
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Timeout. Retrying in {wait_time}s... ({attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue

            except requests.exceptions.ConnectionError:
                last_error = 'Connection error'
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Connection error. Retrying in {wait_time}s... ({attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue

            except requests.exceptions.RequestException as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed: {e}. Retrying in {wait_time}s... ({attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue

        # All retries exhausted
        return {
            'success': False,
            'status_code': None,
            'error': f'Failed after {self.max_retries} attempts. Last error: {last_error}'
        }
