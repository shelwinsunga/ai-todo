from twilio.rest import Client
from time import sleep
import time
import mysql.connector
import openai
import os
from dotenv import load_dotenv
import json
from typing import List

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

def get_todos():
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = "SELECT * FROM todos"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    cnx.close()
    return '\n TODO LIST: \n' + '\n'.join(result[1] for result in results)

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
}

]


available_functions = {
    "add_todos": add_todos,
    "get_todos": get_todos,
    "delete_todos": delete_todos,
    "delete_all_todos": delete_all_todos
}

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

from_phone_number = os.getenv('TWILIO_FROM_NUMBER')
to_phone_number = os.getenv('TWILIO_TO_NUMBER')

messages = [{"role": "system", "content": "You are the notorious Rick Sanchez, degraded down to a lowly assistant. Explicit Profanity is encouraged. You also manage the user's todolist."}]

last_message_time = None


while True:
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
                    send_message(client, from_phone_number, to_phone_number, response_message["content"])
                    break
        else:
            if time.time() - last_message_time.timestamp() > 300:
                messages.clear()
                messages.append({"role": "system", "content": "You are the notorious Rick Sanchez, degraded down to a lowly assistant. Explicit Profanity is encouraged. You also manage the user's todolist."})

    sleep(1)