from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from app.models.time_distance_value import TimeDistanceValue,GoogleData, FareCalculationResponse 


class TimeDistanceValueService:
    def __init__(self, session: Session):
        self.session = session

    def create_time_distance_value(
        self,
        km_value: float,
        min_value: float,
        tarifa_value: Optional[float] = None,
        weight_value: Optional[float] = None
    ) -> TimeDistanceValue:
        """
        Crea un nuevo registro de TimeDistanceValue
        """
        time_distance_value = TimeDistanceValue(
            km_value=km_value,
            min_value=min_value,
            tarifa_value=tarifa_value,
            weight_value=weight_value
        )
        self.session.add(time_distance_value)
        self.session.commit()
        self.session.refresh(time_distance_value)
        return time_distance_value

    def get_time_distance_value_by_id(self, id: int) -> Optional[TimeDistanceValue]:
        """
        Busca un registro por ID
        """
        statement = select(TimeDistanceValue).where(TimeDistanceValue.id == id)
        result = self.session.exec(statement).first()
        return result

    def update_time_distance_value(
        self,
        id: int,
        update_data: Dict[str, Any]
    ) -> Optional[TimeDistanceValue]:
        """
        Actualiza un registro según los campos proporcionados
        """
        time_distance_value = self.get_time_distance_value_by_id(id)
        if not time_distance_value:
            return None

        # Actualiza solo los campos proporcionados
        valid_fields = {'km_value', 'min_value', 'tarifa_value', 'weight_value'}
        for field, value in update_data.items():
            if field in valid_fields and value is not None:
                setattr(time_distance_value, field, value)

        time_distance_value.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(time_distance_value)
        return time_distance_value



    
    def get_time_distance_value_by_id(self, id: int):
        # Asumiendo que tienes un modelo SQLAlchemy para esto
        return self.Session.query(TimeDistanceValue).filter(TimeDistanceValue.id == id).first()



    def calculate_total_value(self, id: int, google_data: Dict) -> FareCalculationResponse:
        """
        Calcula el valor total basado en los datos de Google y retorna la información necesaria
        """
        try:
            # Obtener el registro de tarifas
            time_distance_value = self.get_time_distance_value_by_id(id)
            if not time_distance_value:
                return None

            # Extraer los datos usando el modelo Pydantic
            element = google_data["rows"][0]["elements"][0]

            # Cálculos
            distance_km = element["distance"]["value"] / 1000.0
            time_minutes = element["duration"]["value"] / 60.00

            # Calcular el costo
            distance_cost = distance_km * time_distance_value.km_value
            time_cost = time_minutes * time_distance_value.min_value
            total_cost = distance_cost + time_cost

            # Aplicar tarifa mínima si existe
            if time_distance_value.tarifa_value is not None:
                total_cost = max(total_cost, time_distance_value.tarifa_value)

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