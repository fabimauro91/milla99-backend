from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from app.models.vehicle_type_configuration import VehicleTypeConfiguration, FareCalculationResponse 
import requests


class VehicleTypeConfigurationService:
    def __init__(self, session: Session):
        self.session = session

    def create_vehicle_type_configuration(
        self,
        km_value: float,
        min_value: float,
        tarifa_value: Optional[float] = None,
        weight_value: Optional[float] = None
    ) -> VehicleTypeConfiguration:
        """
        Crea un nuevo registro de VehicleTypeConfiguration
        """ 
        vehicle_type_configuration = VehicleTypeConfiguration(
            km_value=km_value,
            min_value=min_value,
            tarifa_value=tarifa_value,
            weight_value=weight_value
        )
        self.session.add(vehicle_type_configuration)
        self.session.commit()
        self.session.refresh(vehicle_type_configuration)
        return vehicle_type_configuration

    def get_vehicle_type_configuration_by_id(self, id: int) -> Optional[VehicleTypeConfiguration]:
        """
        Busca un registro por ID
        """
        statement = select(VehicleTypeConfiguration).where(VehicleTypeConfiguration.id == id)
        result = self.session.exec(statement).first()
        return result

    def update_vehicle_type_configuration(
        self,
        id_type_vehicle: int,
        update_data: Dict[str, Any]
    ) -> Optional[VehicleTypeConfiguration]:
        """
        Actualiza un registro según los campos proporcionados
        """
        vehicle_type_configuration = self.get_vehicle_type_configuration_by_id(id_type_vehicle)
        if not vehicle_type_configuration:
            return None

        # Actualiza solo los campos proporcionados
        valid_fields = {'km_value', 'min_value', 'tarifa_value', 'weight_value'}
        for field, value in update_data.items():
            if field in valid_fields and value is not None:
                setattr(vehicle_type_configuration, field, value)

        vehicle_type_configuration.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(vehicle_type_configuration)
        return vehicle_type_configuration

    def update_by_vehicle_type_id(self, vehicle_type_id: int, update_data: dict):
        from app.models.vehicle_type_configuration import VehicleTypeConfiguration
        config = self.session.exec(
            select(VehicleTypeConfiguration).where(VehicleTypeConfiguration.vehicle_type_id == vehicle_type_id)
        ).first()
        if not config:
            return None

        valid_fields = {'km_value', 'min_value', 'tarifa_value', 'weight_value'}
        for field, value in update_data.items():
            if field in valid_fields and value is not None:
                setattr(config, field, value)

        config.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(config)
        return config

    def get_google_distance_data(self, origin_lat, origin_lng, destination_lat, destination_lng, api_key):
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": f"{origin_lat},{origin_lng}",
            "destinations": f"{destination_lat},{destination_lng}",
            "units": "metric",
            "key": api_key
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"Error en el API de Google Distance Matrix: {response.status_code}")
        data = response.json()
        if data.get("status") != "OK":
            raise Exception(f"Error en la respuesta del API de Google Distance Matrix: {data.get('status')}")
        return data  

    async def calculate_total_value(self, id: int, google_data: Dict) -> FareCalculationResponse:
        """
        Calcula el valor total basado en los datos de Google y retorna la información necesaria
        """

        
        try:
            # Obtener el registro de tarifas
            vehicle_type_configuration = self.get_vehicle_type_configuration_by_id(id)
            if not vehicle_type_configuration:
                return None

            # Extraer los datos usando el modelo Pydantic
            element = google_data["rows"][0]["elements"][0]

            # Cálculos
            distance_km = element["distance"]["value"] / 1000.0
            time_minutes = element["duration"]["value"] / 60.00

            # Calcular el costo
            distance_cost = distance_km * vehicle_type_configuration.km_value
            time_cost = time_minutes * vehicle_type_configuration.min_value
          
            total_cost = distance_cost + time_cost

            # Aplicar tarifa mínima si existe
            if vehicle_type_configuration.tarifa_value is not None:
                total_cost = max(total_cost, vehicle_type_configuration.tarifa_value)

            return FareCalculationResponse(
                recommended_value=round(total_cost, 2),
                destination_addresses=google_data["destination_addresses"][0],
                origin_addresses=google_data["origin_addresses"][0],
                distance=element["distance"]["text"],
                duration=element["duration"]["text"]
            )

        except Exception as e:
            print(f"Error al calcular el valor total: {str(e)}")
            return None