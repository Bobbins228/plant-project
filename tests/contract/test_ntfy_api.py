"""Contract tests for ntfy.sh HTTP API.

These tests verify the notifier correctly interacts with the ntfy.sh API
according to the contract defined in contracts/ntfy-api.md.

Per constitution: These tests must be written FIRST and FAIL before implementation.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime


class TestNtfyAPIContract:
    """Test ntfy.sh API contract compliance."""

    def test_successful_notification_returns_200(self):
        """Test successful notification to ntfy.sh returns HTTP 200.

        Contract: POST to https://ntfy.sh/{topic} with message body
        should return 200 OK with JSON response containing message details.
        """
        # This will fail until notifier.py is implemented
        from src.lib.notifier import NtfyClient

        with patch('requests.post') as mock_post:
            # Mock successful response per contract
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'id': 'test123',
                'topic': 'test-topic',
                'message': 'Plant-A needs watering (moisture: 35%)'
            }
            mock_post.return_value = mock_response

            # Send notification
            client = NtfyClient(base_url="https://ntfy.sh")
            result = client.send_notification(
                topic='test-topic',
                message='Plant-A needs watering (moisture: 35%)',
                title='Plant Alert',
                priority=4
            )

            # Verify success
            assert result['success'] is True
            assert result['status_code'] == 200

            # Verify API was called correctly per contract
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == 'https://ntfy.sh/test-topic'
            assert 'Plant-A needs watering' in call_args[1]['data'].decode('utf-8')
            assert call_args[1]['headers']['Priority'] == '4'
            assert call_args[1]['headers']['Title'] == 'Plant Alert'

    def test_rate_limit_429_triggers_retry(self):
        """Test HTTP 429 rate limit response triggers retry with backoff.

        Contract: 429 errors should be retried with exponential backoff.
        """
        from src.lib.notifier import NtfyClient

        with patch('requests.post') as mock_post, \
             patch('time.sleep') as mock_sleep:
            # Mock rate limit response
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.json.return_value = {'error': 'rate limit reached'}
            mock_post.return_value = mock_response

            # Send notification (should retry)
            client = NtfyClient(base_url="https://ntfy.sh", max_retries=3)
            result = client.send_notification(
                topic='test-topic',
                message='Test message'
            )

            # Verify retries occurred
            assert result['success'] is False
            assert result['status_code'] == 429
            assert mock_post.call_count == 3  # Initial + 2 retries
            assert mock_sleep.call_count == 2  # Backoff between retries

    def test_bad_request_400_does_not_retry(self):
        """Test HTTP 400 bad request does not retry.

        Contract: 400 errors are permanent and should not be retried.
        """
        from src.lib.notifier import NtfyClient

        with patch('requests.post') as mock_post:
            # Mock bad request response
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {'error': 'invalid request'}
            mock_post.return_value = mock_response

            # Send notification
            client = NtfyClient(base_url="https://ntfy.sh", max_retries=3)
            result = client.send_notification(
                topic='test-topic',
                message=''  # Invalid: empty message
            )

            # Verify no retries (permanent error)
            assert result['success'] is False
            assert result['status_code'] == 400
            assert mock_post.call_count == 1  # No retries

    def test_server_error_500_retries_with_backoff(self):
        """Test HTTP 500 server error triggers retry.

        Contract: 500 errors are transient and should be retried with
        exponential backoff (1s, 2s, 4s).
        """
        from src.lib.notifier import NtfyClient

        with patch('requests.post') as mock_post, \
             patch('time.sleep') as mock_sleep:
            # Mock server error response
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = 'internal server error'
            mock_post.return_value = mock_response

            # Send notification
            client = NtfyClient(base_url="https://ntfy.sh", max_retries=3)
            result = client.send_notification(
                topic='test-topic',
                message='Test message'
            )

            # Verify exponential backoff
            assert result['success'] is False
            assert mock_post.call_count == 3
            # Check backoff times: 1s, 2s (for first 2 retries)
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert sleep_calls[0] == 1  # 2^0 = 1 second
            assert sleep_calls[1] == 2  # 2^1 = 2 seconds

    def test_network_timeout_retries(self):
        """Test network timeout triggers retry.

        Contract: Timeout errors should be retried.
        """
        from src.lib.notifier import NtfyClient
        import requests

        with patch('requests.post') as mock_post, \
             patch('time.sleep') as mock_sleep:
            # Mock timeout
            mock_post.side_effect = requests.Timeout("Connection timeout")

            # Send notification
            client = NtfyClient(base_url="https://ntfy.sh", max_retries=3)
            result = client.send_notification(
                topic='test-topic',
                message='Test message'
            )

            # Verify retries
            assert result['success'] is False
            assert 'timeout' in result['error'].lower() or 'max retries' in result['error'].lower()
            assert mock_post.call_count == 3

    def test_message_format_includes_plant_and_moisture(self):
        """Test notification message format per clarifications.

        Contract: Message format must be "{plant_id} needs watering (moisture: {percent}%)"
        """
        from src.lib.notifier import NtfyClient

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'id': 'test'}
            mock_post.return_value = mock_response

            client = NtfyClient(base_url="https://ntfy.sh")

            # Test exact message format from spec
            result = client.send_notification(
                topic='test-topic',
                message='Plant-A needs watering (moisture: 35%)'
            )

            # Verify message format
            call_args = mock_post.call_args
            message = call_args[1]['data'].decode('utf-8')
            assert 'Plant-A' in message
            assert 'needs watering' in message
            assert '35%' in message
            assert result['success'] is True
