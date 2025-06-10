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

print(f"\nDEBUG: Archivo statistics_service.py cargado desde: {__file__}\n")


class StatisticsService:
    def __init__(self, session: Session):
        self.session = session

    def _print_model_fields(self, model_class):
        """Imprime los campos de un modelo para depuración"""
        print(f"\nCampos de {model_class.__name__}:")
        for field_name, field in model_class.model_fields.items():
            print(f"  {field_name}: {field.annotation}")

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
            print("\n=== Iniciando get_summary_statistics ===")
            print(
                f"Parámetros recibidos: start_date={start_date}, end_date={end_date}, service_type_id={service_type_id}, driver_id={driver_id}")

            # Imprimir estructura de modelos relevantes
            print("\n=== Estructura de Modelos ===")
            try:
                self._print_model_fields(User)
                self._print_model_fields(DriverDocuments)
                self._print_model_fields(UserHasRole)
            except Exception as e:
                print(f"Error al imprimir campos del modelo: {str(e)}")
                print("Continuando con la ejecución...")

            response_data = {}

            # --- 1. Estadísticas de Usuarios ---
            print("\n=== Calculando estadísticas de usuarios ===")

            # Total de conductores activos
            print("\nConsultando conductores activos...")
            active_drivers_query = select(func.count(User.id)).select_from(User).join(
                UserHasRole, and_(
                    User.id == UserHasRole.id_user,
                    UserHasRole.id_rol == "DRIVER",
                    UserHasRole.status == RoleStatus.APPROVED
                )
            )
            print(f"Query conductores activos: {active_drivers_query}")
            active_drivers = self.session.exec(
                active_drivers_query).first() or 0
            print(f"Conductores activos encontrados: {active_drivers}")

            # Conductores con documentos aprobados
            print("\nConsultando documentos aprobados...")
            try:
                # Primero intentamos obtener un documento para ver su estructura
                sample_doc = self.session.exec(
                    select(DriverDocuments).limit(1)).first()
                if sample_doc:
                    print(
                        f"Estructura de documento de muestra: {sample_doc.__dict__}")

                approved_docs_query = select(func.count(User.id)).select_from(User).join(
                    DriverInfo, User.id == DriverInfo.user_id
                ).join(
                    DriverDocuments, and_(
                        DriverInfo.id == DriverDocuments.driver_info_id,
                        DriverDocuments.status == DriverStatus.APPROVED
                    )
                )
                print(f"Query documentos aprobados: {approved_docs_query}")
                approved_docs = self.session.exec(
                    approved_docs_query).first() or 0
                print(f"Documentos aprobados encontrados: {approved_docs}")
            except Exception as e:
                print(f"Error en consulta de documentos: {str(e)}")
                print("Traceback completo:")
                print(traceback.format_exc())
                raise

            # Conductores con vehículos registrados
            print("\nConsultando vehículos registrados...")
            registered_vehicles_query = select(func.count(User.id)).select_from(User).join(
                DriverInfo, User.id == DriverInfo.user_id
            ).join(
                VehicleInfo, DriverInfo.id == VehicleInfo.driver_info_id
            )
            print(f"Query vehículos registrados: {registered_vehicles_query}")
            registered_vehicles = self.session.exec(
                registered_vehicles_query).first() or 0
            print(f"Vehículos registrados encontrados: {registered_vehicles}")

            response_data["user_stats"] = {
                "active_drivers": active_drivers,
                "approved_docs": approved_docs,
                "registered_vehicles": registered_vehicles
            }
            print(
                f"\nEstadísticas de usuarios calculadas: {response_data['user_stats']}")

            # Clientes activos únicos
            print("\nConsultando clientes activos únicos...")
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
            print(f"Query clientes activos únicos: {active_clients_query}")
            active_clients = self.session.exec(
                active_clients_query).first() or 0
            print(f"Clientes activos únicos encontrados: {active_clients}")

            response_data["user_stats"]["active_clients"] = active_clients
            print(
                f"\nEstadísticas de usuarios calculadas (con clientes activos): {response_data['user_stats']}")

            # --- 2. Estadísticas de Servicios ---
            print("\n=== Calculando estadísticas de servicios ===")

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
            print(f"Query servicios completados: {completed_services_query}")
            completed_services = self.session.exec(
                completed_services_query).first() or 0
            print(f"Servicios completados encontrados: {completed_services}")

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
            print(f"Query servicios cancelados: {cancelled_services_query}")
            cancelled_services = self.session.exec(
                cancelled_services_query).first() or 0
            print(f"Servicios cancelados encontrados: {cancelled_services}")

            # Servicios completados por tipo de servicio
            print("\nConsultando servicios completados por tipo de servicio...")
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
            print(
                f"Query servicios completados por tipo: {completed_services_by_type_query}")
            completed_services_by_type = self.session.exec(
                completed_services_by_type_query).all()
            print(
                f"Servicios completados por tipo encontrados: {completed_services_by_type}")

            # Tasa de cancelación
            total_services = completed_services + cancelled_services
            cancellation_rate = (
                cancelled_services / total_services * 100) if total_services > 0 else 0
            print(f"Tasa de cancelación calculada: {cancellation_rate}%")

            response_data["service_stats"] = {
                "completed_services": completed_services,
                "cancelled_services": cancelled_services,
                "cancellation_rate": round(cancellation_rate, 2),
                "completed_by_type": [
                    {"type_name": name, "count": count}
                    for name, count in completed_services_by_type
                ]
            }
            print(
                f"\nEstadísticas de servicios calculadas: {response_data['service_stats']}")

            # --- 3. Estadísticas Financieras ---
            print("\n=== Calculando estadísticas financieras ===")

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
            print(f"Query ingresos totales: {total_income_query}")
            total_income = self.session.exec(total_income_query).first() or 0
            print(f"Ingresos totales encontrados: {total_income}")

            # Comisiones totales (de la empresa, específicamente por servicios)
            total_commission_query = select(func.sum(CompanyAccount.income)).select_from(CompanyAccount).where(
                CompanyAccount.type == cashflow.SERVICE
            )
            total_commission_query = self._build_date_filter(
                total_commission_query, start_date, end_date, CompanyAccount.date)
            print(f"Query comisiones totales: {total_commission_query}")
            total_commission = self.session.exec(
                total_commission_query).first() or 0
            print(f"Comisiones totales encontradas: {total_commission}")

            # Retiros totales (gastos de la empresa por retiros de usuarios)
            total_withdrawals_query = select(func.sum(Transaction.expense)).select_from(Transaction).where(
                Transaction.type == TransactionType.WITHDRAWAL
            )
            if driver_uuid:
                total_withdrawals_query = total_withdrawals_query.where(
                    Transaction.user_id == driver_uuid)
            total_withdrawals_query = self._build_date_filter(
                total_withdrawals_query, start_date, end_date, Transaction.date)
            print(f"Query retiros totales: {total_withdrawals_query}")
            total_withdrawals = self.session.exec(
                total_withdrawals_query).first() or 0
            print(f"Retiros totales encontrados: {total_withdrawals}")

            net_income = total_income - total_withdrawals
            print(f"Ingresos netos calculados: {net_income}")

            # Ingresos promedio por conductor
            print("\nCalculando ingresos promedio por conductor...")
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
            print(
                f"Query ingresos brutos de conductor: {total_driver_gross_income_query}")
            total_driver_gross_income = self.session.exec(
                total_driver_gross_income_query).first() or 0
            print(
                f"Ingresos brutos de conductor encontrados: {total_driver_gross_income}")

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
            print(
                f"Query conductores únicos con viajes completados: {unique_completed_drivers_query}")
            unique_completed_drivers = self.session.exec(
                unique_completed_drivers_query).first() or 0
            print(
                f"Conductores únicos con viajes completados encontrados: {unique_completed_drivers}")

            average_driver_income = (
                total_driver_gross_income / unique_completed_drivers
            ) if unique_completed_drivers > 0 else 0
            print(
                f"Ingresos promedio por conductor calculados: {average_driver_income}")

            response_data["financial_stats"] = {
                "total_income": total_income,
                "total_commission": total_commission,
                "total_withdrawals": total_withdrawals,
                "net_income": net_income,
                "average_driver_income": round(average_driver_income, 2)
            }
            print(
                f"\nEstadísticas financieras calculadas: {response_data['financial_stats']}")

            return response_data

        except Exception as e:
            print(f"\nError en get_summary_statistics: {str(e)}")
            print("Traceback completo:")
            print(traceback.format_exc())
            raise
