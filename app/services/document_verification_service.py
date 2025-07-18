import cv2
import numpy as np
from PIL import Image
import io
import base64
import logging
from typing import Dict, List, Tuple, Optional, Any
from app.core.aws_config import aws_config
# import face_recognition  # Comentado por problemas de compatibilidad en Windows

logger = logging.getLogger(__name__)


class DocumentVerificationService:
    """Service for automated document and selfie verification using AWS services"""

    def __init__(self):
        self.aws_config = aws_config

    def _compress_if_needed(self, image_data: bytes) -> bytes:
        """
        Comprime la imagen si es mayor a 5MB antes de enviar a AWS

        Args:
            image_data: Datos de la imagen en bytes

        Returns:
            Datos de la imagen comprimida o original si no necesita compresión
        """
        try:
            # Si la imagen es menor o igual a 5MB, no comprimir
            if len(image_data) <= 5 * 1024 * 1024:
                return image_data

            logger.info(
                f"Comprimiendo imagen de {len(image_data) / (1024*1024):.2f}MB a máximo 5MB")

            # Abrir imagen con Pillow
            image = Image.open(io.BytesIO(image_data))

            # Redimensionar si es muy grande (máximo 2000x2000 píxeles)
            max_size = 2000
            if image.size[0] > max_size or image.size[1] > max_size:
                # Mantener proporción de aspecto
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                logger.info(f"Redimensionando imagen a {image.size}")

            # Guardar con compresión JPEG
            output = io.BytesIO()

            # Convertir a RGB si es necesario (para JPEG)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Crear fondo blanco para imágenes con transparencia
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()
                                 [-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            # Guardar con compresión optimizada
            image.save(output, format='JPEG', quality=85, optimize=True)
            compressed_data = output.getvalue()

            # Verificar que la compresión fue efectiva
            if len(compressed_data) > 5 * 1024 * 1024:
                # Si aún es muy grande, comprimir más agresivamente
                output = io.BytesIO()
                image.save(output, format='JPEG', quality=70, optimize=True)
                compressed_data = output.getvalue()
                logger.warning(
                    f"Compresión agresiva aplicada - Tamaño final: {len(compressed_data) / (1024*1024):.2f}MB")

            logger.info(
                f"Imagen comprimida exitosamente - Tamaño original: {len(image_data) / (1024*1024):.2f}MB, Final: {len(compressed_data) / (1024*1024):.2f}MB")

            return compressed_data

        except Exception as e:
            logger.error(f"Error comprimiendo imagen: {e}")
            # Si hay error en la compresión, retornar la imagen original
            # AWS puede rechazar la imagen, pero es mejor que fallar completamente
            return image_data

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

    def compare_faces(self, document_image_data: bytes, selfie_image_data: bytes) -> Dict[str, Any]:
        """
        Compara rostros entre un documento y una selfie para verificar identidad
        (Implementación simplificada usando OpenCV - sin face_recognition)

        Args:
            document_image_data: Imagen del documento en bytes
            selfie_image_data: Imagen de la selfie en bytes

        Returns:
            Dict con resultados de la comparación facial
        """
        try:
            # Detectar rostros en el documento usando OpenCV
            document_faces = self._detect_faces_in_document_opencv(
                document_image_data)

            # Detectar rostros en la selfie usando OpenCV
            selfie_faces = self._detect_faces_in_selfie_opencv(
                selfie_image_data)

            # Manejar casos donde no se detecten rostros
            if not document_faces['faces_found']:
                return {
                    'success': False,
                    'error': 'No se detectaron rostros en el documento',
                    'document_faces': 0,
                    'selfie_faces': selfie_faces['face_count'],
                    'similarity_score': 0.0,
                    'note': 'Using OpenCV face detection (face_recognition not available)'
                }

            if not selfie_faces['faces_found']:
                return {
                    'success': False,
                    'error': 'No se detectaron rostros en la selfie',
                    'document_faces': document_faces['face_count'],
                    'selfie_faces': 0,
                    'similarity_score': 0.0,
                    'note': 'Using OpenCV face detection (face_recognition not available)'
                }

            # Comparar rostros usando características básicas de OpenCV
            similarity_results = self._compare_faces_with_opencv(
                document_faces['face_features'],
                selfie_faces['face_features']
            )

            # Calcular score de similitud
            similarity_score = self._calculate_facial_similarity_score_opencv(
                similarity_results)

            # Determinar si es la misma persona (umbral más bajo para OpenCV)
            is_same_person = similarity_score >= 0.4  # Umbral más bajo para OpenCV

            return {
                'success': True,
                'is_same_person': is_same_person,
                'similarity_score': similarity_score,
                'document_faces': document_faces['face_count'],
                'selfie_faces': selfie_faces['face_count'],
                'comparison_details': {
                    'best_match_score': similarity_results.get('best_match_score', 0.0),
                    'average_similarity': similarity_results.get('average_similarity', 0.0),
                    'matches_found': similarity_results.get('matches_found', 0),
                    'total_comparisons': similarity_results.get('total_comparisons', 0)
                },
                'face_locations': {
                    'document_faces': document_faces['face_locations'],
                    'selfie_faces': selfie_faces['face_locations']
                },
                'quality_indicators': {
                    'document_face_quality': document_faces['quality_score'],
                    'selfie_face_quality': selfie_faces['quality_score']
                },
                'note': 'Using OpenCV face detection (face_recognition not available)'
            }

        except Exception as e:
            logger.error(f"Error in face comparison: {e}")
            return {
                'success': False,
                'error': str(e),
                'similarity_score': 0.0,
                'note': 'Using OpenCV face detection (face_recognition not available)'
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

    def _detect_faces_in_document(self, image_data: bytes) -> Dict[str, Any]:
        """Detecta rostros en una imagen de documento"""
        try:
            # Convertir bytes a numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return {
                    'faces_found': False,
                    'face_count': 0,
                    'face_encodings': [],
                    'face_locations': [],
                    'quality_score': 0.0,
                    'error': 'Invalid image format'
                }

            # Convertir BGR a RGB para face_recognition
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detectar ubicaciones de rostros
            face_locations = face_recognition.face_locations(rgb_image)

            if not face_locations:
                return {
                    'faces_found': False,
                    'face_count': 0,
                    'face_encodings': [],
                    'face_locations': [],
                    'quality_score': 0.0,
                    'error': 'No faces detected in document'
                }

            # Extraer encodings de rostros
            face_encodings = face_recognition.face_encodings(
                rgb_image, face_locations)

            # Calcular calidad de los rostros detectados
            quality_score = self._calculate_face_quality_for_comparison(
                image, face_locations)

            return {
                'faces_found': True,
                'face_count': len(face_locations),
                'face_encodings': face_encodings,
                'face_locations': face_locations,
                'quality_score': quality_score
            }

        except Exception as e:
            logger.error(f"Error detecting faces in document: {e}")
            return {
                'faces_found': False,
                'face_count': 0,
                'face_encodings': [],
                'face_locations': [],
                'quality_score': 0.0,
                'error': str(e)
            }

    def _detect_faces_in_selfie(self, image_data: bytes) -> Dict[str, Any]:
        """Detecta rostros en una selfie"""
        try:
            # Convertir bytes a numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return {
                    'faces_found': False,
                    'face_count': 0,
                    'face_encodings': [],
                    'face_locations': [],
                    'quality_score': 0.0,
                    'error': 'Invalid image format'
                }

            # Convertir BGR a RGB para face_recognition
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detectar ubicaciones de rostros
            face_locations = face_recognition.face_locations(rgb_image)

            if not face_locations:
                return {
                    'faces_found': False,
                    'face_count': 0,
                    'face_encodings': [],
                    'face_locations': [],
                    'quality_score': 0.0,
                    'error': 'No faces detected in selfie'
                }

            # Extraer encodings de rostros
            face_encodings = face_recognition.face_encodings(
                rgb_image, face_locations)

            # Calcular calidad de los rostros detectados
            quality_score = self._calculate_face_quality_for_comparison(
                image, face_locations)

            return {
                'faces_found': True,
                'face_count': len(face_locations),
                'face_encodings': face_encodings,
                'face_locations': face_locations,
                'quality_score': quality_score
            }

        except Exception as e:
            logger.error(f"Error detecting faces in selfie: {e}")
            return {
                'faces_found': False,
                'face_count': 0,
                'face_encodings': [],
                'face_locations': [],
                'quality_score': 0.0,
                'error': str(e)
            }

    def _compare_faces_with_face_recognition(self, document_encodings: List, selfie_encodings: List) -> Dict[str, Any]:
        """Compara rostros usando face_recognition"""
        try:
            if not document_encodings or not selfie_encodings:
                return {
                    'best_match_score': 0.0,
                    'average_similarity': 0.0,
                    'matches_found': 0,
                    'total_comparisons': 0,
                    'comparison_matrix': []
                }

            # Realizar todas las comparaciones posibles
            comparison_matrix = []
            total_comparisons = len(document_encodings) * len(selfie_encodings)
            matches_found = 0
            similarity_scores = []

            for doc_encoding in document_encodings:
                for selfie_encoding in selfie_encodings:
                    # Calcular distancia entre encodings
                    distance = face_recognition.face_distance(
                        [doc_encoding], selfie_encoding)[0]

                    # Convertir distancia a score de similitud (1 - distancia)
                    similarity = 1.0 - distance
                    similarity_scores.append(similarity)

                    # Considerar match si similitud > 0.6
                    is_match = similarity > 0.6
                    if is_match:
                        matches_found += 1

                    comparison_matrix.append({
                        'document_face_idx': document_encodings.index(doc_encoding),
                        'selfie_face_idx': selfie_encodings.index(selfie_encoding),
                        'similarity_score': similarity,
                        'is_match': is_match
                    })

            # Calcular estadísticas
            best_match_score = max(
                similarity_scores) if similarity_scores else 0.0
            average_similarity = sum(
                similarity_scores) / len(similarity_scores) if similarity_scores else 0.0

            return {
                'best_match_score': best_match_score,
                'average_similarity': average_similarity,
                'matches_found': matches_found,
                'total_comparisons': total_comparisons,
                'comparison_matrix': comparison_matrix
            }

        except Exception as e:
            logger.error(f"Error comparing faces with face_recognition: {e}")
            return {
                'best_match_score': 0.0,
                'average_similarity': 0.0,
                'matches_found': 0,
                'total_comparisons': 0,
                'comparison_matrix': [],
                'error': str(e)
            }

    def _calculate_facial_similarity_score(self, comparison_results: Dict[str, Any]) -> float:
        """Calcula el score final de similitud facial"""
        try:
            best_match = comparison_results.get('best_match_score', 0.0)
            average_similarity = comparison_results.get(
                'average_similarity', 0.0)
            matches_found = comparison_results.get('matches_found', 0)
            total_comparisons = comparison_results.get('total_comparisons', 1)

            # Pesos para diferentes factores
            weights = {
                'best_match': 0.6,      # El mejor match es más importante
                'average_similarity': 0.3,  # Promedio de similitud
                'match_ratio': 0.1       # Proporción de matches
            }

            # Calcular ratio de matches
            match_ratio = matches_found / total_comparisons if total_comparisons > 0 else 0.0

            # Calcular score final ponderado
            final_score = (
                best_match * weights['best_match'] +
                average_similarity * weights['average_similarity'] +
                match_ratio * weights['match_ratio']
            )

            return max(0.0, min(1.0, final_score))

        except Exception as e:
            logger.error(f"Error calculating facial similarity score: {e}")
            return 0.0

    def _calculate_face_quality_for_comparison(self, image: np.ndarray, face_locations: List) -> float:
        """Calcula la calidad de los rostros para comparación"""
        try:
            if not face_locations:
                return 0.0

            quality_scores = []

            for face_location in face_locations:
                top, right, bottom, left = face_location

                # Extraer región del rostro
                face_region = image[top:bottom, left:right]

                if face_region.size == 0:
                    continue

                # Calcular métricas de calidad
                # Tamaño del rostro
                face_size = (right - left) * (bottom - top)
                image_size = image.shape[0] * image.shape[1]
                size_ratio = face_size / image_size

                # Nitidez del rostro
                gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
                sharpness = cv2.Laplacian(gray_face, cv2.CV_64F).var()

                # Brillo del rostro
                brightness = np.mean(gray_face)

                # Normalizar scores
                # Rostro debe ser al menos 10% de la imagen
                size_score = min(size_ratio * 10, 1.0)
                sharpness_score = min(sharpness / 1000, 1.0)
                brightness_score = 1.0 - abs(brightness - 128) / 128

                # Score de calidad para este rostro
                face_quality = (size_score + sharpness_score +
                                brightness_score) / 3
                quality_scores.append(face_quality)

            # Retornar el promedio de calidad de todos los rostros
            return sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        except Exception as e:
            logger.error(f"Error calculating face quality for comparison: {e}")
            return 0.0

    def _detect_faces_in_document_opencv(self, image_data: bytes) -> Dict[str, Any]:
        """Detecta rostros en una imagen de documento usando OpenCV"""
        try:
            # Convertir bytes a numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return {
                    'faces_found': False,
                    'face_count': 0,
                    'face_features': [],
                    'face_locations': [],
                    'quality_score': 0.0,
                    'error': 'Invalid image format'
                }

            # Convertir a escala de grises para detección
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Cargar el clasificador de rostros de OpenCV
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

            # Detectar rostros
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)

            if len(faces) == 0:
                return {
                    'faces_found': False,
                    'face_count': 0,
                    'face_features': [],
                    'face_locations': [],
                    'quality_score': 0.0,
                    'error': 'No faces detected in document'
                }

            # Extraer características básicas de los rostros
            face_features = []
            face_locations = []

            for (x, y, w, h) in faces:
                # Extraer región del rostro
                face_region = gray[y:y+h, x:x+w]

                # Calcular características básicas
                features = self._extract_face_features_opencv(face_region)
                face_features.append(features)
                # top, right, bottom, left
                face_locations.append([y, x+w, y+h, x])

            # Calcular calidad de los rostros detectados
            quality_score = self._calculate_face_quality_for_comparison(
                image, faces)

            return {
                'faces_found': True,
                'face_count': len(faces),
                'face_features': face_features,
                'face_locations': face_locations,
                'quality_score': quality_score
            }

        except Exception as e:
            logger.error(f"Error detecting faces in document: {e}")
            return {
                'faces_found': False,
                'face_count': 0,
                'face_features': [],
                'face_locations': [],
                'quality_score': 0.0,
                'error': str(e)
            }

    def _detect_faces_in_selfie_opencv(self, image_data: bytes) -> Dict[str, Any]:
        """Detecta rostros en una selfie usando OpenCV"""
        try:
            # Convertir bytes a numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return {
                    'faces_found': False,
                    'face_count': 0,
                    'face_features': [],
                    'face_locations': [],
                    'quality_score': 0.0,
                    'error': 'Invalid image format'
                }

            # Convertir a escala de grises para detección
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Cargar el clasificador de rostros de OpenCV
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

            # Detectar rostros
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)

            if len(faces) == 0:
                return {
                    'faces_found': False,
                    'face_count': 0,
                    'face_features': [],
                    'face_locations': [],
                    'quality_score': 0.0,
                    'error': 'No faces detected in selfie'
                }

            # Extraer características básicas de los rostros
            face_features = []
            face_locations = []

            for (x, y, w, h) in faces:
                # Extraer región del rostro
                face_region = gray[y:y+h, x:x+w]

                # Calcular características básicas
                features = self._extract_face_features_opencv(face_region)
                face_features.append(features)
                # top, right, bottom, left
                face_locations.append([y, x+w, y+h, x])

            # Calcular calidad de los rostros detectados
            quality_score = self._calculate_face_quality_for_comparison(
                image, faces)

            return {
                'faces_found': True,
                'face_count': len(faces),
                'face_features': face_features,
                'face_locations': face_locations,
                'quality_score': quality_score
            }

        except Exception as e:
            logger.error(f"Error detecting faces in selfie: {e}")
            return {
                'faces_found': False,
                'face_count': 0,
                'face_features': [],
                'face_locations': [],
                'quality_score': 0.0,
                'error': str(e)
            }

    def _extract_face_features_opencv(self, face_region: np.ndarray) -> Dict[str, float]:
        """Extrae características básicas de un rostro usando OpenCV"""
        try:
            # Redimensionar a un tamaño estándar para comparación
            face_resized = cv2.resize(face_region, (64, 64))

            # Calcular histograma
            hist = cv2.calcHist([face_resized], [0], None, [256], [0, 256])
            hist_normalized = hist.flatten() / np.sum(hist)

            # Calcular características básicas
            features = {
                'histogram': hist_normalized.tolist(),
                'mean_brightness': np.mean(face_resized),
                'std_brightness': np.std(face_resized),
                'face_size': face_region.shape[0] * face_region.shape[1],
                'aspect_ratio': face_region.shape[1] / face_region.shape[0] if face_region.shape[0] > 0 else 1.0
            }

            return features

        except Exception as e:
            logger.error(f"Error extracting face features: {e}")
            return {
                'histogram': [0.0] * 256,
                'mean_brightness': 0.0,
                'std_brightness': 0.0,
                'face_size': 0.0,
                'aspect_ratio': 1.0
            }

    def _compare_faces_with_opencv(self, document_features: List, selfie_features: List) -> Dict[str, Any]:
        """Compara rostros usando características básicas de OpenCV"""
        try:
            if not document_features or not selfie_features:
                return {
                    'best_match_score': 0.0,
                    'average_similarity': 0.0,
                    'matches_found': 0,
                    'total_comparisons': 0,
                    'comparison_matrix': []
                }

            # Realizar todas las comparaciones posibles
            comparison_matrix = []
            total_comparisons = len(document_features) * len(selfie_features)
            matches_found = 0
            similarity_scores = []

            for doc_features in document_features:
                for selfie_features_item in selfie_features:
                    # Calcular similitud basada en características básicas
                    similarity = self._calculate_face_similarity_opencv(
                        doc_features, selfie_features_item)
                    similarity_scores.append(similarity)

                    # Considerar match si similitud > 0.4 (umbral más bajo para OpenCV)
                    is_match = similarity > 0.4
                    if is_match:
                        matches_found += 1

                    comparison_matrix.append({
                        'document_face_idx': document_features.index(doc_features),
                        'selfie_face_idx': selfie_features.index(selfie_features_item),
                        'similarity_score': similarity,
                        'is_match': is_match
                    })

            # Calcular estadísticas
            best_match_score = max(
                similarity_scores) if similarity_scores else 0.0
            average_similarity = sum(
                similarity_scores) / len(similarity_scores) if similarity_scores else 0.0

            return {
                'best_match_score': best_match_score,
                'average_similarity': average_similarity,
                'matches_found': matches_found,
                'total_comparisons': total_comparisons,
                'comparison_matrix': comparison_matrix
            }

        except Exception as e:
            logger.error(f"Error comparing faces with OpenCV: {e}")
            return {
                'best_match_score': 0.0,
                'average_similarity': 0.0,
                'matches_found': 0,
                'total_comparisons': 0,
                'comparison_matrix': [],
                'error': str(e)
            }

    def _calculate_face_similarity_opencv(self, features1: Dict, features2: Dict) -> float:
        """Calcula similitud entre dos rostros usando características básicas"""
        try:
            # Comparar histogramas usando correlación
            hist1 = np.array(features1['histogram'])
            hist2 = np.array(features2['histogram'])

            # Correlación de histogramas
            hist_similarity = np.corrcoef(hist1, hist2)[0, 1]
            hist_similarity = max(0.0, hist_similarity) if not np.isnan(
                hist_similarity) else 0.0

            # Comparar características básicas
            brightness_similarity = 1.0 - \
                abs(features1['mean_brightness'] -
                    features2['mean_brightness']) / 255.0
            std_similarity = 1.0 - \
                abs(features1['std_brightness'] -
                    features2['std_brightness']) / 255.0
            aspect_similarity = 1.0 - abs(features1['aspect_ratio'] - features2['aspect_ratio']) / max(
                features1['aspect_ratio'], features2['aspect_ratio'])

            # Calcular similitud ponderada
            weights = {
                'histogram': 0.5,
                'brightness': 0.2,
                'std': 0.2,
                'aspect': 0.1
            }

            final_similarity = (
                hist_similarity * weights['histogram'] +
                brightness_similarity * weights['brightness'] +
                std_similarity * weights['std'] +
                aspect_similarity * weights['aspect']
            )

            return max(0.0, min(1.0, final_similarity))

        except Exception as e:
            logger.error(f"Error calculating face similarity: {e}")
            return 0.0

    def _calculate_facial_similarity_score_opencv(self, comparison_results: Dict[str, Any]) -> float:
        """Calcula el score final de similitud facial usando OpenCV"""
        try:
            best_match = comparison_results.get('best_match_score', 0.0)
            average_similarity = comparison_results.get(
                'average_similarity', 0.0)
            matches_found = comparison_results.get('matches_found', 0)
            total_comparisons = comparison_results.get('total_comparisons', 1)

            # Pesos para diferentes factores (ajustados para OpenCV)
            weights = {
                'best_match': 0.7,      # El mejor match es más importante
                'average_similarity': 0.2,  # Promedio de similitud
                'match_ratio': 0.1       # Proporción de matches
            }

            # Calcular ratio de matches
            match_ratio = matches_found / total_comparisons if total_comparisons > 0 else 0.0

            # Calcular score final ponderado
            final_score = (
                best_match * weights['best_match'] +
                average_similarity * weights['average_similarity'] +
                match_ratio * weights['match_ratio']
            )

            return max(0.0, min(1.0, final_score))

        except Exception as e:
            logger.error(f"Error calculating facial similarity score: {e}")
            return 0.0

    def calculate_final_score(self, document_result: Dict[str, Any], selfie_result: Dict[str, Any],
                              face_comparison_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula la puntuación final de verificación combinando todos los resultados

        Args:
            document_result: Resultado de verificación de documento
            selfie_result: Resultado de verificación de selfie
            face_comparison_result: Resultado de comparación facial

        Returns:
            Dict con puntuación final y decisión de verificación
        """
        try:
            # Extraer puntuaciones individuales
            document_score = document_result.get('score', 0.0)
            selfie_score = selfie_result.get('score', 0.0)
            face_comparison_score = face_comparison_result.get(
                'similarity_score', 0.0)

            # Pesos acordados (65% documento, 20% selfie, 15% comparación facial)
            weights = {
                'document': 0.65,
                'selfie': 0.20,
                'face_comparison': 0.15
            }

            # Calcular puntuación final ponderada
            final_score = (
                document_score * weights['document'] +
                selfie_score * weights['selfie'] +
                face_comparison_score * weights['face_comparison']
            )

            # Determinar decisión basada en puntuación final
            decision = self._determine_verification_decision(final_score)

            # Calcular puntuaciones detalladas por componente
            detailed_scores = {
                'document': {
                    'score': document_score,
                    'weight': weights['document'],
                    'weighted_score': document_score * weights['document'],
                    'details': {
                        'quality_score': document_result.get('quality_score', 0.0),
                        'textract_confidence': document_result.get('textract_result', {}).get('confidence', 0.0),
                        'rekognition_confidence': document_result.get('rekognition_result', {}).get('confidence', 0.0),
                        'format_valid': document_result.get('format_validation', {}).get('valid', False),
                        'detected_type': document_result.get('detected_type', 'unknown')
                    }
                },
                'selfie': {
                    'score': selfie_score,
                    'weight': weights['selfie'],
                    'weighted_score': selfie_score * weights['selfie'],
                    'details': {
                        'quality_score': selfie_result.get('quality_score', 0.0),
                        'selfie_quality_score': selfie_result.get('selfie_quality_score', 0.0),
                        'liveness_score': selfie_result.get('liveness_score', 0.0),
                        'aws_confidence': selfie_result.get('aws_confidence', 0.0),
                        'face_detected': selfie_result.get('face_detected', False),
                        'face_count': selfie_result.get('face_count', 0)
                    }
                },
                'face_comparison': {
                    'score': face_comparison_score,
                    'weight': weights['face_comparison'],
                    'weighted_score': face_comparison_score * weights['face_comparison'],
                    'details': {
                        'best_match_score': face_comparison_result.get('best_match_score', 0.0),
                        'average_similarity': face_comparison_result.get('average_similarity', 0.0),
                        'matches_found': face_comparison_result.get('matches_found', 0),
                        'document_faces': face_comparison_result.get('document_faces', 0),
                        'selfie_faces': face_comparison_result.get('selfie_faces', 0),
                        'comparison_method': 'OpenCV (face_recognition not available)'
                    }
                }
            }

            # Información adicional para auditoría
            audit_info = {
                'verification_timestamp': self._get_current_timestamp(),
                'component_scores': detailed_scores,
                'decision_thresholds': {
                    'approval_threshold': 0.75,
                    'manual_review_threshold': 0.60,
                    'rejection_threshold': 0.40
                },
                'weight_justification': {
                    'document_priority': 'Documentos son la base de identidad legal',
                    'selfie_importance': 'Verificación de identidad en tiempo real',
                    'face_comparison': 'Validación adicional de similitud facial'
                }
            }

            return {
                'success': True,
                'final_score': final_score,
                'decision': decision,
                'detailed_scores': detailed_scores,
                'audit_info': audit_info,
                'recommendations': self._generate_verification_recommendations(
                    final_score, detailed_scores, decision
                )
            }

        except Exception as e:
            logger.error(f"Error calculating final score: {e}")
            return {
                'success': False,
                'error': str(e),
                'final_score': 0.0,
                'decision': 'ERROR'
            }

    def _determine_verification_decision(self, final_score: float) -> str:
        """
        Determina la decisión de verificación basada en la puntuación final

        Args:
            final_score: Puntuación final (0.0 - 1.0)

        Returns:
            Decisión: 'APPROVED', 'MANUAL_REVIEW', 'REJECTED'
        """
        if final_score >= 0.75:
            return 'APPROVED'
        elif final_score >= 0.60:
            return 'MANUAL_REVIEW'
        else:
            return 'REJECTED'

    def _generate_verification_recommendations(self, final_score: float,
                                               detailed_scores: Dict, decision: str) -> List[str]:
        """
        Genera recomendaciones basadas en los resultados de verificación

        Args:
            final_score: Puntuación final
            detailed_scores: Puntuaciones detalladas por componente
            decision: Decisión de verificación

        Returns:
            Lista de recomendaciones
        """
        recommendations = []

        # Recomendaciones basadas en la decisión
        if decision == 'APPROVED':
            recommendations.append("Verificación aprobada automáticamente")
        elif decision == 'MANUAL_REVIEW':
            recommendations.append(
                "Revisión manual requerida - verificar documentos adicionales")
        else:  # REJECTED
            recommendations.append(
                "Verificación rechazada - solicitar nueva documentación")

        # Recomendaciones específicas por componente
        doc_score = detailed_scores['document']['score']
        selfie_score = detailed_scores['selfie']['score']
        face_score = detailed_scores['face_comparison']['score']

        if doc_score < 0.6:
            recommendations.append(
                "Calidad del documento baja - solicitar imagen más clara")

        if selfie_score < 0.5:
            recommendations.append(
                "Selfie de baja calidad - solicitar nueva foto")

        if face_score < 0.3:
            recommendations.append(
                "Similitud facial baja - verificar identidad manualmente")

        # Recomendaciones de mejora
        if final_score < 0.75:
            recommendations.append(
                "Considerar implementar verificación biométrica adicional")

        return recommendations

    def _get_current_timestamp(self) -> str:
        """Obtiene timestamp actual para auditoría"""
        from datetime import datetime
        return datetime.now().isoformat()

    def verify_identity(self, document_image_data: bytes, selfie_image_data: bytes,
                        document_type: str = None) -> Dict[str, Any]:
        """
        Verificación completa de identidad: documento, selfie y comparación facial

        Args:
            document_image_data: Imagen del documento en bytes
            selfie_image_data: Imagen de la selfie en bytes
            document_type: Tipo de documento esperado (opcional)

        Returns:
            Dict con resultado completo de verificación de identidad
        """
        try:
            logger.info("Iniciando verificación completa de identidad")

            # Paso 1: Verificar documento
            logger.info("Verificando documento...")
            document_result = self.verify_document(
                document_image_data, document_type)

            if not document_result['success']:
                logger.warning(
                    f"Error en verificación de documento: {document_result.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'error': f"Error en verificación de documento: {document_result.get('error', 'Unknown error')}",
                    'document_result': document_result,
                    'final_score': 0.0,
                    'decision': 'ERROR'
                }

            # Paso 2: Verificar selfie
            logger.info("Verificando selfie...")
            selfie_result = self.verify_selfie(selfie_image_data)

            if not selfie_result['success']:
                logger.warning(
                    f"Error en verificación de selfie: {selfie_result.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'error': f"Error en verificación de selfie: {selfie_result.get('error', 'Unknown error')}",
                    'document_result': document_result,
                    'selfie_result': selfie_result,
                    'final_score': 0.0,
                    'decision': 'ERROR'
                }

            # Paso 3: Comparar rostros
            logger.info("Comparando rostros...")
            face_comparison_result = self.compare_faces(
                document_image_data, selfie_image_data)

            if not face_comparison_result['success']:
                logger.warning(
                    f"Error en comparación facial: {face_comparison_result.get('error', 'Unknown error')}")
                # Continuar con el proceso aunque falle la comparación facial
                face_comparison_result['similarity_score'] = 0.0

            # Paso 4: Calcular puntuación final
            logger.info("Calculando puntuación final...")
            final_score_result = self.calculate_final_score(
                document_result,
                selfie_result,
                face_comparison_result
            )

            # Paso 5: Preparar resultado final
            verification_summary = {
                'success': True,
                'verification_id': self._generate_verification_id(),
                'timestamp': self._get_current_timestamp(),
                'final_score': final_score_result['final_score'],
                'decision': final_score_result['decision'],
                'detailed_scores': final_score_result['detailed_scores'],
                'recommendations': final_score_result['recommendations'],
                'audit_info': final_score_result['audit_info'],
                'component_results': {
                    'document': {
                        'success': document_result['success'],
                        'score': document_result['score'],
                        'detected_type': document_result.get('detected_type', 'unknown'),
                        'quality_score': document_result.get('quality_score', 0.0),
                        'confidence': document_result.get('confidence', 0.0)
                    },
                    'selfie': {
                        'success': selfie_result['success'],
                        'score': selfie_result['score'],
                        'face_detected': selfie_result.get('face_detected', False),
                        'face_count': selfie_result.get('face_count', 0),
                        'liveness_score': selfie_result.get('liveness_score', 0.0)
                    },
                    'face_comparison': {
                        'success': face_comparison_result['success'],
                        'similarity_score': face_comparison_result.get('similarity_score', 0.0),
                        'best_match_score': face_comparison_result.get('best_match_score', 0.0),
                        'document_faces': face_comparison_result.get('document_faces', 0),
                        'selfie_faces': face_comparison_result.get('selfie_faces', 0)
                    }
                },
                'verification_status': self._get_verification_status(final_score_result['decision']),
                'next_steps': self._get_next_steps(final_score_result['decision'])
            }

            logger.info(
                f"Verificación completada. Puntuación final: {final_score_result['final_score']:.3f}, Decisión: {final_score_result['decision']}")

            return verification_summary

        except Exception as e:
            logger.error(f"Error en verificación completa de identidad: {e}")
            return {
                'success': False,
                'error': str(e),
                'final_score': 0.0,
                'decision': 'ERROR',
                'verification_status': 'FAILED'
            }

    def _generate_verification_id(self) -> str:
        """Genera ID único para la verificación"""
        import uuid
        return f"verif_{uuid.uuid4().hex[:8]}_{int(self._get_current_timestamp().replace('-', '').replace(':', '').replace('.', '')[-8:])}"

    def _get_verification_status(self, decision: str) -> str:
        """Obtiene el estado de verificación basado en la decisión"""
        status_map = {
            'APPROVED': 'VERIFIED',
            'MANUAL_REVIEW': 'PENDING_REVIEW',
            'REJECTED': 'REJECTED',
            'ERROR': 'FAILED'
        }
        return status_map.get(decision, 'UNKNOWN')

    def _get_next_steps(self, decision: str) -> List[str]:
        """Genera los próximos pasos basados en la decisión"""
        if decision == 'APPROVED':
            return [
                "El conductor puede comenzar a operar inmediatamente",
                "Se enviará notificación de aprobación al conductor"
            ]
        elif decision == 'MANUAL_REVIEW':
            return [
                "Se requiere revisión manual por parte del administrador",
                "El conductor permanecerá en estado pendiente hasta la revisión",
                "Se enviará notificación al administrador para revisión"
            ]
        else:  # REJECTED
            return [
                "El conductor debe corregir los problemas identificados",
                "Se enviará notificación con detalles de los problemas",
                "El conductor puede volver a intentar después de corregir los problemas"
            ]

    async def verify_driver_complete(self, selfie_path: str, documents_paths: List[str] = None, driver_info_id: str = None) -> Dict[str, Any]:
        """
        Verificación completa durante el registro del conductor

        Args:
            selfie_path: Ruta al archivo de selfie guardado
            documents_paths: Lista de rutas a documentos (opcional, para futuras implementaciones)
            driver_info_id: ID del driver_info para logging

        Returns:
            Dict con el resultado de la verificación completa
        """
        try:
            logger.info(
                f"Iniciando verificación completa para driver_info_id: {driver_info_id}")

            # Leer la selfie
            with open(selfie_path, 'rb') as f:
                selfie_data = f.read()

            # 1. Verificar selfie
            logger.info("Verificando selfie...")
            selfie_result = self.verify_selfie(selfie_data)

            # 2. Verificar documentos (por ahora solo simulamos, ya están guardados)
            logger.info("Verificando documentos...")
            # TODO: En el futuro, aquí se procesarían los documentos guardados
            # Por ahora, simulamos un resultado de documento
            document_result = {
                'score': 0.8,  # Score simulado
                'valid': True,
                'type': 'driver_license',
                'confidence': 0.85
            }

            # 3. Comparación facial (selfie vs selfie por ahora)
            logger.info("Realizando comparación facial...")
            # Por ahora comparamos la selfie consigo misma para simular
            face_comparison_result = {
                'similarity_score': 0.95,  # Score simulado alto
                'confidence': 0.9,
                'faces_detected': 1,
                'method': 'simulated'
            }

            # 4. Calcular score final
            logger.info("Calculando score final...")
            final_result = self.calculate_final_score(
                document_result=document_result,
                selfie_result=selfie_result,
                face_comparison_result=face_comparison_result
            )

            # 5. Determinar decisión
            decision = self._determine_verification_decision(
                final_result['final_score'])

            # 6. Generar recomendaciones
            recommendations = self._generate_verification_recommendations(
                final_result['final_score'],
                final_result['detailed_scores'],
                decision
            )

            # 7. Preparar respuesta
            result = {
                'verification_id': self._generate_verification_id(),
                'timestamp': self._get_current_timestamp(),
                'driver_info_id': driver_info_id,
                'decision': decision,
                'final_score': final_result['final_score'],
                'detailed_scores': final_result['detailed_scores'],
                'recommendations': recommendations,
                'status': self._get_verification_status(decision),
                'next_steps': self._get_next_steps(decision),
                'selfie_verification': selfie_result,
                'document_verification': document_result,
                'face_comparison': face_comparison_result
            }

            logger.info(
                f"Verificación completa completada. Decisión: {decision}, Score: {final_result['final_score']}")
            return result

        except Exception as e:
            logger.error(f"Error en verificación completa: {e}")
            return {
                'verification_id': self._generate_verification_id(),
                'timestamp': self._get_current_timestamp(),
                'driver_info_id': driver_info_id,
                'decision': 'MANUAL_REVIEW',  # En caso de error, requerir revisión manual
                'final_score': 0.0,
                'detailed_scores': {},
                'recommendations': ['Error en verificación automática. Se requiere revisión manual.'],
                'status': 'PENDING',
                'next_steps': ['Revisión manual requerida debido a error en verificación automática'],
                'error': str(e)
            }
