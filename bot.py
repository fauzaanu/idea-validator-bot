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
from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
    CommandHandler,
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


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Describe me your business idea.",
        reply_markup=ForceReply(selective=True),
    )
    main_text = """
Please describe the following elements of your business idea:

Problem: What problem does your product solve, and who has this problem?
Solution: How does your product or service solve this problem?
Results: How quickly can users expect to see results or benefits?
Effort: What do users need to do to get results, and how easy is it for them?
"""
    await update.message.reply_text(main_text)


async def idea_validation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("I will validate your idea. Please wait...")
    # call gemini api with the business idea
    resp = google_structured_request(
        model="chat-bison-001",
        system_prompt="you are a business idea validator",
        prompt=VALUE_FORMULA.format(idea=update.message.text),
        response_model=ValueFormula,
        timeout=10,
    )

    await update.message.reply_text(f"{resp.conclusion}")


if __name__ == "__main__":
    load_dotenv()
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    dev_mode = os.environ.get("DEV_MODE", "False").lower() == "True"

    application = Application.builder().token(token).build()

    # text handler
    idea = MessageHandler(filters.TEXT & ~filters.COMMAND, idea_validation)
    application.add_handler(idea)

    # command handlers
    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)



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
