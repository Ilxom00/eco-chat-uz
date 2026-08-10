from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from . import messages

def get_branch_keyboard(branches: list) -> InlineKeyboardMarkup:
    keyboard = []
    for branch in branches:
        keyboard.append([
            InlineKeyboardButton(branch['name'], callback_data=f"branch:{branch['id']}")
        ])
    return InlineKeyboardMarkup(keyboard)

def get_phone_keyboard() -> ReplyKeyboardMarkup:
    button = KeyboardButton(text=messages.SHARE_PHONE_BUTTON, request_contact=True)
    return ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=messages.BTN_TESTS), KeyboardButton(text=messages.BTN_MY_RESULTS)],
        [KeyboardButton(text=messages.BTN_MY_PROFILE), KeyboardButton(text=messages.BTN_HELP)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_answer_keyboard(answers: list) -> InlineKeyboardMarkup:
    keyboard = []
    labels = ['А', 'Б', 'В', 'Г']
    for idx, answer in enumerate(answers):
        label = labels[idx] if idx < len(labels) else str(idx+1)
        keyboard.append([InlineKeyboardButton(f"{label}) {answer['text']}", callback_data=f"ans:{idx}:{answer['id']}")])
    return InlineKeyboardMarkup(keyboard)

def get_start_test_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(messages.BTN_START_TEST, callback_data="start_test")],
        [InlineKeyboardButton(messages.BTN_BACK, callback_data="back_to_topics")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_seminar_confirm_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(messages.BTN_YES_DONE, callback_data="seminar_yes")],
        [InlineKeyboardButton(messages.BTN_NO_NOT_YET, callback_data="seminar_no")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_topic_list_keyboard(topics: list) -> InlineKeyboardMarkup:
    keyboard = []
    for topic in topics:
        status = topic.get('status', 'locked')
        icon = messages.TOPIC_LOCKED
        callback_data = "ignore"
        if status == 'available':
            icon = messages.TOPIC_AVAILABLE
            callback_data = f"topic:{topic['id']}"
        elif status == 'in_progress':
            icon = messages.TOPIC_IN_PROGRESS
            callback_data = f"topic:{topic['id']}"
        elif status == 'attempt1_done':
            icon = messages.TOPIC_ATTEMPT1_DONE
            callback_data = f"topic:{topic['id']}"
        elif status == 'completed':
            icon = messages.TOPIC_COMPLETED
            callback_data = f"topic:{topic['id']}"
            
        button_text = f"{icon} {topic['name']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    return InlineKeyboardMarkup(keyboard)
