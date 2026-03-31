"""
Input Validation Module
Comprehensive URL and input validation for security
"""

import re
from urllib.parse import urlparse
from typing import Tuple, Optional


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class URLValidator:
    """Validates URLs and prevents common security issues"""
    
    # Supported protocols
    ALLOWED_PROTOCOLS = ['http', 'https']
    
    # Blocked domains (for testing/security)
    BLOCKED_DOMAINS = []
    
    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        r'javascript:',
        r'data:',
        r'file://',
        r'<script',
        r'onclick',
        r'onerror'
    ]
    
    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a URL for security and format
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not url:
            return False, "URL cannot be empty"
        
        url = url.strip()
        
        # Check length
        if len(url) > 2048:
            return False, "URL is too long (max 2048 characters)"
        
        # Check for suspicious patterns
        url_lower = url.lower()
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if pattern in url_lower:
                return False, f"URL contains suspicious pattern: {pattern}"
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"
        
        # Check protocol
        if not parsed.scheme:
            return False, "URL must include protocol (http:// or https://)"
        
        if parsed.scheme.lower() not in cls.ALLOWED_PROTOCOLS:
            return False, f"Protocol '{parsed.scheme}' is not allowed (use http or https)"
        
        # Check hostname
        if not parsed.hostname:
            return False, "URL must include hostname"
        
        # Check for localhost/private IPs (optional - can be configured)
        if cls._is_private_ip(parsed.hostname):
            return False, "Local/private IP addresses are not allowed"
        
        if parsed.hostname in cls.BLOCKED_DOMAINS:
            return False, f"Domain '{parsed.hostname}' is blocked"
        
        return True, None
    
    @staticmethod
    def _is_private_ip(hostname: str) -> bool:
        """Check if hostname is a private IP or localhost"""
        private_patterns = [
            r'^localhost$',
            r'^127\.',
            r'^10\.',
            r'^172\.(1[6-9]|2\d|3[01])\.',
            r'^192\.168\.',
            r'^::1$',
            r'^fe80:',
        ]
        
        for pattern in private_patterns:
            if re.match(pattern, hostname, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def validate_urls_batch(cls, urls: list) -> Tuple[list, list]:
        """
        Validate multiple URLs
        
        Returns:
            Tuple[valid_urls, errors]: List of valid URLs and error messages
        """
        valid_urls = []
        errors = []
        
        for i, url in enumerate(urls, 1):
            is_valid, error_msg = cls.validate_url(url)
            if is_valid:
                valid_urls.append(url)
            else:
                errors.append(f"URL {i}: {error_msg}")
        
        return valid_urls, errors


class FilenameValidator:
    """Validates and sanitizes filenames"""
    
    # Invalid filename characters
    INVALID_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
    
    # Reserved names (Windows)
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    @classmethod
    def sanitize(cls, filename: str, max_length: int = 255) -> str:
        """
        Sanitize filename to be filesystem-safe
        
        Args:
            filename: Original filename
            max_length: Maximum allowed length (default 255)
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return "download"
        
        # Remove invalid characters
        filename = re.sub(cls.INVALID_CHARS, '', filename)
        
        # Replace spaces with underscores
        filename = re.sub(r'\s+', '_', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Check for reserved names
        name_part = filename.split('.')[0].upper()
        if name_part in cls.RESERVED_NAMES:
            filename = f"file_{filename}"
        
        # Truncate to max length (preserving extension)
        if len(filename) > max_length:
            if '.' in filename:
                name, ext = filename.rsplit('.', 1)
                allowed_name_length = max_length - len(ext) - 1
                filename = name[:allowed_name_length] + '.' + ext
            else:
                filename = filename[:max_length]
        
        return filename if filename else "download"
    
    @classmethod
    def validate(cls, filename: str) -> Tuple[bool, Optional[str]]:
        """Validate filename"""
        if not filename:
            return False, "Filename cannot be empty"
        
        if len(filename) > 255:
            return False, "Filename is too long (max 255 characters)"
        
        if re.search(cls.INVALID_CHARS, filename):
            return False, "Filename contains invalid characters"
        
        name_part = filename.split('.')[0].upper()
        if name_part in cls.RESERVED_NAMES:
            return False, f"Filename uses reserved name: {filename.split('.')[0]}"
        
        return True, None


class QueueValidator:
    """Validates queue operations"""
    
    @staticmethod
    def validate_queue_size(current_size: int, max_size: int) -> Tuple[bool, Optional[str]]:
        """Check if queue size is within limits"""
        if current_size >= max_size:
            return False, f"Queue is full (max {max_size} items)"
        return True, None
    
    @staticmethod
    def validate_job_id(job_id: str) -> Tuple[bool, Optional[str]]:
        """Validate job ID format"""
        if not job_id:
            return False, "Job ID cannot be empty"
        
        # UUID format validation (36 chars with hyphens)
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, job_id, re.IGNORECASE):
            return False, "Invalid job ID format"
        
        return True, None


class FormatValidator:
    """Validates format selections"""
    
    VALID_VIDEO_FORMATS = ['mp4', 'webm', 'mkv']
    VALID_AUDIO_FORMATS = ['mp3', 'm4a', 'ogg']
    VALID_VIDEO_QUALITIES = ['best', '1080p', '720p', '480p', '360p']
    VALID_AUDIO_BITRATES = ['320', '192', '128', '96']
    
    @classmethod
    def validate_mode(cls, mode: str) -> Tuple[bool, Optional[str]]:
        """Validate download mode"""
        if mode not in ['video', 'audio']:
            return False, f"Invalid mode: {mode} (must be 'video' or 'audio')"
        return True, None
    
    @classmethod
    def validate_format(cls, mode: str, format_type: str) -> Tuple[bool, Optional[str]]:
        """Validate format for given mode"""
        if mode == 'video':
            if format_type not in cls.VALID_VIDEO_FORMATS:
                return False, f"Invalid video format: {format_type}"
        elif mode == 'audio':
            if format_type not in cls.VALID_AUDIO_FORMATS:
                return False, f"Invalid audio format: {format_type}"
        return True, None
    
    @classmethod
    def validate_quality(cls, mode: str, quality: str) -> Tuple[bool, Optional[str]]:
        """Validate quality for video mode"""
        if mode == 'video':
            if quality not in cls.VALID_VIDEO_QUALITIES:
                return False, f"Invalid quality: {quality}"
        return True, None
    
    @classmethod
    def validate_bitrate(cls, mode: str, bitrate: str) -> Tuple[bool, Optional[str]]:
        """Validate bitrate for audio mode"""
        if mode == 'audio':
            if bitrate not in cls.VALID_AUDIO_BITRATES:
                return False, f"Invalid bitrate: {bitrate}"
        return True, None


def validate_download_request(urls: list, mode: str = 'video', 
                             format_type: str = 'mp4', quality: str = 'best',
                             bitrate: str = '192') -> Tuple[bool, list, list]:
    """
    Comprehensive validation of download request
    
    Returns:
        Tuple[is_valid, valid_urls, errors]
    """
    errors = []
    
    # Validate URLs
    valid_urls, url_errors = URLValidator.validate_urls_batch(urls)
    errors.extend(url_errors)
    
    # Validate mode
    valid, error = FormatValidator.validate_mode(mode)
    if not valid:
        errors.append(error)
        return False, [], errors
    
    # Validate format
    valid, error = FormatValidator.validate_format(mode, format_type)
    if not valid:
        errors.append(error)
    
    # Validate quality
    valid, error = FormatValidator.validate_quality(mode, quality)
    if not valid:
        errors.append(error)
    
    # Validate bitrate
    valid, error = FormatValidator.validate_bitrate(mode, bitrate)
    if not valid:
        errors.append(error)
    
    is_valid = len(valid_urls) > 0 and len(errors) == 0
    
    return is_valid, valid_urls, errors
