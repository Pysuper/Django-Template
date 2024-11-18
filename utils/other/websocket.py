import json
from datetime import datetime


async def websocket_application(scope: dict, receive: callable, send: callable) -> None:
    """
    WebSocket 应用程序主入口：处理客户端连接、断开和消息接收

    :param scope: 包含连接信息的字典。
    :param receive: 用于接收事件的异步函数。
    :param send: 用于发送事件的异步函数。
    """
    # 初始化连接状态
    connection_id = scope.get("client", [""])[0]
    is_connected = False

    try:
        while True:
            # 等待接收客户端事件
            event = await receive()
            event_type = event["type"]

            # 处理 WebSocket 连接事件
            if event_type == "websocket.connect":
                # 建立连接并保存连接状态
                is_connected = True
                await send({"type": "websocket.accept"})
                # 发送欢迎消息
                await send({"type": "websocket.send", "text": f"欢迎连接! 您的连接ID是: {connection_id}"})

            # 处理 WebSocket 断开事件
            elif event_type == "websocket.disconnect":
                # 清理连接状态
                is_connected = False
                # 记录连接断开
                print(f"客户端 {connection_id} 已断开连接")
                break

            # 处理 WebSocket 消息接收事件
            elif event_type == "websocket.receive":
                message = event.get("text", "")

                # 心跳检测
                if message == "ping":
                    await send({"type": "websocket.send", "text": "pong!"})

                # 处理JSON消息
                elif message.startswith("{"):
                    try:
                        data = json.loads(message)
                        # 根据消息类型处理不同业务逻辑
                        msg_type = data.get("type")
                        if msg_type == "chat":
                            # 处理聊天消息
                            await handle_chat_message(data, send)
                        elif msg_type == "notification":
                            # 处理通知消息
                            await handle_notification(data, send)
                    except json.JSONDecodeError:
                        await send({"type": "websocket.send", "text": "消息格式错误，请发送正确的JSON格式"})

                # 处理其他文本消息
                else:
                    await send({"type": "websocket.send", "text": f"收到消息: {message}"})

    except Exception as e:
        # 异常处理和日志记录
        error_msg = f"WebSocket错误 [客户端 {connection_id}]: {str(e)}"
        print(error_msg)
        if is_connected:
            await send({"type": "websocket.send", "text": "服务器发生错误，请稍后重试"})


async def handle_chat_message(data: dict, send: callable) -> None:
    """处理聊天消息"""
    content = data.get("content", "")
    sender = data.get("sender", "匿名用户")
    await send(
        {
            "type": "websocket.send",
            "text": json.dumps(
                {"type": "chat", "sender": sender, "content": content, "timestamp": datetime.now().isoformat()}
            ),
        }
    )


async def handle_notification(data: dict, send: callable) -> None:
    """处理通知消息"""
    notification_type = data.get("notification_type", "")
    message = data.get("message", "")
    await send(
        {
            "type": "websocket.send",
            "text": json.dumps(
                {
                    "type": "notification",
                    "notification_type": notification_type,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                }
            ),
        }
    )
