from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest, DeleteMessagesRequest
from telethon.tl.types import Channel
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

# Загружаем данные из .env
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone_number = os.getenv('PHONE_NUMBER')

client = TelegramClient('classic_session', api_id, api_hash)


async def get_recent_chats(limit=200):
    """Получает список последних чатов и возвращает список кортежей (index, dialog)"""
    await client.start(phone=phone_number)
    all_dialogs = await client.get_dialogs(limit=limit)
    
    # Фильтруем: исключаем каналы, но оставляем форумы и группы
    dialogs = [d for d in all_dialogs if not d.is_channel or (d.is_channel and (getattr(d, 'forum', False) or d.is_group))]
    
    print("\n📋 Последние чаты:")
    print("=" * 60)
    for idx, dialog in enumerate(dialogs, 1):
        is_forum = getattr(dialog, 'forum', False)
        if is_forum:
            dialog_type = "💬"
        elif dialog.is_group:
            dialog_type = "👥"
        else:
            dialog_type = "💬"
        print(f"{idx}. {dialog_type} {dialog.name} (ID: {dialog.id})")
    print("0. ❌ Выход")
    print("=" * 60)
    
    return dialogs


def select_chat(dialogs):
    """Интерактивный выбор чата"""
    while True:
        try:
            choice = input("\nВведите номер чата для удаления сообщений: ").strip()
            choice = int(choice)
            
            if choice == 0:
                print("Выход из программы.")
                return None
            
            if 1 <= choice <= len(dialogs):
                selected_dialog = dialogs[choice - 1]
                print(f"\nВыбрано: {selected_dialog.name}")
                return selected_dialog.id
            else:
                print(f"❌ Некорректный номер. Введите число от 1 до {len(dialogs)} или 0 для выхода.")
        except ValueError:
            print("❌ Введите корректное число.")
        except KeyboardInterrupt:
            print("\n\nВыход из программы.")
            return None


async def delete_own_messages(chat):
    entity = await client.get_entity(chat)
    my_id = (await client.get_me()).id
    
    # Проверяем, является ли это форумом (группой с топиками)
    is_forum = isinstance(entity, Channel) and getattr(entity, 'forum', False)
    
    if is_forum:
        # Для форумных групп удаляем сообщения по одному
        print("💬 Обработка форумной группы...")
        total_deleted = 0
        async for message in client.iter_messages(entity):
            if message.from_id and getattr(message.from_id, 'user_id', None) == my_id:
                try:
                    await message.delete(revoke=True)
                    total_deleted += 1
                    if total_deleted % 10 == 0:
                        print(f"🗑️ Удалено {total_deleted} сообщений...")
                except Exception as e:
                    print(f"❌ Ошибка при удалении сообщения {message.id}: {e}")
    else:
        # Для обычных чатов/каналов используем массовое удаление
        total_deleted = 0
        offset_id = 0
        
        while True:
            history = await client(GetHistoryRequest(
                peer=entity,
                offset_id=offset_id,
                offset_date=None,
                add_offset=0,
                limit=100,
                max_id=0,
                min_id=0,
                hash=0
            ))
            
            messages = history.messages
            if not messages:
                break
            
            own_msg_ids = [
                msg.id for msg in messages 
                if msg.from_id and getattr(msg.from_id, 'user_id', None) == my_id
            ]
            
            if own_msg_ids:
                try:
                    await client(DeleteMessagesRequest(id=own_msg_ids, revoke=True))
                    total_deleted += len(own_msg_ids)
                    print(f"🗑️ Удалено {len(own_msg_ids)} сообщений (всего: {total_deleted})")
                except Exception as e:
                    print(f"❌ Ошибка при удалении батча: {e}")
            
            offset_id = messages[-1].id
    
    print(f"✅ Готово. Всего удалено: {total_deleted} сообщений.")


async def main():
    """Главная функция"""
    # Этап 1: Получить список чатов и выбрать
    dialogs = await get_recent_chats()
    selected_chat_id = select_chat(dialogs)
    
    if selected_chat_id is None:
        return
    
    # Этап 2: Удалить сообщения
    await delete_own_messages(selected_chat_id)


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())