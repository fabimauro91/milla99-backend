import socketio
import json
from datetime import datetime

# Configura Redis como message manager
mgr = socketio.AsyncRedisManager('redis://localhost:6379/0')
# sio = socketio.AsyncServer(
#     async_mode='asgi',
#     client_manager=mgr,
#     cors_allowed_origins='*'
# )
sio = socketio.AsyncServer(async_mode='asgi')

@sio.event
async def connect(sid, environ):
    print(f'Cliente conectado: {sid}')


@sio.event
async def disconnect(sid):
    print(f'Cliente desconectado: {sid}')
    await sio.emit( 'driver_disconnected',{'id_socket':sid})

@sio.event
async def message(sid, data):
    print(f'Datos del cliente en socket: {sid}: {data}')
    await sio.emit(
        'new_message',
        data,
        to=sid
    )

@sio.event
async def change_driver_position(sid, data):
    # Si data es string, conviértelo a dict
    if isinstance(data, str):
        data = json.loads(data)
    print(f'Emitio nueva posicion en socket: {sid}: {data}')
    await sio.emit(
        'new_driver_position',
        {
            'id_socket': sid,
            'id': data['id'],
            'lat': data['lat'],
            'lng': data['lng']
        }
    ) 

@sio.event
async def new_client_request(sid, data):
    # Si data es string, conviértelo a dict
    if isinstance(data, str):
        data = json.loads(data)
    print(f'El cliente emitio una nueva solicitud de servicio en socket: {sid}: {data}')
    await sio.emit(
        'created_client_request',
        {
            'id_socket': sid,
            'id_client_request': data['id_client_request'],
        }
    ) 

@sio.event
async def new_driver_offer(sid, data):
    # Si data es string, conviértelo a dict
    if isinstance(data, str):
        data = json.loads(data)
    print(f'El conductor emitio una nueva oferta de servicio en socket: {sid}: {data}')
    await sio.emit(
        f'created_driver_offer/{data["id_client_request"]}',
        {
            'id_socket': sid
        }
    ) 

@sio.event
async def new_driver_assigned(sid, data):
    # Si data es string, conviértelo a dict
    if isinstance(data, str):
        data = json.loads(data)
    print(f'El cliente emitio una nueva asignacion de conductor en socket: {sid}: {data}')
    await sio.emit(
        f'driver_assigned/{data["id_driver"]}',
        {
            'id_socket': sid,
            "id_client_request": data["id_client_request"]
        }
    ) 

@sio.event
async def trip_change_driver_position(sid, data):
    # Si data es string, conviértelo a dict
    if isinstance(data, str):
        data = json.loads(data)
    print(f'El conductor actualizo su posicion en el socket: {sid}: {data}')
    await sio.emit(
        f'trip_new_driver_position/{data["id_client"]}',
        {
            'id_socket': sid,
            'lat': data['lat'],
            'lng': data['lng']
        }
    ) 

@sio.event
async def update_status_trip(sid, data):
    # Si data es string, conviértelo a dict
    if isinstance(data, str):
        data = json.loads(data)
    print(f'Se actualizo el estado de la viaje en el socket: {sid}: {data}')
    await sio.emit(
        f'new_status_trip/{data["id_client_request"]}',
        {
            'id_socket': sid,
            'status': data['status'],
            'id_client_request': data['id_client_request']
        }
    ) 

@sio.event
async def client_to_driver_message(sid, data):
    # Si data es string, conviértelo a dict
    if isinstance(data, str):
        data = json.loads(data)
    print(f'Mensaje del cliente al conductor: {sid}: {data}')
    # Emitir el mensaje al conductor específico
    await sio.emit(
        f'client_message/{data["id_driver"]}',
        {
            'id_socket': sid,
            'message': data['message'],
            'client_id': data['client_id'],
            'client_name': data['client_name'],
            'id_client_request': data['id_client_request'],
            'timestamp': datetime.utcnow().isoformat()
        }
    )

@sio.event
async def driver_to_client_message(sid, data):
    # Si data es string, conviértelo a dict
    if isinstance(data, str):
        data = json.loads(data)
    print(f'Mensaje del conductor al cliente: {sid}: {data}')
    # Emitir el mensaje al cliente específico
    await sio.emit(
        f'driver_message/{data["id_client"]}',
        {
            'id_socket': sid,
            'message': data['message'],
            'driver_id': data['driver_id'],
            'driver_name': data['driver_name'],
            'id_client_request': data['id_client_request'],
            'timestamp': datetime.utcnow().isoformat()
        }
    )

