import vertexai

import asyncio
#from flask_socketio import SocketIO, emit
#from flask import Flask, request
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from inner_agent import InnerAgent
from session_manager import session_manager
from vertexai.generative_models import (
    GenerativeModel,
    GenerationConfig,
    SafetySetting,
    HarmCategory,
    HarmBlockThreshold,
    ChatSession
)
import traceback
import json
import os
vertexai.init()

app = FastAPI()

class UserInput(BaseModel):
    user_input: str 

class Orchestrator:
    def __init__(self):
        self.current_step = 0
        # self.app = Flask(__name__)
        # self.socketio = SocketIO(self.app)
        # Wrap the Flask application with socketio.WSGIApp
        self.inner_agent = InnerAgent()
        self.intermediate_parameters = {}
        self.plan_steps = []
 
        # Initialize the chat model
        self.chat_model = GenerativeModel(model_name="gemini-1.5-pro-001")
        self.chat = self.chat_model.start_chat()
        self.safety_config = [
                        SafetySetting(
                            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                            threshold=HarmBlockThreshold.BLOCK_NONE,
                        ),
                        SafetySetting(
                            category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                            threshold=HarmBlockThreshold.BLOCK_NONE,
                        ),
                        SafetySetting(
                            category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                            threshold=HarmBlockThreshold.BLOCK_NONE,
                        ),
                        SafetySetting(
                            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                            threshold=HarmBlockThreshold.BLOCK_NONE,
                        ),
                    ]
        self.generation_config = GenerationConfig(response_mime_type="application/json")

 
    async def run_task(self, user_input, websocket: WebSocket):
        session_id = session_manager.create_session()
        session_manager.update_session_data(session_id, 'cuid', user_input)
        
        try:
            # Initial step: get order list and prioritize ---
            print("Starting task with user input:", user_input)
            agent_response, order_list = await self.inner_agent.execute_task("what are the orders assigned for cuid? given in parameters", {'cuid':user_input})
            self.intermediate_parameters.update({'cuid':user_input})
            order_list = json.loads(order_list)
            print("Retrieved order list:", order_list)
            session_manager.update_session_data(session_id, 'order_list', order_list)
            
            # Prioritize order based on timestamp ----
            prioritized_order = await self.prioritize_order(order_list)
            self.intermediate_parameters.update(prioritized_order)
            print("Prioritized order:", prioritized_order)
            
            # Generate confirmation prompt using the model ----
            #confirmation_prompt = await self.generate_prompt(
            #    f"The prioritized order is: {prioritized_order}. Do you want to proceed with this order?"
            #)
            # Ask for confirmation from the technician
            
            question = "Do you want to proceed with this order?"
            
            confirmed = await self.get_confirmation_from_technician(session_id, question, prioritized_order, websocket)

            print("Confirmation received:", confirmed)
            if not confirmed:
                print("Technician did not confirm to proceed with the order.")
                return
            print("Technician confirmed to proceed with the order.")
 
            # Load the appropriate plan based on the order type ----
            print("Loading plan based on order type")
        
            order_type = prioritized_order.get("Work_Type_Name")
            # if not order_type:
            #     websocket.send_text("Order type is missing.")
            #     return
            # if 'install' in order_type:
            plan_file = f'installation_plan.json'
            print(f"Looking for plan file: {plan_file}")
            if not os.path.exists(plan_file):
                print(f"Plan file {plan_file} does not exist.")
                return
 
            with open(plan_file, 'r') as file:
                self.plan_steps = json.load(file)
            print("Loaded plan for order type:", order_type)
 
            # Execute the plan steps
            print("Executing plan steps")
            await self.execute_plan_steps(session_id, websocket)
 
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print(traceback.format_exc())
 
    async def prioritize_order(self, order_list):
        # Prioritize the order list based on timestamp
        print("Prioritizing order list")
        return order_list[0]
 
    async def execute_plan_steps(self, session_id, websocket:WebSocket):
        while self.current_step < len(self.plan_steps):
            step_details = self.plan_steps[self.current_step]
            print(f"Executing step {self.current_step}: {step_details}")
 
            # Check and request missing parameters
            if "parameters" in step_details:
                print(f"Checking parameters for step {self.current_step}: {step_details['parameters']}")
                valid, missing_params = self.validate_parameters(step_details["parameters"])
                if not valid:
                    for param in missing_params:
                        parameter_prompt = await self.generate_prompt(f"Please provide the value for {param}:")
                        print(f"Asking for missing parameter {param}")
                        param_response = await self.get_input_from_technician(session_id, parameter_prompt,param, websocket)
                        print(f"Received user input from technician: {param_response}")
                        self.intermediate_parameters[param.strip()] = param_response
                parameters_dict = {param: self.intermediate_parameters[param] for param in step_details["parameters"]}
                print(f"Parameters for step {self.current_step}: {parameters_dict}")
 
            # Execute tool for the current step using the inner agent
            print(f"Executing tool for step {self.current_step}: {step_details['task']} with parameters {parameters_dict}")
            intermediate_results, data = await self.inner_agent.execute_task(step_details['task'], parameters_dict)
            
            
            message = {"type": "display", "message":intermediate_results}
            await  websocket.send_text(json.dumps(message))
            print(f"Intermediate results for step {self.current_step}: {intermediate_results}")
 
            # Update intermediate parameters with results from the step
            self.intermediate_parameters.update(data)
            print(f"Updated intermediate parameters: {self.intermediate_parameters}")
 
            # Persist intermediate parameters in the session
            session_manager.update_session_data(session_id, 'intermediate_parameters', self.intermediate_parameters)
            print("Intermediate parameters saved to session")
 
            self.current_step += 1
            print("Next step:", self.current_step)
            
            await self.post_task_interaction(websocket,session_id)
 
    def validate_parameters(self, required_params):
        print(f"Validating parameters: {required_params}")
        print(f"existing parameters : {self.intermediate_parameters}")
        missing_params = [param for param in required_params if param not in self.intermediate_parameters]
        if missing_params:
            print(f"Missing parameters: {missing_params}")
            return False, missing_params
        return True, []
 
    async def generate_prompt(self, prompt_text):
        print(f"Generating prompt with model: {prompt_text}")
        response = await self.ask_model(f"Generate a prompt for the technician: {prompt_text}")
        return response.strip()
 
    async def get_confirmation_from_technician(self, session_id, question, prioritized_order, websocket: WebSocket):
        #print(f"Asking confirmation with prompt: {prompt}")
        #self.socketio.emit('message', {'request': prompt})
        #response = await self.get_user_input()
        message = {"type": "input", "message":question, "data":json.dumps(prioritized_order)}
        await websocket.send_text(json.dumps(message))
        response = await self.handle_user_input(websocket, session_id)
        
        print("user responsed with :",response)
        confirmation_check_prompt = f"The technician responded with: {response}. Did they confirm? answer with just (yes/no)"
        confirmation = await self.ask_model(confirmation_check_prompt)
        confirmed = confirmation.strip().lower().replace('.','') == 'yes'
        print(f"Confirmation response: {confirmation} interpreted as {confirmed}")
        return confirmed
 
    async def get_input_from_technician(self, session_id, prompt,param, websocket: WebSocket):
        print(f"Asking for input with prompt: {prompt}")
        # self.socketio.emit('message', {'request': prompt})
        # response = await self.get_user_input()
        message = {"type": "input", "message":prompt, "data_needed": param}
        #handle user input 
        await  websocket.send_text(json.dumps(message))
        response = await self.handle_user_input(websocket, session_id)
        print(f"Received user input: {response}")
        return response.strip()
 
    async def ask_model(self, prompt, config = None):
        print(f"Asking model with prompt: {prompt}")
        response = []
        if not config:
            for chunk in self.chat.send_message(prompt, stream=True, safety_settings=self.safety_config):
                response.append(chunk.text)
        else: 
            for chunk in self.chat.send_message(prompt, stream=True, safety_settings=self.safety_config, generation_config=config):
                response.append(chunk.text)
        full_response = "".join(response)
        print(f"Model response: {full_response}")
        return full_response

    async def post_task_interaction(self, websocket: WebSocket, session_id):
        while True:
            # Explain the situation to the model and generate a prompt to ask the technician about moving to the next order
            situation_description = (
                "The order has been activated. "
                "Please ask the technician if they want to move to the next order."
            )
            next_order_prompt = await self.generate_prompt(situation_description)
            message = {"type": "input", "message":next_order_prompt}
            await  websocket.send_text(json.dumps(message))

            # Receive response from the technician
            response = await self.handle_user_input(websocket, session_id)
            
            # Confirm the technician's response using the model
            confirmation_check_prompt = (
                f"The technician responded with: {response}. "
                "Do they want to move to the next order (yes) or not (no)?"
            )
            confirmation = await self.ask_model(confirmation_check_prompt)
            if confirmation.strip().lower() == 'yes':
                # If the technician wants to move to the next order, update the order list and restart the process
                message = {"type": "input", "message":"Moving to the next order."}
                await  websocket.send_text(json.dumps(message))
                session_data = session_manager.get_session_data(session_id)
                order_list = session_data.get('order_list', [])
                if order_list:
                    order_list.pop(-1)  # Remove the completed order
                    session_manager.update_session_data(session_id, 'order_list', order_list)
                    if order_list:
                        prioritized_order = order_list[-1]
                        self.intermediate_parameters = {'order_list': order_list}
                        order_type = prioritized_order.get("Work_Type_Name")
                        
                        #if 'install' in order_type:
                        plan_file = f'installation_plan.json'

                        with open(plan_file, 'r') as file:
                            self.plan_steps = json.load(file)

                        # Execute the plan steps for the next order
                        await self.execute_plan_steps(session_id, websocket)
                        
                    else:
                        message = {"type": "display", "message":"No more orders in the list."}
                        await websocket.send_text(json.dumps(message))
                        await websocket.close()
                break
            else:
                # If the technician does not want to move to the next order, ask if they need any other help
                help_prompt_description = (
                    "The technician does not want to move to the next order. "
                    "Please ask if they need any other help."
                )
                help_prompt = await self.generate_prompt(help_prompt_description)
                message = {"type": "input", "message":help_prompt}
                await websocket.send_text(json.dumps(message))
                help_response = await self.handle_user_input(websocket, session_id)

                follow_up_prompt = await self.generate_prompt(
                    f"Thank you for your request: {help_response}. "
                    "The techassist will reach out to you shortly"
                )
                message = {"type": "display", "message":follow_up_prompt}
                await websocket.send_text(json.dumps(message))
                # End the session gracefully
                message = {"type": "display", "message":"Thank you for using the service. Ending the session."}
                await websocket.send_text(json.dumps(message))
                await websocket.close()
                break
                
    async def handle_user_input(self, websocket: WebSocket, session_id):
        response = await websocket.receive_json()
        if response['type'] == 'cuid':
            await self.run_task(response['data'], websocket)
            await websocket.close()
        elif response['data'].lower() in ['quit', 'q','exit'] :
            await websocket.close()
        else:
            return response['data'] 
        
                
orchestrator = Orchestrator()
 
#@orchestrator.app.route('/start_task', methods=['POST'])

@app.websocket("/start_task")
async def start_task(websocket:WebSocket):
    # data = request.json
    # user_input = data['user_input']
    # print("Starting task with user input:", user_input)
    # asyncio.run(orchestrator.run_task(user_input))
    # return {"status": "Task started"}
    await websocket.accept()
    
    response = await websocket.receive_json()
    user_input = response['data']
    await orchestrator.run_task(user_input, websocket)
    await websocket.close()
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, ping_interval=10)
