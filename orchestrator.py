from vertexai.preview.generative_models import (
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Part,
    Tool,
    SafetySetting,
    HarmCategory,
    HarmBlockThreshold,
    ChatSession,ToolConfig
)
import json
from tools import autodiscover_tool, activation_tool,retrieve_orders, prioritize_order
import traceback


class Orchestrator:
    def __init__(self):
       
        self.system_prompt = ['''
        Role: You are task executor. who utilizes available tools to complete the task
        you will receive task to be completed and available parameters.
        input format 
        {"step": {"type": "integer", "description": "current step number"},
        "task": {"type": "string", "description": "task to be completed"},
        "user_input": {"type": "string", "description": "user input to previous output, might be empty if you didnt expect an input"},
        "available_parameters":{"type": "json" , "description": "dictionary of available parameters and their values"}
        
        Rules: Follow the response format.
        Tasks:    
        1. check if you have functions available to complete the task. Detect tool needed to call.
        2. check if you have all the required parameters to run the tool.
        3. if you dont have tools to complete the task, try to do it manually.
        4. if you dont have the required parameters needed for the step, dont change the step number
        5. if you have all the required parameters then trigger the tool
        6. if you have already asked for user input then wait for his response, check if the user input satisfies the task and increment step if it does.
        7. Only perform task from the point you stopped, don't retrigger the tool.
        Response format:
         
        "step": {"type": integer, "description": "increment only if the completion status is completed"},
        "input_needed": {"type": boolean, "description": "This will tell the model if user input is required"} ,
        "input_type": {"type": string, "description": "What type of input is expected from user [confirmation or parameters]"} ,
        "step_details": {"type": "string", "description": "This is step description in the sense what is expected for step to be complete"} ,
        "step_status": {"type": "string", "description": "This is current situation or status of the task"} ,
        "parameters": {"type": array, "description": "if the input type is parameters then this would contain what all parameters required from user else it ill be empty list"},
        "completion_status": {"type": string, "description": "This will either say 'pending', 'failed' or 'completed'"}
        ''']

        self.generation_config = GenerationConfig(response_mime_type="application/json")
        self.tool_config = ToolConfig(
            function_calling_config =
                ToolConfig.FunctionCallingConfig(
                    mode=ToolConfig.FunctionCallingConfig.Mode.AUTO,  # The default model behavior. The model decides whether to predict a function call or a natural language response.
                    #mode=ToolConfig.FunctionCallingConfig.Mode.ANY,  # ANY mode forces the model to predict a function call from a subset of function names.
                    #mode=ToolConfig.FunctionCallingConfig.Mode.NONE,  # NONE mode instructs the model to not predict function calls. Equivalent to a model request without any function declarations.
                    #allowed_function_names = ["function_to_call"]  # Allowed functions to call when mode is ANY, if empty any one of the provided functions will be called.
                )
        )
        self.prioritize_order_func =  FunctionDeclaration.from_func(prioritize_order)
        #print(self.prioritize_order_func)
        self.get_orders_func = FunctionDeclaration.from_func(retrieve_orders)
        self.run_autodiscover_func = FunctionDeclaration.from_func(autodiscover_tool)
        self.run_activation_func = FunctionDeclaration.from_func(activation_tool)
        
        self.ont_tool = Tool(function_declarations=[self.get_orders_func, self.run_autodiscover_func, self.run_activation_func, self.prioritize_order_func])
        
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
        
        self.inner_model = GenerativeModel(model_name="gemini-1.5-pro-001",
                                           system_instruction = self.system_prompt,
                                           generation_config=GenerationConfig(temperature=0.1),
                                           tools=[self.ont_tool], 
                                           tool_config = self.tool_config,
                                           safety_settings= self.safety_config,)
        self.parse_model_response = GenerativeModel(model_name="gemini-1.5-flash-001",
                                     system_instruction = ["convert the string to proper json format"])
        
        
        self.orch_chat = self.inner_model.start_chat(responder = None)
        
        with open('access_plans.json', 'r') as file:
            self.plan_steps = json.load(file)
            
        #self.afc_responder = AutomaticFunctionCallingResponder()
        
    async def parse_response(self, response):
        try:
            parsed_response = self.parse_model_response.generate_content(response.text,generation_config = self.generation_config)
            parsed_response = json.loads(parsed_response.text)
            return parsed_response
        except Exception as e:
            print("parse response: ", response)
            raise e
    
    async def agent_executor(self, session_manager, session_id,user_input, tool, step):
        try:
            #print(self.ont_tool)
            #self.ont_tool = Tool(function_declarations=[self.get_orders_func, self.run_autodiscover_func, self.run_activation_func])
            task = self.plan_steps[tool][step]['task']
            last_step = self.plan_steps[tool][-1]['step']
            
            step = self.plan_steps[tool][step]['step']
            available_parameters = session_manager.get_session_data(session_id)
            if 'orders' in available_parameters and step != 1:
                available_parameters['orders'] = []
            #print("input prompt "+f'"step": "{step}", "task": "{task}"')#, "available_parameters": {available_parameters}')
            response, function_call_result = await self.execute_task(user_input, task, step, parameters = str(available_parameters))
            parsed_response = await self.parse_response(response)
            parsed_response["tool"] = tool
            
            if function_call_result: 
                parsed_response['data'] = function_call_result['response'] 
            
                
                session_manager.update_session_data(session_id, data = parsed_response['data'])
            else: parsed_response['data'] = []
            #print(parsed_response)
                
            if parsed_response["parameters"]:
                #parsed_response["parameters"] = parsed_response["parameters"].split(',')
                pass
            else:
                parsed_response["parameters"] = []
            if step != last_step:
                parsed_response['completion_status'] = 'pending'
            return parsed_response
        except Exception as e:
            print("inner agent exception", e)
            #print(traceback.format_exc())

        
        
    async def execute_task(self,user_input, task, step, parameters):
        input_prompt = '{' +f'"step": "{step}","user_input": "{user_input}", "task": "{task}", "available_parameters": "{parameters}"' + '}'
        print(input_prompt)
        response = self.orch_chat.send_message(input_prompt)
        function_call_result = []
        #print("orchestrator first: ",response)
        try:
            chosen_candidate = response.candidates[0].function_calls[0]
            name = chosen_candidate.name
            #print("function call name: ", name)
            function_args = type(chosen_candidate).to_dict(chosen_candidate)["args"]
            callable_function = self.ont_tool._callable_functions.get(name)
            function_call_result = callable_function._function(**function_args)
            #print(function_call_result)
            response = self.orch_chat.send_message(Part.from_function_response(
                    name=name,
                    response={"result":function_call_result},))
            #print(response)
            
        except Exception as e: 
            function_call_result = None                 
            #print("No function call needed :",e)
        
        
        return response, function_call_result
 