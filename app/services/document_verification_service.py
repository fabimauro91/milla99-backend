import cv2
import numpy as np
from PIL import Image
import io
import base64
import logging
from typing import Dict, List, Tuple, Optional, Any
from app.core.aws_config import aws_config

logger = logging.getLogger(__name__)


class DocumentVerificationService:
    """Service for automated document and selfie verification using AWS services"""

    def __init__(self):
        self.aws_config = aws_config

    def verify_selfie(self, image_data: bytes) -> Dict[str, Any]:
        """
        Verify selfie quality and face detection

        Args:
            image_data: Image bytes

        Returns:
            Dict with verification results
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return {
                    'success': False,
                    'error': 'Invalid image format',
                    'score': 0.0
                }

            # Convert BGR to RGB for face detection
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Load OpenCV face detection cascade
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

            # Convert to grayscale for face detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)

            if len(faces) == 0:
                return {
                    'success': False,
                    'error': 'No face detected',
                    'score': 0.0
                }

            if len(faces) > 1:
                return {
                    'success': False,
                    'error': 'Multiple faces detected',
                    'score': 0.0
                }

            # Analyze image quality
            quality_score = self._analyze_image_quality(image)

            # Use AWS Rekognition for additional face analysis
            aws_face_analysis = self._analyze_face_with_aws(image_data)

            # Calculate final score
            final_score = (quality_score +
                           aws_face_analysis.get('confidence', 0.0)) / 2

            return {
                'success': True,
                'score': final_score,
                'face_detected': True,
                'face_count': len(faces),
                'quality_score': quality_score,
                'aws_confidence': aws_face_analysis.get('confidence', 0.0),
                'aws_analysis': aws_face_analysis
            }

        except Exception as e:
            logger.error(f"Error in selfie verification: {e}")
            return {
                'success': False,
                'error': str(e),
                'score': 0.0
            }

    def verify_document(self, image_data: bytes, document_type: str = None) -> Dict[str, Any]:
        """
        Verify document using AWS Textract and Rekognition

        Args:
            image_data: Image bytes
            document_type: Expected document type (optional)

        Returns:
            Dict with verification results
        """
        try:
            # Analyze image quality
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return {
                    'success': False,
                    'error': 'Invalid image format',
                    'score': 0.0
                }

            quality_score = self._analyze_image_quality(image)

            # Extract text using AWS Textract
            textract_result = self._extract_text_with_textract(image_data)

            # Analyze document with AWS Rekognition
            rekognition_result = self._analyze_document_with_rekognition(
                image_data)

            # Detect document type
            detected_type = self._detect_document_type(
                textract_result, rekognition_result)

            # Validate document format
            format_validation = self._validate_document_format(
                textract_result,
                detected_type,
                document_type
            )

            # Calculate final score
            final_score = self._calculate_document_score(
                quality_score,
                textract_result.get('confidence', 0.0),
                rekognition_result.get('confidence', 0.0),
                format_validation.get('valid', False)
            )

            return {
                'success': True,
                'score': final_score,
                'quality_score': quality_score,
                'detected_type': detected_type,
                'textract_result': textract_result,
                'rekognition_result': rekognition_result,
                'format_validation': format_validation,
                'extracted_text': textract_result.get('text', ''),
                'confidence': textract_result.get('confidence', 0.0)
            }

        except Exception as e:
            logger.error(f"Error in document verification: {e}")
            return {
                'success': False,
                'error': str(e),
                'score': 0.0
            }

    def _analyze_image_quality(self, image: np.ndarray) -> float:
        """Analyze image quality metrics"""
        try:
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Calculate sharpness (Laplacian variance)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            # Calculate brightness
            brightness = np.mean(gray)

            # Calculate contrast
            contrast = np.std(gray)

            # Normalize scores
            sharpness_score = min(laplacian_var / 1000,
                                  1.0)  # Normalize to 0-1
            brightness_score = 1.0 - \
                abs(brightness - 128) / 128  # Optimal around 128
            contrast_score = min(contrast / 50, 1.0)  # Normalize to 0-1

            # Calculate overall quality score
            quality_score = (sharpness_score +
                             brightness_score + contrast_score) / 3

            return max(0.0, min(1.0, quality_score))

        except Exception as e:
            logger.error(f"Error analyzing image quality: {e}")
            return 0.0

    def _analyze_face_with_aws(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze face using AWS Rekognition"""
        try:
            response = self.aws_config.rekognition_client.detect_faces(
                Image={'Bytes': image_data},
                Attributes=['ALL']
            )

            if not response['FaceDetails']:
                return {'confidence': 0.0, 'error': 'No face detected by AWS'}

            face = response['FaceDetails'][0]

            return {
                'confidence': face['Confidence'] / 100.0,
                'quality': face.get('Quality', {}),
                'attributes': face.get('Attributes', {}),
                'bounding_box': face.get('BoundingBox', {})
            }

        except Exception as e:
            logger.error(f"Error in AWS face analysis: {e}")
            return {'confidence': 0.0, 'error': str(e)}

    def _extract_text_with_textract(self, image_data: bytes) -> Dict[str, Any]:
        """Extract text using AWS Textract"""
        try:
            response = self.aws_config.textract_client.detect_document_text(
                Document={'Bytes': image_data}
            )

            # Extract text blocks
            text_blocks = []
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_blocks.append(block['Text'])

            full_text = ' '.join(text_blocks)

            # Calculate confidence based on average confidence of text blocks
            confidences = [
                block['Confidence']
                for block in response['Blocks']
                if block['BlockType'] == 'LINE'
            ]

            avg_confidence = sum(confidences) / \
                len(confidences) if confidences else 0.0

            return {
                'text': full_text,
                'confidence': avg_confidence / 100.0,
                'blocks': text_blocks,
                'block_count': len(text_blocks)
            }

        except Exception as e:
            logger.error(f"Error in Textract text extraction: {e}")
            return {'text': '', 'confidence': 0.0, 'error': str(e)}

    def _analyze_document_with_rekognition(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze document using AWS Rekognition"""
        try:
            response = self.aws_config.rekognition_client.detect_labels(
                Image={'Bytes': image_data},
                MaxLabels=10
            )

            # Look for document-related labels
            document_labels = ['Document', 'Text',
                               'Paper', 'Card', 'ID', 'License']
            found_labels = []

            for label in response['Labels']:
                if any(doc_label.lower() in label['Name'].lower() for doc_label in document_labels):
                    found_labels.append({
                        'name': label['Name'],
                        'confidence': label['Confidence'] / 100.0
                    })

            # Calculate overall confidence
            if found_labels:
                avg_confidence = sum(label['confidence']
                                     for label in found_labels) / len(found_labels)
            else:
                avg_confidence = 0.0

            return {
                'confidence': avg_confidence,
                'labels': found_labels,
                'all_labels': response['Labels']
            }

        except Exception as e:
            logger.error(f"Error in AWS document analysis: {e}")
            return {'confidence': 0.0, 'error': str(e)}

    def _detect_document_type(self, textract_result: Dict, rekognition_result: Dict) -> str:
        """Detect document type based on extracted text and labels"""
        text = textract_result.get('text', '').lower()
        labels = [label['name'].lower()
                  for label in rekognition_result.get('labels', [])]

        # Simple keyword-based detection
        if any(word in text for word in ['licencia', 'license', 'driver']):
            return 'driver_license'
        elif any(word in text for word in ['cedula', 'dni', 'identity', 'id']):
            return 'identity_card'
        elif any(word in text for word in ['pasaporte', 'passport']):
            return 'passport'
        elif any(word in text for word in ['vehiculo', 'vehicle', 'car']):
            return 'vehicle_registration'
        else:
            return 'unknown'

    def _validate_document_format(self, textract_result: Dict, detected_type: str, expected_type: str = None) -> Dict[str, Any]:
        """Validate document format based on type"""
        text = textract_result.get('text', '')
        block_count = textract_result.get('block_count', 0)

        # Basic validation rules
        valid = True
        errors = []

        if block_count < 3:
            valid = False
            errors.append('Insufficient text detected')

        if len(text) < 50:
            valid = False
            errors.append('Document text too short')

        if expected_type and detected_type != expected_type:
            valid = False
            errors.append(
                f'Document type mismatch: expected {expected_type}, detected {detected_type}')

        return {
            'valid': valid,
            'errors': errors,
            'detected_type': detected_type,
            'expected_type': expected_type
        }

    def _calculate_document_score(self, quality_score: float, textract_confidence: float,
                                  rekognition_confidence: float, format_valid: bool) -> float:
        """Calculate final document verification score"""
        # Weight the different factors
        weights = {
            'quality': 0.3,
            'textract': 0.4,
            'rekognition': 0.2,
            'format': 0.1
        }

        format_score = 1.0 if format_valid else 0.0

        final_score = (
            quality_score * weights['quality'] +
            textract_confidence * weights['textract'] +
            rekognition_confidence * weights['rekognition'] +
            format_score * weights['format']
        )

        return max(0.0, min(1.0, final_score))
