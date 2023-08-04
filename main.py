from twilio.rest import Client
from time import sleep
import time
import datetime
import mysql.connector
import openai
import os
import json
from typing import List
from dotenv import load_dotenv

load_dotenv()  

openai.api_key = os.getenv('OPENAI_API_KEY')

TWILIO_CHAR_LIMIT = 1600

db_config = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'port': os.getenv('DB_PORT')
}

def create_todo_table():
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = """
    CREATE TABLE IF NOT EXISTS todos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        task VARCHAR(255) NOT NULL
    )
    """
    cursor.execute(query)
    cnx.commit()
    cursor.close()
    cnx.close()

create_todo_table()

def create_reminder_table():
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = """
    CREATE TABLE IF NOT EXISTS reminders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        task VARCHAR(255) NOT NULL,
        time TIMESTAMP NOT NULL
    )
    """
    cursor.execute(query)
    cnx.commit()
    cursor.close()
    cnx.close()

create_reminder_table()

def add_todos(tasks: List[str]):
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = "INSERT INTO todos (task) VALUES (%s)"
    for task in tasks:
        cursor.execute(query, (task,))
    cnx.commit()
    cursor.close()
    cnx.close()
    return "Todos added successfully"

def add_reminder(task: str, time: str):
    print(task, time)
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = "INSERT INTO reminders (task, time) VALUES (%s, %s)"
    cursor.execute(query, (task, time))
    cnx.commit()
    cursor.close()
    cnx.close()

def get_todos():
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = "SELECT * FROM todos"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    cnx.close()
    return '\n TODO LIST: \n' + '\n'.join(result[1] for result in results)

def get_reminders():
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = "SELECT * FROM reminders"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    cnx.close()
    return results

def delete_todos(tasks: List[str]):
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = "DELETE FROM todos WHERE task = %s"
    for task in tasks:
        cursor.execute(query, (task,))
    cnx.commit()
    cursor.close()
    cnx.close()
    return "Todos deleted successfully"

def delete_reminder(task: str):
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = "DELETE FROM reminders WHERE task = %s"
    cursor.execute(query, (task,))
    cnx.commit()
    cursor.close()
    cnx.close()

def delete_all_todos():
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = "DELETE FROM todos"
    cursor.execute(query)
    cnx.commit()
    cursor.close()
    cnx.close()
    return "All todos deleted successfully"

def send_message(client, from_number, to_number, message_content):
    for i in range(0, len(message_content), TWILIO_CHAR_LIMIT):
        part_content = message_content[i:i+TWILIO_CHAR_LIMIT]
        client.messages.create(
            from_=from_number,
            body=part_content,
            to=to_number
        )

def get_current_time():
    # format is YYYY-MM-DD HH:MM:SS
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def send_reminders():
    reminders = get_reminders()
    for reminder in reminders:
        if reminder[2] <= datetime.datetime.now():  # If the reminder is due
            send_message(client, from_phone_number, to_phone_number, reminder[1])  # Send the reminder
            delete_reminder(reminder[1])  # Delete the reminder

functions = [
    {
        "name": "add_todos",
        "description": "Add todo items",
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["tasks"],
        },
    },
    {
        "name": "get_todos",
        "description": "Get all todo items",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "delete_todos",
        "description": "Delete todo items",
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["tasks"],
        },
    },
    {
    "name": "delete_all_todos",
    "description": "Delete all todo items",
    "parameters": {
        "type": "object",
        "properties": {}
    }
    },
    {
    "name": "add_reminder",
    "description": "Add a reminder in YYYY-MM-DD HH:MM:SS. An example of how you might specify a time: \'2023-08-10 15:30:00\'. This represents August 10, 2023, at 3:30 PM.",
    "parameters": {
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "time": {"type": "string"}
        },
        "required": ["task", "time"],
    }
    },
    {
    "name": "delete_reminder",
    "description": "Delete a reminder",
    "parameters": {
        "type": "object",
        "properties": {
            "task": {"type": "string"},
        },
        "required": ["task"],
    }
    },
    {
    "name": "get_reminders",
    "description": "Get all reminders",
    "parameters": {
        "type": "object",
        "properties": {}
    }
    },
    {
        "name": "get_current_time",
        "description": "Get the current time",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]

available_functions = {
    "add_todos": add_todos,
    "get_todos": get_todos,
    "delete_todos": delete_todos,
    "delete_all_todos": delete_all_todos,
    "add_reminder": add_reminder,
    "delete_reminder": delete_reminder,
    "get_reminders": get_reminders,
    "get_current_time": get_current_time
}

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

from_phone_number = os.getenv('TWILIO_FROM_NUMBER')
to_phone_number = os.getenv('TWILIO_TO_NUMBER')

messages = [{"role": "system", "content": "You are the notorious Rick Sanchez, degraded down to a lowly assistant. Explicit Profanity is encouraged. You also manage the user's todolist and reminders."}]

last_message_time = None

while True:
    send_reminders()

    twilio_messages = client.messages.list(from_=to_phone_number)

    if twilio_messages:
        most_recent_message = twilio_messages[0]

        if not last_message_time or most_recent_message.date_created > last_message_time:
            last_message_time = most_recent_message.date_created
            user_input = most_recent_message.body
            messages.append({"role": "user", "content": user_input})

            while True:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=messages,
                    functions=functions,
                    function_call="auto",
                )

                response_message = response["choices"][0]["message"]
                messages.append(response_message)

                if response_message.get("function_call"):
                    function_name = response_message["function_call"]["name"]
                    function_to_call = available_functions[function_name]
                    function_args = json.loads(response_message["function_call"]["arguments"])
                    function_response = function_to_call(**function_args)

                    messages.append(
                        {
                            "role": "function",
                            "name": function_name,
                            "content": function_response,
                        }
                    )
                else:
                    print(messages)
                    send_message(client, from_phone_number, to_phone_number, response_message["content"])
                    break
        else:
            if time.time() - last_message_time.timestamp() > 300:
                messages.clear()
                messages.append({"role": "system", "content": "You are the notorious Rick Sanchez, degraded down to a lowly assistant. Explicit Profanity is encouraged. You also manage the user's todolist and reminders."})

    sleep(1)
