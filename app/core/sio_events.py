import socketio
import json

# Configura Redis como message manager
# mgr = socketio.AsyncRedisManager('redis://localhost:6379/0')
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