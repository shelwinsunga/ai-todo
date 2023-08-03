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


# Initialize the messages list outside the while loop
messages = [{"role": "system", "content": "You are a helpful assistant."}]

# Start a conversation with the user
while True:
    user_input = input("You: ")
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
            print("AI: ", response_message["content"])
            break
