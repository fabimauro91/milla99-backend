import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.services.document_verification_service import DocumentVerificationService
from app.services.verify_docs_service import VerifyDocsService
from app.models.verify_docs import VerifyDocs
from app.core.db import get_db

logger = logging.getLogger(__name__)


class DriverVerificationOrchestrator:
    """
    Orchestrator service that coordinates automatic document verification
    with the existing manual verification system
    """

    def __init__(self):
        self.document_service = DocumentVerificationService()
        self.verify_docs_service = VerifyDocsService()

    async def process_driver_verification(
        self,
        driver_id: int,
        selfie_data: bytes = None,
        document_data: bytes = None,
        document_type: str = None
    ) -> Dict[str, Any]:
        """
        Process complete driver verification including selfie and documents

        Args:
            driver_id: ID of the driver
            selfie_data: Selfie image bytes
            document_data: Document image bytes
            document_type: Expected document type

        Returns:
            Dict with verification results and status
        """
        try:
            results = {
                'driver_id': driver_id,
                'timestamp': datetime.now().isoformat(),
                'selfie_verification': None,
                'document_verification': None,
                'overall_status': 'pending',
                'requires_manual_review': False,
                'automatic_score': 0.0
            }

            # Verify selfie if provided
            if selfie_data:
                logger.info(
                    f"Processing selfie verification for driver {driver_id}")
                selfie_result = self.document_service.verify_selfie(
                    selfie_data)
                results['selfie_verification'] = selfie_result

                if not selfie_result.get('success', False):
                    results['requires_manual_review'] = True
                    results['overall_status'] = 'failed'
                    logger.warning(
                        f"Selfie verification failed for driver {driver_id}")

            # Verify document if provided
            if document_data:
                logger.info(
                    f"Processing document verification for driver {driver_id}")
                document_result = self.document_service.verify_document(
                    document_data,
                    document_type
                )
                results['document_verification'] = document_result

                if not document_result.get('success', False):
                    results['requires_manual_review'] = True
                    results['overall_status'] = 'failed'
                    logger.warning(
                        f"Document verification failed for driver {driver_id}")

            # Calculate overall automatic score
            scores = []
            if results['selfie_verification'] and results['selfie_verification'].get('success'):
                scores.append(results['selfie_verification'].get('score', 0.0))

            if results['document_verification'] and results['document_verification'].get('success'):
                scores.append(
                    results['document_verification'].get('score', 0.0))

            if scores:
                results['automatic_score'] = sum(scores) / len(scores)

            # Determine if automatic verification is sufficient
            if results['automatic_score'] >= 0.8 and not results['requires_manual_review']:
                results['overall_status'] = 'approved'
                await self._update_verification_status(driver_id, 'approved', results)
                logger.info(
                    f"Driver {driver_id} automatically approved with score {results['automatic_score']}")
            else:
                results['overall_status'] = 'pending_manual_review'
                await self._update_verification_status(driver_id, 'pending', results)
                logger.info(
                    f"Driver {driver_id} requires manual review with score {results['automatic_score']}")

            return results

        except Exception as e:
            logger.error(
                f"Error processing verification for driver {driver_id}: {e}")
            return {
                'driver_id': driver_id,
                'error': str(e),
                'overall_status': 'error',
                'requires_manual_review': True
            }

    async def _update_verification_status(
        self,
        driver_id: int,
        status: str,
        verification_data: Dict[str, Any]
    ):
        """Update verification status in the database"""
        try:
            db = next(get_db())

            # Find existing verification record
            verify_doc = db.query(VerifyDocs).filter(
                VerifyDocs.driver_id == driver_id
            ).first()

            if verify_doc:
                # Update existing record
                verify_doc.status = status
                verify_doc.verification_data = verification_data
                verify_doc.updated_at = datetime.now()

                if status == 'approved':
                    verify_doc.verified_at = datetime.now()
                    verify_doc.verified_by = 'automatic_system'

            else:
                # Create new verification record
                verify_doc = VerifyDocs(
                    driver_id=driver_id,
                    status=status,
                    verification_data=verification_data,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

                if status == 'approved':
                    verify_doc.verified_at = datetime.now()
                    verify_doc.verified_by = 'automatic_system'

                db.add(verify_doc)

            db.commit()
            logger.info(
                f"Updated verification status for driver {driver_id} to {status}")

        except Exception as e:
            logger.error(
                f"Error updating verification status for driver {driver_id}: {e}")
            db.rollback()
            raise

    async def get_verification_status(self, driver_id: int) -> Dict[str, Any]:
        """Get current verification status for a driver"""
        try:
            db = next(get_db())

            verify_doc = db.query(VerifyDocs).filter(
                VerifyDocs.driver_id == driver_id
            ).first()

            if verify_doc:
                return {
                    'driver_id': driver_id,
                    'status': verify_doc.status,
                    'verification_data': verify_doc.verification_data,
                    'created_at': verify_doc.created_at.isoformat() if verify_doc.created_at else None,
                    'updated_at': verify_doc.updated_at.isoformat() if verify_doc.updated_at else None,
                    'verified_at': verify_doc.verified_at.isoformat() if verify_doc.verified_at else None,
                    'verified_by': verify_doc.verified_by
                }
            else:
                return {
                    'driver_id': driver_id,
                    'status': 'not_found',
                    'message': 'No verification record found'
                }

        except Exception as e:
            logger.error(
                f"Error getting verification status for driver {driver_id}: {e}")
            return {
                'driver_id': driver_id,
                'status': 'error',
                'error': str(e)
            }

    async def get_pending_verifications(self) -> List[Dict[str, Any]]:
        """Get all pending verifications that require manual review"""
        try:
            db = next(get_db())

            pending_verifications = db.query(VerifyDocs).filter(
                VerifyDocs.status.in_(['pending', 'pending_manual_review'])
            ).all()

            return [
                {
                    'driver_id': v.driver_id,
                    'status': v.status,
                    'verification_data': v.verification_data,
                    'created_at': v.created_at.isoformat() if v.created_at else None,
                    'updated_at': v.updated_at.isoformat() if v.updated_at else None
                }
                for v in pending_verifications
            ]

        except Exception as e:
            logger.error(f"Error getting pending verifications: {e}")
            return []

    async def approve_verification_manually(
        self,
        driver_id: int,
        admin_user_id: int,
        notes: str = None
    ) -> Dict[str, Any]:
        """Approve verification manually by admin"""
        try:
            db = next(get_db())

            verify_doc = db.query(VerifyDocs).filter(
                VerifyDocs.driver_id == driver_id
            ).first()

            if not verify_doc:
                return {
                    'success': False,
                    'error': 'Verification record not found'
                }

            # Update verification status
            verify_doc.status = 'approved'
            verify_doc.verified_at = datetime.now()
            verify_doc.verified_by = f'admin_{admin_user_id}'
            verify_doc.updated_at = datetime.now()

            # Add admin notes to verification data
            if verify_doc.verification_data is None:
                verify_doc.verification_data = {}

            verify_doc.verification_data['admin_approval'] = {
                'admin_user_id': admin_user_id,
                'approved_at': datetime.now().isoformat(),
                'notes': notes
            }

            db.commit()

            logger.info(
                f"Driver {driver_id} verification approved manually by admin {admin_user_id}")

            return {
                'success': True,
                'driver_id': driver_id,
                'status': 'approved',
                'approved_by': f'admin_{admin_user_id}',
                'approved_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(
                f"Error approving verification for driver {driver_id}: {e}")
            db.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    async def reject_verification_manually(
        self,
        driver_id: int,
        admin_user_id: int,
        reason: str,
        notes: str = None
    ) -> Dict[str, Any]:
        """Reject verification manually by admin"""
        try:
            db = next(get_db())

            verify_doc = db.query(VerifyDocs).filter(
                VerifyDocs.driver_id == driver_id
            ).first()

            if not verify_doc:
                return {
                    'success': False,
                    'error': 'Verification record not found'
                }

            # Update verification status
            verify_doc.status = 'rejected'
            verify_doc.updated_at = datetime.now()

            # Add admin rejection data
            if verify_doc.verification_data is None:
                verify_doc.verification_data = {}

            verify_doc.verification_data['admin_rejection'] = {
                'admin_user_id': admin_user_id,
                'rejected_at': datetime.now().isoformat(),
                'reason': reason,
                'notes': notes
            }

            db.commit()

            logger.info(
                f"Driver {driver_id} verification rejected by admin {admin_user_id}: {reason}")

            return {
                'success': True,
                'driver_id': driver_id,
                'status': 'rejected',
                'rejected_by': f'admin_{admin_user_id}',
                'rejected_at': datetime.now().isoformat(),
                'reason': reason
            }

        except Exception as e:
            logger.error(
                f"Error rejecting verification for driver {driver_id}: {e}")
            db.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    async def get_verification_statistics(self) -> Dict[str, Any]:
        """Get verification statistics"""
        try:
            db = next(get_db())

            total_verifications = db.query(VerifyDocs).count()
            approved_verifications = db.query(VerifyDocs).filter(
                VerifyDocs.status == 'approved'
            ).count()
            pending_verifications = db.query(VerifyDocs).filter(
                VerifyDocs.status.in_(['pending', 'pending_manual_review'])
            ).count()
            rejected_verifications = db.query(VerifyDocs).filter(
                VerifyDocs.status == 'rejected'
            ).count()

            automatic_approvals = db.query(VerifyDocs).filter(
                VerifyDocs.status == 'approved',
                VerifyDocs.verified_by == 'automatic_system'
            ).count()

            manual_approvals = approved_verifications - automatic_approvals

            return {
                'total_verifications': total_verifications,
                'approved_verifications': approved_verifications,
                'pending_verifications': pending_verifications,
                'rejected_verifications': rejected_verifications,
                'automatic_approvals': automatic_approvals,
                'manual_approvals': manual_approvals,
                'approval_rate': (approved_verifications / total_verifications * 100) if total_verifications > 0 else 0,
                'automatic_approval_rate': (automatic_approvals / total_verifications * 100) if total_verifications > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error getting verification statistics: {e}")
            return {
                'error': str(e)
            }
