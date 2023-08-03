from twilio.rest import Client
from time import sleep
import time
import mysql.connector
import openai
import os
from dotenv import load_dotenv
import json

load_dotenv()  # load environment variables from .env file

openai.api_key = os.getenv('OPENAI_API_KEY')

# MySQL connection details.
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

def add_todo(task: str):
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = "INSERT INTO todos (task) VALUES (%s)"
    cursor.execute(query, (task,))
    cnx.commit()
    cursor.close()
    cnx.close()
    return "Todo added successfully"

def get_todos():
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = "SELECT * FROM todos"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    cnx.close()
    # Convert the list of todos to a string
    # return in a formatted way so that the AI model can read it
    return '\n TODO LIST: \n' + '\n'.join(result[1] for result in results)  # assuming that the task is the second column in the results

def delete_todo(task: str):
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    query = "DELETE FROM todos WHERE task = %s"
    cursor.execute(query, (task,))
    cnx.commit()
    cursor.close()
    cnx.close()
    return "Todo deleted successfully"

# Define the functions that the AI model can call
functions = [
    {
        "name": "add_todo",
        "description": "Add a todo item",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string"}
            },
            "required": ["task"],
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
        "name": "delete_todo",
        "description": "Delete a todo item",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string"}
            },
            "required": ["task"],
        },
    }
]


# The available functions that the AI model can call
available_functions = {
    "add_todo": add_todo,
    "get_todos": get_todos,
    "delete_todo": delete_todo,
}


# Your Twilio credentials
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

# This is the number that will send the reply message
from_phone_number = os.getenv('TWILIO_FROM_NUMBER')
# This is the number that will receive the reply message
to_phone_number = os.getenv('TWILIO_TO_NUMBER')

# Initialize the messages list outside the while loop
messages = [{"role": "system", "content": "You are a warm, intelligent, somewhat snarky assistant. You also manage my todo list."}]

# Initialize the last time a message was received
last_message_time = None

# Start a conversation with the user
while True:
    # Get the list of messages
    twilio_messages = client.messages.list(from_=to_phone_number)

    if twilio_messages:
        # Get the most recent message
        most_recent_message = twilio_messages[0]

        # Only process the message if it's new
        if not last_message_time or most_recent_message.date_created > last_message_time:
            # Update the last message time
            last_message_time = most_recent_message.date_created

            # Get the user's input from the message body
            user_input = most_recent_message.body
            messages.append({"role": "user", "content": user_input})

            while True:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
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
                    )  # extend conversation with function response
                else:
                    # Send the AI's response to the user via SMS
                    client.messages.create(
                        from_=from_phone_number,
                        body=response_message["content"],
                        to=to_phone_number
                    )
                    break

    # Clear the conversation if no new messages have been received in the last 30 seconds
    if last_message_time and time.time() - last_message_time.timestamp() > 30:
        messages.clear()
        messages.append({"role": "system", "content": "You are a helpful assistant."})

    # Wait before checking for new messages again
    sleep(1)
