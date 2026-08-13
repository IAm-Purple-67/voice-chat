import asyncio
import json
import uuid
from websockets.server import serve
from aiohttp import web
import os

# اتاق‌های عمومی (همه گروه‌ها)
ROOMS = {
    "گروه ۱: گفتگوی آزاد": [],
    "گروه ۲: موسیقی": [],
    "گروه ۳: فیلم و سریال": [],
    "گروه ۴: برنامه‌نویسی": [],
    "گروه ۵: ورزش": [],
}

# نگهداری کاربران متصل در هر اتاق
clients = {}  # {room_name: [websocket, ...]}

async def websocket_handler(websocket, path):
    """مدیریت اتصال WebSocket هر کاربر"""
    room_name = None
    user_id = str(uuid.uuid4())[:8]
    
    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")
            
            if action == "join_room":
                room_name = data.get("room")
                if room_name not in ROOMS:
                    room_name = None
                    continue
                
                # اضافه کردن کاربر به اتاق
                if room_name not in clients:
                    clients[room_name] = []
                clients[room_name].append(websocket)
                
                # اطلاع‌رسانی به بقیه کاربران اتاق
                await broadcast_to_room(room_name, {
                    "type": "user_joined",
                    "user_id": user_id,
                    "message": f"کاربر {user_id} وارد شد"
                })
                
                # ارسال لیست کاربران فعلی به فرد جدید
                await websocket.send(json.dumps({
                    "type": "room_users",
                    "users": [{"id": "user1"}, {"id": "user2"}],  # ساده‌سازی
                    "room": room_name
                }))
            
            elif action == "signal":
                # ارسال سیگنال WebRTC به سایر کاربران اتاق
                target = data.get("target")
                signal_data = data.get("data")
                
                # پیدا کردن کاربر هدف و ارسال سیگنال
                if room_name and room_name in clients:
                    for client in clients[room_name]:
                        if client != websocket:
                            try:
                                await client.send(json.dumps({
                                    "type": "signal",
                                    "from": user_id,
                                    "data": signal_data
                                }))
                            except:
                                pass
            
            elif action == "leave":
                # خروج از اتاق
                if room_name and room_name in clients:
                    if websocket in clients[room_name]:
                        clients[room_name].remove(websocket)
                    await broadcast_to_room(room_name, {
                        "type": "user_left",
                        "user_id": user_id,
                        "message": f"کاربر {user_id} خارج شد"
                    })
                break
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # پاک‌سازی هنگام خروج
        if room_name and room_name in clients:
            if websocket in clients[room_name]:
                clients[room_name].remove(websocket)
            await broadcast_to_room(room_name, {
                "type": "user_left",
                "user_id": user_id,
                "message": f"کاربر {user_id} خارج شد"
            })

async def broadcast_to_room(room_name, message):
    """ارسال پیام به همه‌ی کاربران یک اتاق"""
    if room_name in clients:
        for client in clients[room_name]:
            try:
                await client.send(json.dumps(message))
            except:
                pass

# ========== بخش HTTP (صفحه وب) ==========

async def index(request):
    """صفحه اصلی سایت"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return web.Response(text=html, content_type="text/html")

async def websocket_endpoint(request):
    """مسیر WebSocket برای اتصال"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    # اینجا می‌تونیم WebSocket رو مدیریت کنیم (فعلاً از websockets استفاده می‌کنیم)
    return ws

# ========== اجرای اصلی ==========

async def main():
    # راه‌اندازی سرور HTTP برای صفحه وب
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_get('/ws', websocket_endpoint)
    
    # اجرای همزمان HTTP و WebSocket
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=8000)
    await site.start()
    
    print("✅ سرور روی http://localhost:8000 اجرا شد")
    print(f"📡 اتاق‌های موجود: {', '.join(ROOMS.keys())}")
    
    # راه‌اندازی WebSocket روی پورت 8765
    async with serve(websocket_handler, "0.0.0.0", 8765):
        await asyncio.Future()  # اجرا تا بینهایت

if __name__ == "__main__":
    asyncio.run(main())
