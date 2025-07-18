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
        Verify selfie quality, face detection, and liveness detection

        Args:
            image_data: Image bytes

        Returns:
            Dict with verification results including liveness detection
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

            # Analyze selfie-specific quality
            selfie_quality = self._analyze_selfie_quality(image, faces[0])

            # Detect liveness
            liveness_score = self._detect_liveness(image, faces[0])

            # Use AWS Rekognition for additional face analysis
            aws_face_analysis = self._analyze_face_with_aws(image_data)

            # Calculate final score with weighted components
            final_score = self._calculate_selfie_score(
                quality_score,
                selfie_quality,
                liveness_score,
                aws_face_analysis.get('confidence', 0.0)
            )

            return {
                'success': True,
                'score': final_score,
                'face_detected': True,
                'face_count': len(faces),
                'quality_score': quality_score,
                'selfie_quality_score': selfie_quality,
                'liveness_score': liveness_score,
                'aws_confidence': aws_face_analysis.get('confidence', 0.0),
                'aws_analysis': aws_face_analysis,
                'face_position': {
                    'x': int(faces[0][0]),
                    'y': int(faces[0][1]),
                    'width': int(faces[0][2]),
                    'height': int(faces[0][3])
                },
                'verification_details': {
                    'quality_analysis': {
                        'sharpness': self._calculate_sharpness(image),
                        'brightness': self._calculate_brightness(image),
                        'contrast': self._calculate_contrast(image)
                    },
                    'face_analysis': {
                        'face_size_ratio': self._calculate_face_size_ratio(image, faces[0]),
                        'face_centered': self._is_face_centered(image, faces[0]),
                        'face_angle': self._estimate_face_angle(image, faces[0])
                    },
                    'liveness_indicators': {
                        'natural_lighting': self._check_natural_lighting(image),
                        'no_screen_reflection': self._check_no_screen_reflection(image),
                        'natural_skin_tone': self._check_natural_skin_tone(image)
                    }
                }
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

    def _analyze_selfie_quality(self, image: np.ndarray, face_rect: tuple) -> float:
        """Analiza la calidad específica de una selfie"""
        try:
            # Extraer la región del rostro
            x, y, w, h = face_rect
            face_region = image[y:y+h, x:x+w]

            # Calcular el tamaño relativo del rostro
            face_size_ratio = self._calculate_face_size_ratio(image, face_rect)

            # Verificar si el rostro está centrado
            face_centered = self._is_face_centered(image, face_rect)

            # Estimar el ángulo del rostro
            face_angle = self._estimate_face_angle(image, face_rect)

            # Calcular scores individuales
            # Rostro debe ocupar al menos 50% de la imagen
            size_score = min(face_size_ratio * 2, 1.0)
            center_score = 1.0 if face_centered else 0.5
            # Penalizar ángulos muy pronunciados
            angle_score = 1.0 - abs(face_angle) / 45.0

            # Score final de calidad de selfie
            selfie_score = (size_score + center_score + angle_score) / 3
            return max(0.0, min(1.0, selfie_score))

        except Exception as e:
            logger.error(f"Error analyzing selfie quality: {e}")
            return 0.0

    def _detect_liveness(self, image: np.ndarray, face_rect: tuple) -> float:
        """Detecta si la selfie es de una persona real (liveness detection)"""
        try:
            # Extraer la región del rostro
            x, y, w, h = face_rect
            face_region = image[y:y+h, x:x+w]

            # Verificar iluminación natural
            natural_lighting = self._check_natural_lighting(image)

            # Verificar que no hay reflejos de pantalla
            no_screen_reflection = self._check_no_screen_reflection(image)

            # Verificar tono de piel natural
            natural_skin_tone = self._check_natural_skin_tone(image)

            # Verificar que no es una foto de una foto
            not_photo_of_photo = self._check_not_photo_of_photo(image)

            # Calcular score de liveness
            liveness_indicators = [
                natural_lighting,
                no_screen_reflection,
                natural_skin_tone,
                not_photo_of_photo
            ]

            liveness_score = sum(liveness_indicators) / \
                len(liveness_indicators)
            return max(0.0, min(1.0, liveness_score))

        except Exception as e:
            logger.error(f"Error in liveness detection: {e}")
            return 0.0

    def _calculate_selfie_score(self, quality_score: float, selfie_quality: float,
                                liveness_score: float, aws_confidence: float) -> float:
        """Calcula el score final de la selfie con pesos ponderados"""
        # Pesos para cada componente
        weights = {
            'quality': 0.25,        # Calidad general de la imagen
            'selfie_quality': 0.25,  # Calidad específica de selfie
            'liveness': 0.30,        # Detección de liveness (más importante)
            'aws_confidence': 0.20   # Confianza de AWS Rekognition
        }

        final_score = (
            quality_score * weights['quality'] +
            selfie_quality * weights['selfie_quality'] +
            liveness_score * weights['liveness'] +
            aws_confidence * weights['aws_confidence']
        )

        return max(0.0, min(1.0, final_score))

    def _calculate_face_size_ratio(self, image: np.ndarray, face_rect: tuple) -> float:
        """Calcula la proporción del tamaño del rostro respecto a la imagen"""
        try:
            x, y, w, h = face_rect
            face_area = w * h
            image_area = image.shape[0] * image.shape[1]
            ratio = face_area / image_area
            return min(ratio, 1.0)  # Normalizar a máximo 1.0
        except Exception as e:
            logger.error(f"Error calculating face size ratio: {e}")
            return 0.0

    def _is_face_centered(self, image: np.ndarray, face_rect: tuple) -> bool:
        """Verifica si el rostro está centrado en la imagen"""
        try:
            x, y, w, h = face_rect
            face_center_x = x + w // 2
            face_center_y = y + h // 2

            image_center_x = image.shape[1] // 2
            image_center_y = image.shape[0] // 2

            # Tolerancia del 20% del tamaño de la imagen
            tolerance_x = image.shape[1] * 0.2
            tolerance_y = image.shape[0] * 0.2

            return (abs(face_center_x - image_center_x) < tolerance_x and
                    abs(face_center_y - image_center_y) < tolerance_y)
        except Exception as e:
            logger.error(f"Error checking if face is centered: {e}")
            return False

    def _estimate_face_angle(self, image: np.ndarray, face_rect: tuple) -> float:
        """Estima el ángulo del rostro (simplificado)"""
        try:
            # Implementación simplificada - en producción usar landmarks faciales
            x, y, w, h = face_rect

            # Calcular la proporción ancho/alto del rostro
            aspect_ratio = w / h if h > 0 else 1.0

            # Si la proporción es muy diferente de 1, puede indicar rotación
            angle_estimate = abs(aspect_ratio - 1.0) * 45  # Máximo 45 grados

            return min(angle_estimate, 45.0)
        except Exception as e:
            logger.error(f"Error estimating face angle: {e}")
            return 0.0

    def _calculate_sharpness(self, image: np.ndarray) -> float:
        """Calcula la nitidez de la imagen"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            return min(laplacian_var / 1000, 1.0)
        except Exception as e:
            logger.error(f"Error calculating sharpness: {e}")
            return 0.0

    def _calculate_brightness(self, image: np.ndarray) -> float:
        """Calcula el brillo de la imagen"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            return 1.0 - abs(brightness - 128) / 128
        except Exception as e:
            logger.error(f"Error calculating brightness: {e}")
            return 0.0

    def _calculate_contrast(self, image: np.ndarray) -> float:
        """Calcula el contraste de la imagen"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            contrast = np.std(gray)
            return min(contrast / 50, 1.0)
        except Exception as e:
            logger.error(f"Error calculating contrast: {e}")
            return 0.0

    def _check_natural_lighting(self, image: np.ndarray) -> float:
        """Verifica si la iluminación es natural (no artificial)"""
        try:
            # Convertir a HSV para analizar la iluminación
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # Analizar el canal de valor (V) para detectar iluminación uniforme
            v_channel = hsv[:, :, 2]

            # Calcular la desviación estándar del valor
            v_std = np.std(v_channel)

            # Iluminación natural tiende a tener más variación
            natural_score = min(v_std / 50, 1.0)

            return natural_score
        except Exception as e:
            logger.error(f"Error checking natural lighting: {e}")
            return 0.5

    def _check_no_screen_reflection(self, image: np.ndarray) -> float:
        """Verifica que no hay reflejos de pantalla"""
        try:
            # Convertir a HSV
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # Buscar áreas muy brillantes que podrían ser reflejos
            v_channel = hsv[:, :, 2]

            # Contar píxeles muy brillantes (> 200)
            bright_pixels = np.sum(v_channel > 200)
            total_pixels = v_channel.size

            bright_ratio = bright_pixels / total_pixels

            # Si hay muchos píxeles brillantes, puede ser un reflejo
            no_reflection_score = 1.0 - min(bright_ratio * 5, 1.0)

            return max(0.0, no_reflection_score)
        except Exception as e:
            logger.error(f"Error checking screen reflection: {e}")
            return 0.5

    def _check_natural_skin_tone(self, image: np.ndarray) -> float:
        """Verifica que el tono de piel es natural"""
        try:
            # Convertir a HSV
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # Rango de tonos de piel en HSV
            lower_skin = np.array([0, 20, 70])
            upper_skin = np.array([20, 255, 255])

            # Crear máscara para tonos de piel
            skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)

            # Contar píxeles de piel
            skin_pixels = np.sum(skin_mask > 0)
            total_pixels = skin_mask.size

            skin_ratio = skin_pixels / total_pixels

            # Un ratio razonable de piel indica tono natural
            natural_skin_score = min(skin_ratio * 3, 1.0)

            return natural_skin_score
        except Exception as e:
            logger.error(f"Error checking natural skin tone: {e}")
            return 0.5

    def _check_not_photo_of_photo(self, image: np.ndarray) -> float:
        """Verifica que no es una foto de una foto (detección de moiré)"""
        try:
            # Convertir a escala de grises
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Aplicar FFT para detectar patrones repetitivos
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)

            # Calcular el espectro de potencia
            magnitude_spectrum = np.log(np.abs(f_shift) + 1)

            # Buscar patrones de alta frecuencia que indican moiré
            high_freq_energy = np.sum(magnitude_spectrum > np.mean(
                magnitude_spectrum) + 2 * np.std(magnitude_spectrum))

            # Normalizar
            total_energy = magnitude_spectrum.size
            high_freq_ratio = high_freq_energy / total_energy

            # Si hay mucha energía de alta frecuencia, puede ser una foto de foto
            not_photo_of_photo_score = 1.0 - min(high_freq_ratio * 10, 1.0)

            return max(0.0, not_photo_of_photo_score)
        except Exception as e:
            logger.error(f"Error checking photo of photo: {e}")
            return 0.5
