# Contract: ntfy.sh HTTP API

**Feature**: 001-moisture-monitoring
**Date**: 2026-02-13
**External Service**: ntfy.sh Push Notification API
**API Version**: v1 (RESTful HTTP)

## Overview

This contract defines how the plant monitoring system interacts with the ntfy.sh API to send watering notifications. The contract covers request format, expected responses, error handling, and retry behavior.

## Base URL

```
https://ntfy.sh
```

**Alternative**: Self-hosted ntfy server (configurable via `NTFY_URL` environment variable)

## Authentication

**Public topics**: No authentication required
- Topic name acts as a shared secret/password
- Choose non-guessable topic names (e.g., "mark-test-watering-monitor")

**Protected topics** (future enhancement):
- HTTP Basic Auth: `Authorization: Basic base64(username:password)`
- Bearer token: `Authorization: Bearer <token>`

**MVP Requirement**: No authentication (use default public topic)

---

## API Endpoint: Send Notification

### Request

**Method**: `POST`

**URL**: `https://ntfy.sh/{topic}`

**Headers**:
| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| `Content-Type` | No | string | Defaults to `text/plain` | `text/plain; charset=utf-8` |
| `Title` or `X-Title` | No | string | Notification title | `Plant Alert` |
| `Priority` or `X-Priority` | No | integer | Priority level (1-5) | `4` |
| `Tags` or `X-Tags` | No | string | Comma-separated emoji tags | `droplet,warning` |
| `Click` or `X-Click` | No | URL | URL to open on notification click | `https://example.com` |

**Body**: Plain text message (UTF-8 encoded)

**Example Request**:
```http
POST /mark-test-watering-monitor HTTP/1.1
Host: ntfy.sh
Content-Type: text/plain; charset=utf-8
Title: Plant Alert
Priority: 4
Tags: droplet,warning

Plant-A needs watering (moisture: 35%)
```

**Python Implementation**:
```python
import requests

def send_notification(topic: str, message: str) -> dict:
    """Send notification to ntfy.sh"""
    url = f"https://ntfy.sh/{topic}"
    headers = {
        'Title': 'Plant Alert',
        'Priority': '4',  # High priority
        'Tags': 'droplet,warning'
    }

    try:
        response = requests.post(
            url,
            data=message.encode('utf-8'),
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return {'success': True, 'status_code': 200}
    except requests.RequestException as e:
        return {'success': False, 'error': str(e)}
```

### Successful Response

**Status Code**: `200 OK`

**Headers**:
```
Content-Type: application/json
```

**Body**:
```json
{
  "id": "wze7RzQb4Blv",
  "time": 1675900000,
  "event": "message",
  "topic": "mark-test-watering-monitor",
  "message": "Plant-A needs watering (moisture: 35%)",
  "title": "Plant Alert",
  "priority": 4,
  "tags": ["droplet", "warning"]
}
```

**Contract Guarantee**:
- Response code 200 indicates message was successfully queued for delivery
- Message will be cached for 12 hours for offline subscribers
- No guarantee of immediate delivery (push notification may be delayed)

### Error Responses

#### 400 Bad Request

**Cause**: Invalid request format or parameters

**Example**:
```json
{
  "error": "invalid request: message too long",
  "http": 400
}
```

**Handling**: Log error, **do not retry** (permanent error)

---

#### 401 Unauthorized

**Cause**: Authentication failed (protected topics only)

**Example**:
```json
{
  "error": "unauthorized",
  "http": 401
}
```

**Handling**: Log error, **do not retry** (check credentials)

---

#### 429 Too Many Requests

**Cause**: Rate limit exceeded

**Rate Limits**:
- Burst: 60 requests
- Sustained: 1 request per 5 seconds

**Response**:
```json
{
  "error": "rate limit reached",
  "http": 429
}
```

**Note**: No `Retry-After` header provided

**Handling**: Retry with exponential backoff (5s, 10s, 20s), max 3 retries

---

#### 500 Internal Server Error

**Cause**: Transient server-side failure

**Response**:
```json
{
  "error": "internal server error",
  "http": 500
}
```

**Handling**: Retry with exponential backoff (1s, 2s, 4s), max 3 retries

---

#### 507 Insufficient Storage

**Cause**: Topic not subscribed (UnifiedPush-specific error)

**Response**:
```json
{
  "error": "insufficient storage",
  "http": 507
}
```

**Handling**: Log warning, **do not retry** (user needs to subscribe to topic)

---

## Retry Strategy

**Transient Errors** (retry):
- 429 Too Many Requests → Exponential backoff (5s, 10s, 20s)
- 500 Internal Server Error → Exponential backoff (1s, 2s, 4s)
- 503 Service Unavailable → Exponential backoff (1s, 2s, 4s)
- Network timeout → Exponential backoff (1s, 2s, 4s)
- Connection errors → Exponential backoff (1s, 2s, 4s)

**Permanent Errors** (do not retry):
- 400 Bad Request
- 401 Unauthorized
- 404 Not Found
- 507 Insufficient Storage

**Maximum Retries**: 3 attempts per notification

**Backoff Formula**:
```python
import time

def retry_with_backoff(func, max_retries=3):
    """Retry func with exponential backoff"""
    for attempt in range(max_retries):
        result = func()

        if result['status_code'] == 200:
            return result
        elif result['status_code'] in [400, 401, 404, 507]:
            # Permanent error - don't retry
            return result
        elif result['status_code'] == 429:
            # Rate limit - longer backoff
            wait = min(5 * (2 ** attempt), 60)  # 5s, 10s, 20s, max 60s
            time.sleep(wait)
        else:
            # Server error - standard backoff
            wait = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait)

    return {'success': False, 'error': 'Max retries exceeded'}
```

---

## Message Format Requirements

### Plant Watering Notification

**Spec Requirement** (from clarifications):
```
Title: "Plant Alert"
Body: "{plant_id} needs watering (moisture: {moisture_percent:.0f}%)"
Priority: 4
Tags: droplet,warning
```

**Example Messages**:
```
Plant-A needs watering (moisture: 35%)
Plant-B needs watering (moisture: 38%)
Plant-C needs watering (moisture: 42%)
```

**Validation**:
- Message length: 1-4096 characters
- Moisture value: 0-100 (integer format)
- Plant ID: "Plant-A", "Plant-B", or "Plant-C"

### Priority Levels

| Level | Name | Use Case | Behavior |
|-------|------|----------|----------|
| 1 | min | Low-priority info | Normal notification |
| 2 | low | Routine updates | Normal notification |
| 3 | default | Standard notifications | Normal notification (default) |
| 4 | high | Important alerts | **Used for plant watering alerts** |
| 5 | max/urgent | Critical failures | Breaks through do-not-disturb |

**MVP Uses**: Priority 4 (high) for all watering alerts

---

## Testing Contract

### Mock ntfy.sh API (for integration tests)

```python
from unittest.mock import Mock, patch

def test_send_notification_success():
    """Test successful notification"""
    with patch('requests.post') as mock_post:
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'test123',
            'topic': 'test-topic',
            'message': 'Test message'
        }
        mock_post.return_value = mock_response

        # Send notification
        result = send_notification('test-topic', 'Test message')

        # Assertions
        assert result['success'] is True
        assert result['status_code'] == 200
        mock_post.assert_called_once()

def test_send_notification_rate_limited():
    """Test rate limit handling"""
    with patch('requests.post') as mock_post:
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {'error': 'rate limit reached'}
        mock_post.return_value = mock_response

        # Send notification (should retry)
        result = send_notification('test-topic', 'Test message')

        # Assertions
        assert result['success'] is False
        assert result['status_code'] == 429

def test_send_notification_invalid_request():
    """Test handling of bad request"""
    with patch('requests.post') as mock_post:
        # Mock bad request response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'invalid request'}
        mock_post.return_value = mock_response

        # Send notification (should NOT retry)
        result = send_notification('test-topic', '')

        # Assertions
        assert result['success'] is False
        assert result['status_code'] == 400
```

---

## Contract Guarantees

### What ntfy.sh Guarantees

✅ **Messages delivered to active subscribers** within seconds (typically <1s)
✅ **Messages cached for 12 hours** for offline/new subscribers
✅ **HTTP 200 response** indicates message successfully queued
✅ **Rate limits enforced consistently** (60 burst, 1/5s sustained)

### What ntfy.sh Does NOT Guarantee

❌ **Immediate delivery** (push notifications may be delayed by mobile OS)
❌ **Delivery confirmation** (no webhook/callback when user receives message)
❌ **Message persistence** beyond 12 hours
❌ **Duplicate prevention** (sending same message twice = two notifications)

### System Responsibilities

The plant monitoring system MUST:
1. ✅ Handle rate limits gracefully (retry with backoff)
2. ✅ Prevent duplicate notifications (throttle logic: 6 hours between alerts per plant)
3. ✅ Log all notification attempts (success and failure)
4. ✅ Handle network errors (timeout, connection refused)
5. ✅ Validate message format before sending

---

## Configuration

**Environment Variables**:
```ini
# ntfy.sh API configuration
NTFY_URL=https://ntfy.sh
NTFY_TOPIC=mark-test-watering-monitor
NTFY_TIMEOUT=10  # HTTP request timeout (seconds)
NTFY_MAX_RETRIES=3  # Maximum retry attempts
```

**Example Topic Naming**:
- ❌ Bad: `plants` (too generic, guessable)
- ❌ Bad: `test123` (too simple, guessable)
- ✅ Good: `mark-test-watering-monitor` (specific, harder to guess)
- ✅ Good: `plant-alerts-7f3a92bc` (unique identifier)

---

## Appendix: Full API Reference

For complete ntfy.sh API documentation, see:
- Publishing: https://docs.ntfy.sh/publish/
- Subscribing: https://docs.ntfy.sh/subscribe/api/
- Rate Limits: https://docs.ntfy.sh/faq/#are-there-rate-limits

**Last Verified**: 2026-02-13
