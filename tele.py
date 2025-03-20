from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater, CallbackQueryHandler, CommandHandler,
    MessageHandler, Filters, ConversationHandler, CallbackContext
)

import requests

import configparser
config = configparser.ConfigParser()
config.read('config.ini')
NOTION_TOKEN = config['DEFAULT']['NOTION_TOKEN']
NOTION_DATABASE_ID = config['DEFAULT']['NOTION_DATABASE_ID']
TELEGRAM_TOKEN = config['DEFAULT']['TELEGRAM_TOKEN']

def add_page_to_notion(nickname,date,text):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"  # 최신 버전으로 업데이트 필요 시 문서 참고
    }
    data = {
        "parent": { "type": "database_id", "database_id": NOTION_DATABASE_ID },
        "properties": {
            "이름/닉네임": {
            "title": [
                {
                    "text": {
                        "content": nickname
                    }
                }
            ]
        },
            
            "날짜":{
                "type": "date",
                "date": { "start": date }
            },
            "일지":{
               "rich_text": [
                {
                    "text": {
                        "content": text
                    }
                }
            ]
            }
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

#print(add_page_to_notion("dㅉ","yanggank"))

WAITING_NICKNAME = 1
WAITING_DATE = 2
WAITING_WRITE = 3

def start(update: Update, context: CallbackContext) -> None:
    # 메인 페이지와 "일지 작성" 버튼
    keyboard = [[InlineKeyboardButton("일지 작성", callback_data='journal')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    sent_message = update.message.reply_text('메인 페이지', reply_markup=reply_markup)
    context.user_data["msg_id"] = sent_message.message_id

def journal_page(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    # 일지 작성 페이지: 닉네임, 날짜, 작성하기 버튼 구성
    # 날짜 버튼은 기본값으로 오늘 날짜 (YYYY-MM-DD)로 설정
    today = datetime.today().strftime("%Y-%m-%d")
    keyboard = [
        [InlineKeyboardButton("닉네임", callback_data='nickname')],
        [InlineKeyboardButton(today, callback_data='date')],
        [InlineKeyboardButton("작성하기", callback_data='write')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(text="일지 작성 페이지", reply_markup=reply_markup)
    # 인라인 키보드 구조를 저장 (나중에 특정 버튼만 업데이트하기 위해)
    context.user_data["keyboard"] = keyboard
    context.user_data["msg_id"] = query.message.message_id

def nickname_callback(update: Update, context: CallbackContext) -> int:
    """'닉네임' 버튼 클릭 시 호출"""
    query = update.callback_query
    query.answer()
    # 인라인 키보드 구조를 저장
    context.user_data['keyboard'] = query.message.reply_markup.inline_keyboard
    # "닉네임을 입력해주세요" 프롬프트 메시지를 보내고, 해당 message_id 저장
    prompt_message = query.message.reply_text("닉네임을 입력해주세요")
    context.user_data['prompt_msg_id'] = prompt_message.message_id
    return WAITING_NICKNAME

def nickname_input(update: Update, context: CallbackContext) -> int:
    # 사용자가 입력한 닉네임
    nickname = update.message.text
    chat_id = update.effective_chat.id
    msg_id = context.user_data.get("msg_id")
    
    # 프롬프트 메시지 삭제 (저장해둔 message_id 사용)
    prompt_msg_id = context.user_data.get("prompt_msg_id")
    if prompt_msg_id:
        context.bot.delete_message(chat_id=chat_id, message_id=prompt_msg_id)
    
    # 사용자가 보낸 닉네임 메시지도 삭제 (원한다면)
    context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
    
    # 저장해둔 기존 키보드를 가져와서 닉네임 버튼만 업데이트
    keyboard = context.user_data.get("keyboard")
    if keyboard and len(keyboard) > 0 and len(keyboard[0]) > 0:
        keyboard[0][0] = InlineKeyboardButton(nickname, callback_data='nickname')
    else:
        # 만약 저장된 키보드가 없다면, 기본 키보드를 새로 구성합니다.
        today = datetime.today().strftime("%Y-%m-%d")
        keyboard = [
            [InlineKeyboardButton(nickname, callback_data='nickname')],
            [InlineKeyboardButton(today, callback_data='date')],
            [InlineKeyboardButton("작성하기", callback_data='write')]
        ]
    new_markup = InlineKeyboardMarkup(keyboard)
    
    # 전체 메시지 업데이트: 텍스트와 인라인 키보드 변경
    context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg_id,
        text="일지 작성 페이지",
        reply_markup=new_markup
    )
    
    return ConversationHandler.END


def date_callback(update: Update, context: CallbackContext) -> int:
    """'날짜' 버튼 클릭 시 호출"""
    query = update.callback_query
    query.answer()
    # 인라인 키보드 구조를 저장
    context.user_data['keyboard'] = query.message.reply_markup.inline_keyboard
    # "닉네임을 입력해주세요" 프롬프트 메시지를 보내고, 해당 message_id 저장
    prompt_message = query.message.reply_text("날짜를 입력해주세요")
    context.user_data['prompt_msg_id'] = prompt_message.message_id
    return WAITING_DATE

def date_input(update: Update, context: CallbackContext) -> int:
    # 사용자가 입력한 닉네임
    new_date = update.message.text
    chat_id = update.effective_chat.id
    msg_id = context.user_data.get("msg_id")
    
    # 프롬프트 메시지 삭제 (저장해둔 message_id 사용)
    prompt_msg_id = context.user_data.get("prompt_msg_id")
    if prompt_msg_id:
        context.bot.delete_message(chat_id=chat_id, message_id=prompt_msg_id)
    
    # 사용자가 보낸 닉네임 메시지도 삭제 (원한다면)
    context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
    
    # 저장해둔 기존 키보드를 가져와서 닉네임 버튼만 업데이트
    keyboard = context.user_data.get("keyboard")
    if keyboard and len(keyboard) > 0 and len(keyboard[1]) > 0:
        keyboard[1][0] = InlineKeyboardButton(new_date, callback_data='date')
    else:
        # 만약 저장된 키보드가 없다면, 기본 키보드를 새로 구성합니다.
        today = datetime.today().strftime("%Y-%m-%d")
        keyboard = [
            [InlineKeyboardButton("닉네임", callback_data='nickname')],
            [InlineKeyboardButton(today, callback_data='date')],
            [InlineKeyboardButton("작성하기", callback_data='write')]
        ]
    new_markup = InlineKeyboardMarkup(keyboard)
    
    # 전체 메시지 업데이트: 텍스트와 인라인 키보드 변경
    context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg_id,
        text="일지 작성 페이지",
        reply_markup=new_markup
    )
    
    return ConversationHandler.END

def write_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    # "작성할 텍스트를 입력해주세요" 프롬프트 전송 후 message_id 저장
    prompt_message = query.message.reply_text("작성할 텍스트를 입력해주세요")
    context.user_data['prompt_msg_id'] = prompt_message.message_id
    return WAITING_WRITE

def write_input(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    chat_id = update.effective_chat.id
    msg_id = context.user_data.get("msg_id")
    # 프롬프트 메시지와 사용자의 텍스트 메시지 삭제
    prompt_msg_id = context.user_data.get("prompt_msg_id")
    if prompt_msg_id:
        context.bot.delete_message(chat_id=chat_id, message_id=prompt_msg_id)
    context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
    
    # 저장된 키보드에서 닉네임과 날짜 버튼의 텍스트 값을 가져옴
    keyboard = context.user_data.get("keyboard")
    if keyboard and len(keyboard) > 1:
        nickname_value = keyboard[0][0].text if len(keyboard[0]) > 0 else "닉네임"
        date_value = keyboard[1][0].text if len(keyboard[1]) > 0 else datetime.today().strftime("%Y-%m-%d")
    else:
        nickname_value = "닉네임"
        date_value = datetime.today().strftime("%Y-%m-%d")
    
    # 저장된 값들과 사용자가 입력한 텍스트를 Notion에 추가하는 함수 호출
    add_page_to_notion(nickname_value, date_value, text)
    
    # 사용자에게 결과를 확인시켜줌
    context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg_id,
        text=f"Notion에 추가되었습니다.\n닉네임: {nickname_value}\n날짜: {date_value}\n내용: {text}",
        reply_markup=None
    )
    
    return ConversationHandler.END

def main() -> None:
    updater = Updater("8164620057:AAGX4Pl1Rc7C5fcElYVnO4ZvGwv9B2L6gTc", use_context=True)
    dispatcher = updater.dispatcher

    conv_handler_nickname = ConversationHandler(
        entry_points=[CallbackQueryHandler(nickname_callback, pattern='^nickname$')],
        states={
            WAITING_NICKNAME: [MessageHandler(Filters.text & ~Filters.command, nickname_input)]
        },
        fallbacks=[]
    )
    conv_handler_date = ConversationHandler(
        entry_points=[CallbackQueryHandler(date_callback, pattern='^date$')],
        states={
            WAITING_DATE: [MessageHandler(Filters.text & ~Filters.command, date_input)]
        },
        fallbacks=[]
    )
    conv_handler_write = ConversationHandler(
        entry_points=[CallbackQueryHandler(write_callback, pattern='^write$')],
        states={
            WAITING_WRITE: [MessageHandler(Filters.text & ~Filters.command, write_input)]
        },
        fallbacks=[]
    )

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CallbackQueryHandler(journal_page, pattern='^journal$'))
    dispatcher.add_handler(conv_handler_nickname)
    dispatcher.add_handler(conv_handler_date)
    dispatcher.add_handler(conv_handler_write)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
