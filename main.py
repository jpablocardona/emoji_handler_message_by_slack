import os
import re
import sys
import time
import sqlite3

from dotenv import load_dotenv
from slack import WebClient
from slack.errors import SlackApiError

load_dotenv()

# Setting environment variables for Slack access token
slack_token = os.environ["SLACK_API_TOKEN"]
channelID=os.environ["CHANNEL_ID"]
EMOJI = os.environ["EMOJI"]

# Connect to the database and create a table if it doesn't exist
conexion = sqlite3.connect('datos.db')
cursor = conexion.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS datos (
                    id INTEGER PRIMARY KEY,
                    transaction_id TEXT,
                    sender_user_id TEXT,
                    user_id TEXT,
                    name TEXT,
                    email TEXT,
                    segment TEXT,
                    emoji INTEGER,
                    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')

# Initialize the Slack API client
slack_client = WebClient(token=slack_token)

def normalize_segments(sentence):    
    for sep in ['  ', '   ', '     ']:
        sentence = re.sub(r'\s+', sep, sentence)

    paragraphs = []
    current_parragraph = []

    for word in sentence.split():
        if word.startswith("<@"):
            if current_parragraph:
                paragraphs.append(current_parragraph)
                current_parragraph = []
        current_parragraph.append(word)

    if current_parragraph:
        paragraphs.append(current_parragraph)

    paragraphs = [parragraph for parragraph in paragraphs if "<@" in "".join(parragraph)]

    segments = []
    buffer = []
    for i, parragraph in enumerate(paragraphs, 1):
        if len(parragraph) > 1:
            segments.append(" ".join(parragraph))
            if len(buffer) > 0:
                last_parr = [p for p in segments[-1].split() if '<@' not in p]
                for item in buffer:
                    text = " ".join(last_parr)
                    segments.append(item + " " + text)
                    buffer.pop()
        else:
            buffer.append(parragraph[0])

    return segments
    
def extract_user_id(text):
    user_id = None
    match = re.search(r'<@(\w+)>', text)
    if match:
        user_id = match.group(1)

    # Get user info by slack
    user_info = slack_client.users_info(user=user_id)
    user_name = user_info["user"]["name"]
    user_email = user_info["user"]["profile"].get("email")
    
    return user_id, user_name, user_email

def extract_count_by_emoji(text):
    emoji = ":"+EMOJI+":"
    return text.count(emoji)

def calculate_emoji(event):
    client_msg_id = event["client_msg_id"]
    cursor.execute("SELECT count(*) FROM datos WHERE transaction_id = ?", (client_msg_id,))
    count = cursor.fetchone()[0]
    if count > 0:
        return

    sender_user_id = event["user"]

    try:
        segments = normalize_segments(event['text'])
        user_emoji = {}

        if not len(segments):
            return
        
        for segment in segments:
            user_id, user_name, user_email = extract_user_id(segment)
            emoji = extract_count_by_emoji(segment)

            user_emoji[user_id] = {
                "sender_user_id": sender_user_id,
                "user_id": user_id,
                "name": user_name,
                "email": user_email,
                "segment": segment,
                "emoji": emoji
            }
   
        user_emoji = {k: v for k, v in user_emoji.items() if v["email"] and k != sender_user_id and v["emoji"] > 0}

        for user_id, user_info in user_emoji.items():
            cursor.execute("INSERT INTO datos (sender_user_id, transaction_id, user_id, name, email, segment, emoji) VALUES (?, ?, ?, ?, ?, ?, ?)", (sender_user_id, client_msg_id, user_info["user_id"], user_info["name"], user_info["email"], user_info["segment"], user_info["emoji"]))
            conexion.commit()

        print("Processed segments {}".format(user_emoji.__len__()))
        print("*"*40)
    except SlackApiError as e:
        print(f"Error getting user information: {e.response['error']}")

# Function to handle message events
def handle_message(event):
    # Check if the message contains a user tag and a specific emoji
    if ":"+EMOJI+":" in event["text"]:
        calculate_emoji(event)
        

# Listen to message events in real time
if __name__ == "__main__":
    try:
        while True:
            events = slack_client.conversations_history(channel=channelID)
            for event in events["messages"]:
                if "user" in event and "text" in event:
                    handle_message(event)
                    break

    except SlackApiError as e:
        print(f"Error getting Slack events: {e.response['error']}")
        print(e)
        print("*"*40)
        time.sleep(60)
        # Run the program again
        os.execv(sys.executable, ['python'] + sys.argv)