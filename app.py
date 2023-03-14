import os
import re
import pprint
import urllib

from slack_bolt import App
from functools import cache
import sqlite3
import openai

SQLITE_FILENAME = "tuvix-slack.db"
PROMPT_HEADER = "In a Star Trek episode, the year is 2387. Aboard Federation Starship Voyager, Tuvix is in a holodeck simulation of a chatroom from the year 2022. In the simulated chatroom, he is talking to his friends and trying to convince them that he should be allowed to keep living. Tuvix is clever, creative, and friendly.\n\n"

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

def store_display_name(userid, display_name):
    con = sqlite3.connect(SQLITE_FILENAME)
    cur = con.cursor()
    cur.execute("INSERT INTO display_names (userid, display_name) VALUES (?, ?) ON CONFLICT(userid) DO UPDATE SET display_name=excluded.display_name", [userid, display_name])
    con.commit()

@cache
def get_display_name(userid):
    cur = sqlite3.connect(SQLITE_FILENAME).cursor()
    cur.execute("SELECT display_name FROM display_names WHERE userid=?", [userid])
    result = cur.fetchone()
    return result[0] if result else None

def prompt_text(messages):
    lines = "\n".join(f"{actor}: {message}" for (actor, message) in messages)
    return PROMPT_HEADER + lines + "\n\n" + MY_NAME.upper() + ":"

def openai_query(prompt):
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":prompt}],
        temperature=0.9,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0.6,
    )
    return resp['choices'][0]['message']['content'] if ['choices'][0] else None

def openai_draw(prompt):
    resp = openai.Image.create(
        prompt=prompt,
        n=1,
        size="512x512",
    )
    return resp['data'][0]['url'] if resp.data else None

def username(client, user_id):
    name = get_display_name(user_id)
    if name:
        return name

    result = client.users_info(user=user_id)
    name = result.get("user").get("profile").get("display_name_normalized")
    store_display_name(user_id, name)
    return name

@app.event("message")
def on_message(client, event, say, logger, context):
    my_userid = context['bot_user_id']
    actor = event['user']
    msg = event['text']
    stripped_msg = re.sub(f"\<@({my_userid})\>", MY_NAME, msg)
    name = username(client, actor)

    store_message(name.upper(), stripped_msg)

    if msg.startswith(f"<@{my_userid}> draw "):
        prompt = msg[len(f"<@{my_userid}> draw "):]
        url = openai_draw(prompt)
        with urllib.request.urlopen(url) as f:
            client.files_upload(
                channels=event['channel'],
                content=f.read(),
                filetype="png",
                title=prompt,
                initial_comment=f"<@{actor}> Here you go!",
            )
            store_message(MY_NAME.upper(), "Sure! Here's the image I've drawn.")
    elif f"<@{my_userid}>" in msg:
        prompt = prompt_text(recent_messages())
        response = openai_query(prompt)
        if response:
            store_message(MY_NAME.upper(), response)
            say(f"<@{actor}> {response}")


if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
