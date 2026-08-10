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
    Answers shown in MESSAGE TEXT (full), buttons only have short labels А/Б/В/Г.
    This prevents any text truncation in Telegram inline buttons.
    Returns keyboard with 2 buttons per row: [А][Б] / [В][Г]
    """
    labels = ['А', 'Б', 'В', 'Г']
    row1 = []
    row2 = []
    for idx, answer in enumerate(answers):
        label = labels[idx] if idx < len(labels) else str(idx + 1)
        btn = InlineKeyboardButton(f"  {label}  ", callback_data=f"ans:{idx+1}:{answer['id']}")
        if idx < 2:
            row1.append(btn)
        else:
            row2.append(btn)
    keyboard = [row1, row2] if row2 else [row1]
    return InlineKeyboardMarkup(keyboard)


def format_answers_text(answers: list) -> str:
    """Format answers as readable text to put in the message body."""
    labels = ['А', 'Б', 'В', 'Г']
    lines = []
    for idx, answer in enumerate(answers):
        label = labels[idx] if idx < len(labels) else str(idx + 1)
        text = answer.get('text', '')
        lines.append(f"<b>{label})</b> {text}")
    return '\n'.join(lines)


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
