import asyncio
import websockets
import json
 
async def interact():
    uri = "ws://localhost:8000/start_task"
    async with websockets.connect(uri) as websocket:
        # Send initial user input (e.g., CUID)
        user_input = {"user_input": "ADXXXXX"}  # Example CUID
        await websocket.send(json.dumps(user_input))
 
        while True:
            # Receive and print the server message
            response = await websocket.recv()
            #print("Server:", response)
            response = json.loads(response)
            # Check if the server message asks for further input or confirmation
            if 'data' in response:
                print(response['data'])
            print(response['message'])
            if response['type'] == 'input':
                user_response = input("Enter response: ")
                await websocket.send(user_response)

asyncio.run(interact())