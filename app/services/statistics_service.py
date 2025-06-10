from sqlmodel import Session, select
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

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

from sqlalchemy import func, and_


class StatisticsService:
    def __init__(self, session: Session):
        self.session = session

    def get_summary_statistics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        service_type_id: Optional[int] = None,
        driver_id: Optional[str] = None  # Cambiado a str para UUIDs
    ) -> Dict[str, Any]:
        """
        Obtiene un resumen de estadísticas administrativas.
        """
        response_data = {
            "period_summary": {},
            "service_stats": {},
            "financial_stats": {},
            "effectiveness_stats": {},
            "driver_specific_stats": []
        }

        # --- 1. Resumen del Período ---
        if start_date:
            response_data["period_summary"]["start_date"] = start_date.isoformat()
        if end_date:
            response_data["period_summary"]["end_date"] = end_date.isoformat()

        # Calcular total_days si ambas fechas están presentes
        if start_date and end_date:
            response_data["period_summary"]["total_days"] = (
                end_date - start_date).days + 1
        elif start_date or end_date:
            # Si solo una fecha es provista, no se puede calcular un rango de días coherente
            response_data["period_summary"]["total_days"] = None

        # --- 2. Estadísticas de Servicios ---
        base_query_services = select(ClientRequest)

        # Aplicar filtros de fecha a servicios
        if start_date:
            base_query_services = base_query_services.where(
                ClientRequest.created_at >= start_date)
        if end_date:
            # end_date se considera hasta el final del día
            end_of_day = datetime(
                end_date.year, end_date.month, end_date.day, 23, 59, 59)
            base_query_services = base_query_services.where(
                ClientRequest.created_at <= end_of_day)

        # Aplicar filtro por tipo de servicio a servicios
        if service_type_id:
            base_query_services = base_query_services.where(
                ClientRequest.type_service_id == service_type_id)

        # Aplicar filtro por conductor a servicios
        if driver_id:
            base_query_services = base_query_services.where(
                ClientRequest.id_driver_assigned == UUID(driver_id))

        # Contar total de solicitudes
        total_requests = self.session.exec(base_query_services.select(
            func.count(ClientRequest.id))).first() or 0

        # Contar servicios por estado
        completed_services = self.session.exec(base_query_services.where(
            ClientRequest.status == StatusEnum.COMPLETED).select(func.count(ClientRequest.id))).first() or 0
        cancelled_services = self.session.exec(base_query_services.where(
            ClientRequest.status == StatusEnum.CANCELLED).select(func.count(ClientRequest.id))).first() or 0
        in_progress_services = self.session.exec(base_query_services.where(
            and_(
                ClientRequest.status != StatusEnum.COMPLETED,
                ClientRequest.status != StatusEnum.CANCELLED,
                ClientRequest.status != StatusEnum.REJECTED
            )).select(func.count(ClientRequest.id))).first() or 0

        # Calcular porcentajes
        completed_percentage = (
            completed_services / total_requests * 100) if total_requests > 0 else 0.0
        cancellation_rate = (
            cancelled_services / total_requests * 100) if total_requests > 0 else 0.0

        response_data["service_stats"] = {
            "total_requests": total_requests,
            "completed_services": completed_services,
            "cancelled_services": cancelled_services,
            "in_progress_services": in_progress_services,
            "completed_percentage": round(completed_percentage, 2),
            "cancellation_rate": round(cancellation_rate, 2)
        }

        # --- 3. Estadísticas Financieras ---
        # Obtener configuración del proyecto para porcentajes de comisión
        project_settings = self.session.exec(select(ProjectSettings)).first()
        company_commission_rate = float(
            project_settings.company) if project_settings and project_settings.company else 0.0

        base_query_transactions = select(Transaction)
        base_query_withdrawals = select(Withdrawal)

        # Aplicar filtros de fecha a transacciones y retiros
        if start_date:
            base_query_transactions = base_query_transactions.where(
                Transaction.date >= start_date)
            base_query_withdrawals = base_query_withdrawals.where(
                Withdrawal.created_at >= start_date)
        if end_date:
            end_of_day_trans = datetime(
                end_date.year, end_date.month, end_date.day, 23, 59, 59) if end_date else None
            if end_of_day_trans:
                base_query_transactions = base_query_transactions.where(
                    Transaction.date <= end_of_day_trans)
                base_query_withdrawals = base_query_withdrawals.where(
                    Withdrawal.created_at <= end_of_day_trans)

        # Aplicar filtro por conductor a transacciones y retiros
        if driver_id:
            # Para transacciones relacionadas con el conductor (ej. bonos, retiros, comisiones)
            base_query_transactions = base_query_transactions.where(
                Transaction.user_id == UUID(driver_id))
            # Para retiros realizados por el conductor
            base_query_withdrawals = base_query_withdrawals.where(
                Withdrawal.user_id == UUID(driver_id))

        # Total de ingresos de servicios (monto final pagado por el cliente)
        total_income_from_services = self.session.exec(
            base_query_services.where(
                ClientRequest.status == StatusEnum.COMPLETED)
            .select(func.sum(ClientRequest.final_amount))
        ).first() or 0.0

        # Total de gastos (egresos) y bonificaciones
        total_expenses = self.session.exec(
            base_query_transactions.where(Transaction.expense > 0)
            .select(func.sum(Transaction.expense))
        ).first() or 0.0

        # Total de retiros procesados (aprobados)
        total_withdrawals_processed = self.session.exec(
            base_query_withdrawals.where(
                Withdrawal.status == WithdrawalStatus.APPROVED)
            .select(func.sum(Withdrawal.amount))
        ).first() or 0.0

        # Ganancias netas de la empresa (ingresos por comisión - gastos de la empresa)
        company_gross_commission = total_income_from_services * company_commission_rate
        # Asumiendo que los gastos registrados en Transaction son relevantes para la empresa
        # Podríamos necesitar más granularidad si hay gastos de conductor vs. empresa
        company_net_earnings = company_gross_commission - total_expenses

        # Ahorros acumulados de los conductores
        # Este no se filtra por fecha porque los ahorros son acumulativos
        total_driver_savings_query = select(func.sum(DriverSavings.amount))
        if driver_id:  # Si se filtra por conductor, solo sus ahorros
            total_driver_savings_query = total_driver_savings_query.where(
                DriverSavings.user_id == UUID(driver_id))
        total_driver_savings = self.session.exec(
            total_driver_savings_query).first() or 0.0

        response_data["financial_stats"] = {
            "total_income_from_services": round(total_income_from_services, 2),
            "total_expenses_bonuses": round(total_expenses, 2),
            "total_withdrawals_processed": round(total_withdrawals_processed, 2),
            "company_net_earnings": round(company_net_earnings, 2),
            "driver_savings_accumulated": round(total_driver_savings, 2)
        }

        # --- 4. Estadísticas de Efectividad ---
        # Tiempo promedio de aceptación de solicitudes (desde created_at hasta accepted_at)
        # Solo para solicitudes que fueron aceptadas
        accepted_requests_query = base_query_services.where(
            ClientRequest.status == StatusEnum.ACCEPTED_BY_DRIVER
        )

        # Calcular la diferencia en segundos y luego en minutos
        avg_time_to_accept_sec = self.session.exec(
            accepted_requests_query.select(
                func.avg(func.timestampdiff(
                    func.second, ClientRequest.created_at, ClientRequest.accepted_at))
            )
        ).first() or 0.0
        avg_time_to_accept_minutes = avg_time_to_accept_sec / 60.0

        # Tiempo promedio de finalización de servicios (desde accepted_at hasta completed_at)
        # Solo para solicitudes completadas
        completed_requests_query = base_query_services.where(
            ClientRequest.status == StatusEnum.COMPLETED
        )

        avg_completion_time_sec = self.session.exec(
            completed_requests_query.select(
                func.avg(func.timestampdiff(
                    func.second, ClientRequest.accepted_at, ClientRequest.completed_at))
            )
        ).first() or 0.0
        avg_completion_time_minutes = avg_completion_time_sec / 60.0

        # Tasa de actividad de conductores (conductores que han completado al menos 1 viaje en el período)
        active_drivers_in_period = self.session.exec(
            base_query_services.where(
                ClientRequest.status == StatusEnum.COMPLETED)
            .select(func.count(ClientRequest.id_driver_assigned.distinct()))
        ).first() or 0

        total_drivers = self.session.exec(
            select(func.count(UserHasRole.id_user.distinct()))
            .where(UserHasRole.id_rol == "DRIVER")
        ).first() or 0

        driver_activity_rate_percentage = (
            active_drivers_in_period / total_drivers * 100) if total_drivers > 0 else 0.0

        response_data["effectiveness_stats"] = {
            "avg_time_to_accept_request_minutes": round(avg_time_to_accept_minutes, 2),
            "avg_completion_time_minutes": round(avg_completion_time_minutes, 2),
            "driver_activity_rate": {
                "active_drivers_in_period": active_drivers_in_period,
                "total_drivers": total_drivers,
                "activity_percentage": round(driver_activity_rate_percentage, 2)
            }
        }

        # --- 5. Estadísticas Específicas del Conductor (si se proporciona driver_id) ---
        if driver_id:
            driver_uuid = UUID(driver_id)

            # Viajes completados por este conductor
            driver_completed_trips = self.session.exec(
                base_query_services.where(
                    and_(
                        ClientRequest.id_driver_assigned == driver_uuid,
                        ClientRequest.status == StatusEnum.COMPLETED
                    )
                ).select(func.count(ClientRequest.id))
            ).first() or 0

            # Viajes cancelados por este conductor (asumimos que el driver_id también está en cancelados)
            driver_cancelled_trips = self.session.exec(
                base_query_services.where(
                    and_(
                        ClientRequest.id_driver_assigned == driver_uuid,
                        ClientRequest.status == StatusEnum.CANCELLED
                    )
                ).select(func.count(ClientRequest.id))
            ).first() or 0

            # Ganancias totales del conductor (ingresos por servicios + bonos - gastos/retiros)
            # Incluimos solo transacciones asociadas a servicios completados o bonificaciones directamente
            driver_total_income_from_services = self.session.exec(
                select(func.sum(Transaction.income))
                .where(
                    and_(
                        Transaction.user_id == driver_uuid,
                        # O cualquier otro tipo que represente ganancia para el conductor
                        Transaction.type.in_(
                            [TransactionType.SERVICE, TransactionType.BONUS])
                    )
                )
            ).first() or 0.0

            driver_total_expense_from_services = self.session.exec(
                select(func.sum(Transaction.expense))
                .where(
                    and_(
                        Transaction.user_id == driver_uuid,
                        # O cualquier otro tipo que represente gasto para el conductor
                        Transaction.type.in_(
                            [TransactionType.WITHDRAWAL, TransactionType.SERVICE_FEE])
                    )
                )
            ).first() or 0.0

            driver_total_earnings = driver_total_income_from_services - \
                driver_total_expense_from_services

            # Obtener nombre del conductor
            driver_user_info = self.session.exec(
                select(User).where(User.id == driver_uuid)).first()
            driver_name = driver_user_info.full_name if driver_user_info else "Desconocido"

            response_data["driver_specific_stats"].append({
                "driver_id": driver_id,
                "driver_name": driver_name,
                "completed_trips": driver_completed_trips,
                "cancelled_trips_by_driver": driver_cancelled_trips,
                "total_earnings": round(driver_total_earnings, 2)
            })

        return response_data
