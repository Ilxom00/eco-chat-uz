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
    """
    Build answer keyboard. Each answer on its own row.
    Long answer text is split into multiple lines within the button.
    Telegram supports multi-line button text natively.
    """
    keyboard = []
    labels = ['А', 'Б', 'В', 'Г']
    for idx, answer in enumerate(answers):
        label = labels[idx] if idx < len(labels) else str(idx + 1)
        text = answer.get('text', '')
        display_order = answer.get('display_order', idx + 1)
        # Telegram buttons support up to ~200 chars; wrap long text with newlines
        btn_text = f"{label}) {text}"
        # Split very long text into readable chunks at word boundaries
        if len(btn_text) > 60:
            words = btn_text.split(' ')
            lines = []
            current_line = ''
            for word in words:
                if len(current_line) + len(word) + 1 <= 60:
                    current_line = (current_line + ' ' + word).strip()
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            btn_text = '\n'.join(lines)
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"ans:{idx+1}:{answer['id']}")])
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
        button_text = f"📝 {topic.get('name', 'Мавзу')}"
        callback_data = f"topic:{topic['id']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    return InlineKeyboardMarkup(keyboard)
