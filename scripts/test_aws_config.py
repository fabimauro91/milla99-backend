#!/usr/bin/env python3
"""
Test script for AWS configuration and document verification service
"""

from app.services.document_verification_service import DocumentVerificationService
from app.core.aws_config import aws_config
import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_aws_connection():
    """Test AWS connection"""
    print("🔍 Testing AWS connection...")

    try:
        # Test connection
        success = aws_config.test_connection()

        if success:
            print("✅ AWS connection successful!")
            return True
        else:
            print("❌ AWS connection failed!")
            return False

    except Exception as e:
        print(f"❌ Error testing AWS connection: {e}")
        return False


def test_document_verification_service():
    """Test document verification service"""
    print("\n🔍 Testing document verification service...")

    try:
        service = DocumentVerificationService()
        print("✅ Document verification service initialized successfully!")
        return True

    except Exception as e:
        print(f"❌ Error initializing document verification service: {e}")
        return False


def test_environment_variables():
    """Test if required environment variables are set"""
    print("\n🔍 Checking environment variables...")

    required_vars = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_REGION'
    ]

    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var} is set")

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your environment or .env file")
        return False
    else:
        print("✅ All required environment variables are set!")
        return True


def main():
    """Main test function"""
    print("🚀 Starting AWS configuration tests...\n")

    # Test environment variables
    env_ok = test_environment_variables()

    if not env_ok:
        print(
            "\n❌ Environment variables test failed. Please configure your AWS credentials.")
        return

    # Test AWS connection
    aws_ok = test_aws_connection()

    if not aws_ok:
        print("\n❌ AWS connection test failed. Please check your credentials and network connection.")
        return

    # Test document verification service
    service_ok = test_document_verification_service()

    if not service_ok:
        print("\n❌ Document verification service test failed.")
        return

    print("\n🎉 All tests passed! AWS configuration is working correctly.")
    print("\nNext steps:")
    print("1. Install the new dependencies: pip install -r requirements.txt")
    print("2. Configure your AWS credentials in env.docker")
    print("3. Test the document verification endpoints")


if __name__ == "__main__":
    main()
