#!/usr/bin/env python3
"""
Simple test script for AWS configuration
"""
import logging
import sys
import os
from dotenv import load_dotenv
load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_environment_variables():
    """Test if required environment variables are set"""
    print("🔍 Checking environment variables...")

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


def test_aws_import():
    """Test if AWS modules can be imported"""
    print("\n🔍 Testing AWS module imports...")

    try:
        import boto3
        print("✅ boto3 imported successfully")

        from botocore.exceptions import ClientError, NoCredentialsError
        print("✅ botocore exceptions imported successfully")

        return True

    except ImportError as e:
        print(f"❌ Error importing AWS modules: {e}")
        return False


def test_opencv_import():
    """Test if OpenCV can be imported"""
    print("\n🔍 Testing OpenCV import...")

    try:
        import cv2
        print("✅ OpenCV imported successfully")

        # Test if face detection cascade is available
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        print(f"✅ Face detection cascade path: {cascade_path}")

        return True

    except ImportError as e:
        print(f"❌ Error importing OpenCV: {e}")
        return False


def test_pillow_import():
    """Test if Pillow can be imported"""
    print("\n🔍 Testing Pillow import...")

    try:
        from PIL import Image, ImageDraw
        print("✅ Pillow imported successfully")
        return True

    except ImportError as e:
        print(f"❌ Error importing Pillow: {e}")
        return False


def main():
    """Main test function"""
    print("🚀 Starting simple AWS configuration tests...\n")

    # Test environment variables
    env_ok = test_environment_variables()

    # Test AWS imports
    aws_ok = test_aws_import()

    # Test OpenCV imports
    opencv_ok = test_opencv_import()

    # Test Pillow imports
    pillow_ok = test_pillow_import()

    # Summary
    print("\n📋 Test Summary:")
    print(f"   Environment Variables: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"   AWS Modules: {'✅ PASS' if aws_ok else '❌ FAIL'}")
    print(f"   OpenCV: {'✅ PASS' if opencv_ok else '❌ FAIL'}")
    print(f"   Pillow: {'✅ PASS' if pillow_ok else '❌ FAIL'}")

    if env_ok and aws_ok and opencv_ok and pillow_ok:
        print("\n🎉 All basic tests passed! Dependencies are installed correctly.")
        print("\nNext steps:")
        print("1. Configure your AWS credentials in env.docker")
        print("2. Test with real document images")
        print("3. Integrate with the API endpoints")
    else:
        print("\n⚠️ Some tests failed. Please check the configuration and try again.")


if __name__ == "__main__":
    main()
