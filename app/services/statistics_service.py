from sqlmodel import Session, select
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
import traceback
import inspect

# Importar modelos necesarios
from app.models.user import User
from app.models.client_request import ClientRequest, StatusEnum
from app.models.transaction import Transaction, TransactionType
from app.models.withdrawal import Withdrawal, WithdrawalStatus
from app.models.driver_documents import DriverDocuments, DriverStatus
from app.models.driver_info import DriverInfo
from app.models.vehicle_info import VehicleInfo
from app.models.vehicle_type import VehicleType
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.driver_savings import DriverSavings
from app.models.project_settings import ProjectSettings
from app.models.company_account import CompanyAccount, cashflow
from app.models.type_service import TypeService

from sqlalchemy import func, and_, or_


class StatisticsService:
    def __init__(self, session: Session):
        self.session = session

    def _print_model_fields(self, model_class):
        """Imprime los campos de un modelo para depuración"""
        for field_name, field in model_class.model_fields.items():
            pass

    def _build_date_filter(self, query, start_date: Optional[date], end_date: Optional[date], date_field):
        """Construye el filtro de fechas para una consulta"""
        if start_date:
            query = query.where(date_field >= start_date)
        if end_date:
            end_of_day = datetime(
                end_date.year, end_date.month, end_date.day, 23, 59, 59)
            query = query.where(date_field <= end_of_day)
        return query

    def _get_base_query(self, model, start_date: Optional[date], end_date: Optional[date], date_field):
        """Construye una consulta base con filtros de fecha"""
        query = select(model)
        return self._build_date_filter(query, start_date, end_date, date_field)

    def get_summary_statistics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        service_type_id: Optional[int] = None,
        driver_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas resumidas del sistema.

        Args:
            start_date: Fecha de inicio para filtrar estadísticas
            end_date: Fecha de fin para filtrar estadísticas
            service_type_id: ID del tipo de servicio para filtrar
            driver_id: ID del conductor para filtrar

        Returns:
            Dict con estadísticas de usuarios, servicios y finanzas
        """
        try:
            response_data = {}

            # --- 1. Estadísticas de Usuarios ---
            # Total de conductores activos
            active_drivers_query = select(func.count(User.id)).select_from(User).join(
                UserHasRole, and_(
                    User.id == UserHasRole.id_user,
                    UserHasRole.id_rol == "DRIVER",
                    UserHasRole.status == RoleStatus.APPROVED
                )
            )
            active_drivers = self.session.exec(
                active_drivers_query).first() or 0

            # Conductores con documentos aprobados
            approved_docs_query = select(func.count(User.id)).select_from(User).join(
                DriverInfo, User.id == DriverInfo.user_id
            ).join(
                DriverDocuments, and_(
                    DriverInfo.id == DriverDocuments.driver_info_id,
                    DriverDocuments.status == DriverStatus.APPROVED
                )
            )
            approved_docs = self.session.exec(
                approved_docs_query).first() or 0

            # Conductores con vehículos registrados
            registered_vehicles_query = select(func.count(User.id)).select_from(User).join(
                DriverInfo, User.id == DriverInfo.user_id
            ).join(
                VehicleInfo, DriverInfo.id == VehicleInfo.driver_info_id
            )
            registered_vehicles = self.session.exec(
                registered_vehicles_query).first() or 0

            response_data["user_stats"] = {
                "active_drivers": active_drivers,
                "approved_docs": approved_docs,
                "registered_vehicles": registered_vehicles
            }

            # Clientes activos únicos
            active_clients_query = select(func.count(func.distinct(
                ClientRequest.id_client))).select_from(ClientRequest)
            active_clients_query = self._build_date_filter(
                active_clients_query, start_date, end_date, ClientRequest.created_at
            )
            if service_type_id:
                active_clients_query = active_clients_query.where(
                    ClientRequest.type_service_id == service_type_id)
            if driver_id:
                active_clients_query = active_clients_query.where(
                    ClientRequest.id_driver_assigned == driver_id)
            active_clients = self.session.exec(
                active_clients_query).first() or 0

            response_data["user_stats"]["active_clients"] = active_clients

            # --- 2. Estadísticas de Servicios ---
            # Convertir driver_id a UUID si existe
            driver_uuid = UUID(driver_id) if driver_id else None

            # Total de servicios completados
            completed_services_query = select(func.count(ClientRequest.id)).select_from(ClientRequest).where(
                ClientRequest.status == StatusEnum.PAID
            )
            if service_type_id:
                completed_services_query = completed_services_query.where(
                    ClientRequest.type_service_id == service_type_id
                )
            if driver_uuid:
                completed_services_query = completed_services_query.where(
                    ClientRequest.id_driver_assigned == driver_uuid
                )
            completed_services_query = self._build_date_filter(
                completed_services_query, start_date, end_date, ClientRequest.created_at)
            completed_services = self.session.exec(
                completed_services_query).first() or 0

            # Servicios cancelados
            cancelled_services_query = select(func.count(ClientRequest.id)).select_from(ClientRequest).where(
                ClientRequest.status == StatusEnum.CANCELLED
            )
            if service_type_id:
                cancelled_services_query = cancelled_services_query.where(
                    ClientRequest.type_service_id == service_type_id
                )
            if driver_uuid:
                cancelled_services_query = cancelled_services_query.where(
                    ClientRequest.id_driver_assigned == driver_uuid
                )
            cancelled_services_query = self._build_date_filter(
                cancelled_services_query, start_date, end_date, ClientRequest.created_at)
            cancelled_services = self.session.exec(
                cancelled_services_query).first() or 0

            # Servicios completados por tipo de servicio
            completed_services_by_type_query = select(
                TypeService.name, func.count(ClientRequest.id))
            completed_services_by_type_query = completed_services_by_type_query.join(
                TypeService, ClientRequest.type_service_id == TypeService.id
            ).where(
                ClientRequest.status == StatusEnum.PAID
            )
            if service_type_id:
                completed_services_by_type_query = completed_services_by_type_query.where(
                    ClientRequest.type_service_id == service_type_id
                )
            if driver_uuid:
                completed_services_by_type_query = completed_services_by_type_query.where(
                    ClientRequest.id_driver_assigned == driver_uuid
                )
            completed_services_by_type_query = self._build_date_filter(
                completed_services_by_type_query, start_date, end_date, ClientRequest.created_at)
            completed_services_by_type_query = completed_services_by_type_query.group_by(
                TypeService.name)
            completed_services_by_type = self.session.exec(
                completed_services_by_type_query).all()

            # Tasa de cancelación
            total_services = completed_services + cancelled_services
            cancellation_rate = (
                cancelled_services / total_services * 100) if total_services > 0 else 0

            response_data["service_stats"] = {
                "completed_services": completed_services,
                "cancelled_services": cancelled_services,
                "cancellation_rate": round(cancellation_rate, 2),
                "completed_by_type": [
                    {"type_name": name, "count": count}
                    for name, count in completed_services_by_type
                ]
            }

            # --- 3. Estadísticas Financieras ---
            # Obtener configuración del proyecto para porcentajes de comisión
            project_settings = self.session.exec(
                select(ProjectSettings)).first()
            company_commission_rate = float(
                project_settings.company) if project_settings and project_settings.company else 0.0

            # Ingresos totales (de la empresa, incluye servicios y adicionales)
            total_income_query = select(func.sum(CompanyAccount.income)).select_from(CompanyAccount).where(
                or_(
                    CompanyAccount.type == cashflow.SERVICE,
                    CompanyAccount.type == cashflow.ADDITIONAL
                )
            )
            total_income_query = self._build_date_filter(
                total_income_query, start_date, end_date, CompanyAccount.date)
            total_income = self.session.exec(total_income_query).first() or 0

            # Comisiones totales (de la empresa, específicamente por servicios)
            total_commission_query = select(func.sum(CompanyAccount.income)).select_from(CompanyAccount).where(
                CompanyAccount.type == cashflow.SERVICE
            )
            total_commission_query = self._build_date_filter(
                total_commission_query, start_date, end_date, CompanyAccount.date)
            total_commission = self.session.exec(
                total_commission_query).first() or 0

            # Retiros totales (gastos de la empresa por retiros de usuarios)
            total_withdrawals_query = select(func.sum(Transaction.expense)).select_from(Transaction).where(
                Transaction.type == TransactionType.WITHDRAWAL
            )
            if driver_uuid:
                total_withdrawals_query = total_withdrawals_query.where(
                    Transaction.user_id == driver_uuid)
            total_withdrawals_query = self._build_date_filter(
                total_withdrawals_query, start_date, end_date, Transaction.date)
            total_withdrawals = self.session.exec(
                total_withdrawals_query).first() or 0

            net_income = total_income - total_withdrawals

            # Ingresos promedio por conductor
            total_driver_gross_income_query = select(func.sum(ClientRequest.fare_assigned)).where(
                ClientRequest.status == StatusEnum.PAID
            )
            if service_type_id:
                total_driver_gross_income_query = total_driver_gross_income_query.where(
                    ClientRequest.type_service_id == service_type_id
                )
            if driver_uuid:
                total_driver_gross_income_query = total_driver_gross_income_query.where(
                    ClientRequest.id_driver_assigned == driver_uuid
                )
            total_driver_gross_income_query = self._build_date_filter(
                total_driver_gross_income_query, start_date, end_date, ClientRequest.updated_at)
            total_driver_gross_income = self.session.exec(
                total_driver_gross_income_query).first() or 0

            # Contar conductores únicos que completaron viajes
            unique_completed_drivers_query = select(func.count(func.distinct(ClientRequest.id_driver_assigned))).where(
                ClientRequest.status == StatusEnum.PAID,
                # Asegurar que hay un conductor asignado
                ClientRequest.id_driver_assigned != None
            )
            if service_type_id:
                unique_completed_drivers_query = unique_completed_drivers_query.where(
                    ClientRequest.type_service_id == service_type_id
                )
            if driver_uuid:
                unique_completed_drivers_query = unique_completed_drivers_query.where(
                    ClientRequest.id_driver_assigned == driver_uuid
                )
            unique_completed_drivers_query = self._build_date_filter(
                unique_completed_drivers_query, start_date, end_date, ClientRequest.updated_at)
            unique_completed_drivers = self.session.exec(
                unique_completed_drivers_query).first() or 0

            average_driver_income = (
                total_driver_gross_income / unique_completed_drivers
            ) if unique_completed_drivers > 0 else 0

            response_data["financial_stats"] = {
                "total_income": total_income,
                "total_commission": total_commission,
                "total_withdrawals": total_withdrawals,
                "net_income": net_income,
                "average_driver_income": round(average_driver_income, 2)
            }

            # --- 4. Estadísticas de Suspensiones ---
            suspended_drivers_stats = self.batch_check_all_suspended_drivers()
            response_data["suspended_drivers_stats"] = suspended_drivers_stats

            return response_data

        except Exception as e:
            raise

    def batch_check_all_suspended_drivers(self):
        """
        Método para verificar y levantar suspensiones de todos los conductores suspendidos.
        Útil para ejecutar como tarea programada (cron job).

        Returns:
            dict: Resumen de las suspensiones levantadas
        """
        # Importar la función desde client_requests_service
        from app.services.client_requests_service import check_and_lift_driver_suspension

        # Obtener todos los conductores suspendidos
        suspended_drivers = self.session.exec(
            select(UserHasRole).where(
                UserHasRole.id_rol == "DRIVER",
                UserHasRole.suspension == True
            )
        ).all()

        lifted_suspensions = []
        still_suspended = []

        for driver in suspended_drivers:
            result = check_and_lift_driver_suspension(
                self.session, driver.id_user)

            if result["success"] and not result.get("is_suspended", True):
                lifted_suspensions.append({
                    "driver_id": str(driver.id_user),
                    "message": result["message"]
                })
            else:
                still_suspended.append({
                    "driver_id": str(driver.id_user),
                    "message": result["message"]
                })

        return {
            "success": True,
            "total_suspended_drivers": len(suspended_drivers),
            "suspensions_lifted": len(lifted_suspensions),
            "still_suspended": len(still_suspended),
            "lifted_details": lifted_suspensions,
            "still_suspended_details": still_suspended
        }
