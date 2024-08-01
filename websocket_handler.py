import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
#from orchestrator import Orchestrator
from agent import Agent
import uvicorn
import json
from logging_config import logger
from session_manager import SessionManager
#from orchestrator import Orchestrator
import traceback
app = FastAPI()
#orchestrator = Orchestrator()
agent = Agent()
session_manager = SessionManager()

class WebSocketHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = session_manager.create_session()

    async def connect(self):
        await self.websocket.accept()
 
    async def disconnect(self):
        await self.websocket.close()
 
    async def send_message(self, message_type:str, message:str, data = []):
        try: 
            if data == '' or data == '[]':
                data = []
            output_message = {"type": message_type, "message":message, "data":json.dumps(data)}
            print(output_message)
            await self.websocket.send_text(json.dumps(output_message))
            status = "Message Sent Successfully"
            logger.info(status)
            if data != []:
                session_manager.save_conversation("Data: " + str(data))
            session_manager.save_conversation("Agent: " + str(message))
            #session_manager.save_conversation("server: " + str(output_message))
            return status
        except Exception as e:
            print(e)
            status = "Send Message Failed"
            logger.info(status)
            return status

         
    async def receive_message(self):
        '''Get user input'''
        user_input = await self.websocket.receive_json()
        session_manager.save_conversation("Tech: " + str(user_input['data']))
        if user_input['type'] == 'cuid':
            # Treat as a new session if CUID is provided
            session_manager.update_session_data(self.session_id, user_input['type'], user_input['data'])
            sytem_input = 'System message: Technician has joined the conversation'
            return sytem_input
        elif user_input['data'].lower() in ['quit', 'q','exit']:
            await self.disconnect()
        else:
            user_input = str(user_input['data'])
            return user_input
            
        
    async def keep_alive(self):
        while True:
            try:
                await self.websocket.send_text("ping")
                response = await self.websocket.receive_text()
                if response == "pong":
                    await asyncio.sleep(30)  # Send ping every 30 seconds
                else:
                    break
            except WebSocketDisconnect:
                break
                
                


@app.websocket("/start_task")
async def websocket_endpoint(websocket: WebSocket):
    handler = WebSocketHandler(websocket)
    session_id = handler.session_id
    await handler.connect()
    api_response = ""
    input_needed = True
    #keep_alive_task = asyncio.create_task(handler.keep_alive())
    try:
        while True:
            print('\n\n\n\n\nWaiting on input from client\n\n\n\n\n')
            prompt = await handler.receive_message()
            message, data, api_response, input_needed = await agent.ask_model(session_manager, session_id, prompt)
            print("output_text: ", message)
            #data = api_response['data']
            if input_needed:
                message_type = 'input'
            else:
                message_type = 'display'
            print('\n\n\n\n\Sending response to client\n\n\n\n\n')
                
            status = await handler.send_message(message_type, message, data)
    except WebSocketDisconnect as e:
        print("Client disconnected", e)
        await handler.disconnect()
    except Exception as exc:
        print('Exception occured: ', exc)
    #finally:
    #    keep_alive_task.cancel()  # Cancel keep-alive task when done

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=5, timeout_keep_alive=5000)