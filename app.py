import os
import re

from slack_bolt import App
import sqlite3
import openai

SQLITE_FILENAME = "tuvix-slack.db"
PROMPT_HEADER = "This is a conversation between Tuvix, a character from Star Trek Voyager and a group of his friends.\n\n"

MY_NAME = "Tuvix"

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)
openai.api_key = os.getenv("OPENAI_API_KEY")


def store_message(actor, data):
    con = sqlite3.connect(SQLITE_FILENAME)
    cur = con.cursor()
    cur.execute("INSERT INTO messages (actor, data) VALUES (?, ?)", [actor, data])
    con.commit()

def recent_messages(limit=10):
    cur = sqlite3.connect(SQLITE_FILENAME).cursor()
    cur.execute("SELECT actor, data FROM (SELECT * FROM messages ORDER BY id DESC LIMIT ?) ORDER BY id ASC", [limit])
    return cur.fetchall()

def prompt_single_line(actor, message):
    return f"{actor}: {message}"

def prompt_text(messages):
    lines = "\n".join(prompt_single_line(actor, message) for (actor, message) in messages)
    return PROMPT_HEADER + lines + "\n\n" + MY_NAME.upper() + ":"

def openai_query(prompt):
    resp = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        temperature=0.7,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    if resp.choices:
        return resp.choices[0].text.strip()
    return False

@app.event("message")
def on_message(client, event, say, logger, context):
    my_userid = context['bot_user_id']
    actor = event['user']
    msg = event['text']
    stripped_msg = re.sub(f"\<@({my_userid})\>", MY_NAME, msg)

    store_message(actor, stripped_msg)

    if f"<@{my_userid}>" in msg:
        prompt = prompt_text(recent_messages())
        response = openai_query(prompt)
        if response:
            store_message(MY_NAME.upper(), response)
            say(f"<@{actor}>, {response}")


if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
