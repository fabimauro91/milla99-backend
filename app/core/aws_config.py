import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class AWSConfig:
    """AWS Configuration and client management"""

    def __init__(self):
        self.region_name = settings.AWS_REGION
        self.access_key_id = settings.AWS_ACCESS_KEY_ID
        self.secret_access_key = settings.AWS_SECRET_ACCESS_KEY
        self.rekognition_collection_id = settings.AWS_REKOGNITION_COLLECTION_ID

        # Initialize clients as None
        self._rekognition_client = None
        self._textract_client = None
        self._s3_client = None

    def _get_session(self):
        """Create AWS session with credentials"""
        if not self.access_key_id or not self.secret_access_key:
            raise ValueError(
                "AWS credentials not found in environment variables")

        return boto3.Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region_name
        )

    @property
    def rekognition_client(self):
        """Get or create Rekognition client"""
        if self._rekognition_client is None:
            try:
                session = self._get_session()
                self._rekognition_client = session.client('rekognition')
                logger.info("Rekognition client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Rekognition client: {e}")
                raise
        return self._rekognition_client

    @property
    def textract_client(self):
        """Get or create Textract client"""
        if self._textract_client is None:
            try:
                session = self._get_session()
                self._textract_client = session.client('textract')
                logger.info("Textract client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Textract client: {e}")
                raise
        return self._textract_client

    @property
    def s3_client(self):
        """Get or create S3 client"""
        if self._s3_client is None:
            try:
                session = self._get_session()
                self._s3_client = session.client('s3')
                logger.info("S3 client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                raise
        return self._s3_client

    def test_connection(self) -> bool:
        """Test AWS connection by making a simple API call"""
        try:
            # Test with a simple Rekognition call
            response = self.rekognition_client.list_collections(MaxResults=1)
            logger.info("AWS connection test successful")
            return True
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"AWS connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during AWS connection test: {e}")
            return False


# Global instance
aws_config = AWSConfig()
