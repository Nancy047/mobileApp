import asyncio
import websockets
import json
 
async def interact():
    uri = "ws://localhost:8000/start_task"
    async with websockets.connect(uri) as websocket:
        # Send initial user input (e.g., CUID)
        user_input = {"type": "cuid", "data": "ADXXXXX"}  # Example CUID
        append_value(f"To backend: {user_input}")
        await websocket.send(json.dumps(user_input))
 
        while True:
            # Receive and print the server message
            response = await websocket.recv()
            #print("Server:", response)
            response = json.loads(response)
            # Check if the server message asks for further input or confirmation
            append_value(f"from backend: {response}")
            
            if 'data' in response:
                print(response['data'])
            print(response['message'])
            if response['type'] == 'input':
                user_response = input("Enter response: ")
                to_send = {"type": "message", "data": user_response}
                await websocket.send(json.dumps(to_send))
            
            append_value(f"To backend: {to_send}")
            
def append_value(new_value):
    """Appends a new value to the text file."""
    file_path = "tracker.txt"
    with open(file_path, 'a') as file:
        file.write(f"{new_value}\n")

asyncio.run(interact())
