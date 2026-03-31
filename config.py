"""
Configuration Management Module
Handles all application settings with support for environment variables
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AppConfig:
    """Application configuration with environment variable support"""
    
    # Server settings
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'production')
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'change-me-in-production-12345')
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '5000'))
    
    # Download settings
    OUTPUT_DIR: str = os.getenv('OUTPUT_DIR', './downloads')
    MAX_QUEUE_SIZE: int = int(os.getenv('MAX_QUEUE_SIZE', '100'))
    MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', '1'))
    
    # Performance settings
    CHUNK_SIZE: int = int(os.getenv('CHUNK_SIZE', '8192'))
    SOCKET_TIMEOUT: int = int(os.getenv('SOCKET_TIMEOUT', '30'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    CONNECTION_POOL_SIZE: int = int(os.getenv('CONNECTION_POOL_SIZE', '4'))
    
    # Feature flags
    ENABLE_ACCELERATION: bool = os.getenv('ENABLE_ACCELERATION', 'True').lower() == 'true'
    ENABLE_HISTORY: bool = os.getenv('ENABLE_HISTORY', 'True').lower() == 'true'
    ENABLE_CONCURRENT_DOWNLOADS: bool = os.getenv('ENABLE_CONCURRENT_DOWNLOADS', 'False').lower() == 'true'
    
    # Validation settings
    MIN_FILE_SIZE: int = 1024  # 1 KB
    MAX_FILE_SIZE: int = 50 * 1024 * 1024 * 1024  # 50 GB
    ALLOWED_PROTOCOLS: list = ['http', 'https', 'ftp']
    
    # UI settings
    THEME: str = os.getenv('THEME', 'dark')
    ITEMS_PER_PAGE: int = int(os.getenv('ITEMS_PER_PAGE', '20'))
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', './downloads.log')
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Load configuration from environment variables"""
        return cls()
    
    def validate(self) -> bool:
        """Validate configuration values"""
        if self.MAX_QUEUE_SIZE < 1:
            raise ValueError("MAX_QUEUE_SIZE must be >= 1")
        if self.MAX_CONCURRENT_DOWNLOADS < 1:
            raise ValueError("MAX_CONCURRENT_DOWNLOADS must be >= 1")
        if self.SOCKET_TIMEOUT < 5:
            raise ValueError("SOCKET_TIMEOUT must be >= 5")
        if self.PORT < 1 or self.PORT > 65535:
            raise ValueError("PORT must be between 1 and 65535")
        return True


# Global config instance
config = AppConfig.from_env()
