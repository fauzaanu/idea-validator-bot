#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import os

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
    CommandHandler,
    ConversationHandler,
)

from datamodels import ValueFormula
from prompts import VALUE_FORMULA
from structuredllm.llm_wrapper import google_structured_request

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Define conversation states
PROBLEM, SOLUTION, RESULTS, EFFORT = range(4)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for the problem."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Let's discuss your business idea step by step."
    )
    await update.message.reply_text(
        "What problem does your product solve, and who has this problem?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PROBLEM

async def problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the problem and ask for solution."""
    context.user_data['problem'] = update.message.text
    await update.message.reply_text(
        "How does your product or service solve this problem?"
    )
    return SOLUTION

async def solution(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the solution and ask for results."""
    context.user_data['solution'] = update.message.text
    await update.message.reply_text(
        "How quickly can users expect to see results or benefits?"
    )
    return RESULTS

async def results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the results and ask for effort."""
    context.user_data['results'] = update.message.text
    await update.message.reply_text(
        "What do users need to do to get results, and how easy is it for them?"
    )
    return EFFORT

async def effort(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the effort and process the complete idea."""
    context.user_data['effort'] = update.message.text
    
    # Combine all responses into one text
    complete_idea = f"""
Problem: {context.user_data['problem']}
Solution: {context.user_data['solution']}
Results: {context.user_data['results']}
Effort: {context.user_data['effort']}
"""
    
    await update.message.reply_text("Thank you! I will now validate your complete idea...")
    
    # Call the LLM with the complete idea
    resp = google_structured_request(
        model="chat-bison-001",
        system_prompt="you are a business idea validator",
        prompt=VALUE_FORMULA.format(idea=complete_idea),
        response_model=ValueFormula,
        timeout=10,
    )
    
    analysis = (
        f"📊 Market Analysis: {resp.market_potential}\n\n"
        f"⚙️ Feasibility: {resp.feasibility}\n\n"
        f"💪 Competitive Edge: {resp.competitive_advantage}\n\n"
        f"⚠️ Key Risks: {resp.risks}\n\n"
        f"📋 Recommendation: {resp.recommendation}\n\n"
        f"👉 Next Steps: {resp.next_steps}"
    )
    await update.message.reply_text(analysis)
    return ConversationHandler.END




if __name__ == "__main__":
    load_dotenv()
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    dev_mode = os.environ.get("DEV_MODE", "False").lower() == "True"

    application = Application.builder().token(token).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, problem)],
            SOLUTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, solution)],
            RESULTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, results)],
            EFFORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, effort)],
        },
        fallbacks=[],
    )
    application.add_handler(conv_handler)



    if dev_mode:
        # Webhook settings
        webhook_url = os.environ.get("WEBHOOK_URL")
        port = int(os.environ.get("PORT", 8443))

        # Set webhook
        application.bot.set_webhook(
            url=f"{webhook_url}/{token}", drop_pending_updates=True
        )

        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=f"{webhook_url}/{token}",
        )
    else:
        application.run_polling()
