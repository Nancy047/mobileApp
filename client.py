import asyncio
import websockets
import json
import time
 
async def interact():
    uri = "ws://localhost:8000/start_task"
    async with websockets.connect(uri) as websocket:
        # Send initial user input (e.g., CUID)
        try:
            user_input = {"type": "cuid", "data": "ADXXXXX"}  # Example CUID
            append_value(f"To backend: {user_input}")
            await websocket.send(json.dumps(user_input))
            track = 1
            print(f"To backend: {user_input}")
            while True:
                
                # Receive and print the server message
                print('\n\n\n\n\n\nWaiting for server to send message\n\n\n\n\n\n')
                response = await websocket.recv()
                print(f"from backend: {response}")
                #print("Server:", response)
                response = json.loads(response)
                # Check if the server message asks for further input or confirmation
                append_value(f"from backend: {response}")
                if 'data' in response:
                    print(response['data'])
                print(response['message'])
                #if response['type'] == 'input':
                if track == 1:
                    user_response = "i need help with installation"
                elif track == 2:
                    user_response = "continue"
                elif track == 3:
                    user_response = "yes"
                elif track == 4: 
                    user_response = "continue"
                elif track == 5:
                    user_response = str({"ethernet_port":2, "fsan": "AXON10XXXXXX", "model":"716GE"})
                elif track == 6:
                    user_response = "continue"
                else:
                    user_response = "q"
                    track +=1
                    break
                track +=1
                to_send = {"type": "message", "data": user_response}
                print(f"To backend: {to_send}")
                print('\n\n\n\n\n\nSending a message to server\n\n\n\n\n\n')
                await websocket.send(json.dumps(to_send))
                time.sleep(2)

                append_value(f"To backend: {to_send}")
        except Exception as e:
            print('Exception occured in client', e)
            
def append_value(new_value):
    """Appends a new value to the text file."""
    file_path = "tracker.txt"
    with open(file_path, 'a') as file:
        file.write(f"{new_value}\n")

asyncio.run(interact())