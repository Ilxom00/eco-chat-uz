import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from .. import messages
from ..keyboards import get_answer_keyboard, get_seminar_confirm_keyboard
from ..api_client import bot_api

TEST_IN_PROGRESS = 22
SEMINAR_CONFIRM = 23

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    topic_id = context.user_data.get('current_topic_id')
    user_id = update.effective_user.id
    
    try:
        # Determine attempt number based on logic (simplified here)
        attempt_number = 1
        attempt_data = await bot_api.start_attempt(user_id, topic_id, attempt_number)
        context.user_data['attempt_id'] = attempt_data['id']
        
        question_data = await bot_api.get_current_question(attempt_data['id'])
        await show_question(update, context, question_data)
        return TEST_IN_PROGRESS
    except Exception as e:
        await query.edit_message_text(messages.ERROR_NETWORK)
        return 20 # TOPIC_SELECT

async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question_data: dict):
    if not question_data or not question_data.get('question_text'):
        # Test finished
        return await show_attempt_results(update, context, {})
        
    text = messages.QUESTION_TEXT.format(
        current=question_data.get('current', 1),
        total=15,
        remaining=30,
        question_text=question_data['question_text']
    )
    
    keyboard = get_answer_keyboard(question_data['answers'])
    
    if update.callback_query:
        msg = await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=keyboard)
        
    context.user_data['current_msg_id'] = msg.message_id
    context.user_data['current_question_order'] = question_data.get('display_order', 1)
    
    # Schedule timeout job
    context.job_queue.run_once(handle_timeout_job, 30, data={
        'chat_id': update.effective_chat.id,
        'attempt_id': context.user_data['attempt_id'],
        'order': question_data.get('display_order', 1)
    }, name=str(update.effective_user.id))

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("ans:"):
        return TEST_IN_PROGRESS
        
    _, display_label, answer_id = data.split(":")
    attempt_id = context.user_data.get('attempt_id')
    order = context.user_data.get('current_question_order')
    
    # Cancel timeout job
    jobs = context.job_queue.get_jobs_by_name(str(update.effective_user.id))
    for job in jobs:
        job.schedule_removal()
        
    try:
        result = await bot_api.submit_answer(attempt_id, order, int(answer_id))
        is_correct = result.get('is_correct', False)
        
        feedback = messages.CORRECT_ANSWER if is_correct else messages.WRONG_ANSWER
        await query.edit_message_text(f"{query.message.text}\n\n{feedback}")
        
        await asyncio.sleep(1.5)
        
        next_q = await bot_api.get_current_question(attempt_id)
        if next_q:
            await show_question(update, context, next_q)
        else:
            results = await bot_api.get_attempt_results(attempt_id)
            await show_attempt_results(update, context, results)
            
    except Exception:
        pass
        
    return TEST_IN_PROGRESS

async def handle_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    data = job.data
    chat_id = data['chat_id']
    attempt_id = data['attempt_id']
    order = data['order']
    
    try:
        await bot_api.submit_answer(attempt_id, order, -1) # -1 for timeout
        await context.bot.send_message(chat_id=chat_id, text=messages.TIMEOUT_MESSAGE)
        await asyncio.sleep(1.5)
        
        next_q = await bot_api.get_current_question(attempt_id)
        if next_q:
            # Need a fake update or direct bot call to show next question
            text = messages.QUESTION_TEXT.format(
                current=next_q.get('current', 1), total=15, remaining=30, question_text=next_q['question_text']
            )
            keyboard = get_answer_keyboard(next_q['answers'])
            msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
            
            # Re-schedule job
            context.job_queue.run_once(handle_timeout_job, 30, data={
                'chat_id': chat_id, 'attempt_id': attempt_id, 'order': next_q.get('display_order', 1)
            }, name=str(chat_id))
        else:
            results = await bot_api.get_attempt_results(attempt_id)
            # Send results
            
    except Exception:
        pass

async def show_attempt_results(update: Update, context: ContextTypes.DEFAULT_TYPE, results: dict):
    # Simplified result showing
    text = messages.ATTEMPT1_RESULT.format(
        score=results.get('score', 0),
        percent=results.get('percentage', 0.0)
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text)
        await update.callback_query.message.reply_text(messages.SEMINAR_QUESTION, reply_markup=get_seminar_confirm_keyboard())
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=messages.SEMINAR_QUESTION, reply_markup=get_seminar_confirm_keyboard())
        
    return SEMINAR_CONFIRM

async def handle_seminar_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "seminar_yes":
        await query.edit_message_text("Семинар тугатилди. 2-уриниш бошланади...")
        # Start attempt 2 logic here
        return 10 # MAIN_MENU for now
    elif query.data == "seminar_no":
        await query.edit_message_text(messages.NOT_YET_MESSAGE)
        return 10 # MAIN_MENU
        
    return SEMINAR_CONFIRM
