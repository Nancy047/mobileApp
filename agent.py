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
import traceback
from orchestrator import Orchestrator

orchestrator = Orchestrator()

class Agent:
    def __init__(self):
        
        self.installation = "installation"
        self.installation_strt = FunctionDeclaration(
            name= self.installation,
            description="""
            Discription: This tool will start installation process. It will contain multiple steps to complete. is the completion status is completed then the installation job is completed.
            
            Returns:{"tool": {"type": "string", "description": "Tool name that was triggered"},
                    "input_needed": {"type": "boolean", "description": "This will tell the model if user input is required. only ask user questions if this is true."} ,
                    "input_type": {"type": "string", "description": "What type of input is expected from user [confirmation or parameters]"},
                    "step_details": {"type": "string", "description": "This is subtask description, it will tell what step entails"} ,
                    "step_status": {"type": "string", "description": "This is current status of the subtask, this will tell if the subtask is completed so that you can update the technician"} ,
                    "parameters": {"type": "string", "description": "if the input type is parameters then this would contain what all parameters required from user"},
                    "completion_status": {"type": "string", "description": "this is main task final status completion status, This will either say 'pending', 'failed' or 'completed'"},
            """,
            # Function parameters are specified in OpenAPI JSON schema format
            parameters={"type": "object",
                "properties": {
                    "technician_input": {"type": "string", "description": "user input"},
                    
                }
            },
        )

    
        self.ont_activation_tool = Tool(
            function_declarations=[
                self.installation_strt,
            ],
        )
        
        self.system_prompt = ['''You are AI Assistant who guides telecom technician on the field with various tasks.
        You have an internal agent that gives you system messages that updates you on the current status and instructs you what to do meaning conversational, generative and function calling tasks.
        Rules:
        1. Always look for available tools that could do the job before answering on your own. 
        2. If you are unsure of the request, let the technician know that that you have raised a ticket and the techassist team will reach out to technician shortly
        3. Don't ask questions unless prompted buy the function results.
        Tasks: 1. Trigger appropriate tools and help technician in getting job done. like ont activation tool dont go on your own.
               2. Have a conversation with technician and be helpful. The technician input will be given by the system message.
               3. You will get intermittent system message follow the prompt and give appropriate response only for that interaction
               4. System message might be directed towards technician in that case reframe the and give first person response to technician. Each turn it will yield progress so you can keep the technician updated.
               5. The technician will say continue if he wants get the status by running the same function call as before since the completion status is still pending.
               6. Give your status update to the user based on the api response. Focus on step status, before updating the user.
               7. If all steps are completed ask if the technician needs ay other help.
               
               ''']

        # Initialize Gemini model
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
        self.model = GenerativeModel(model_name="gemini-1.5-pro-001",
                                     system_instruction = self.system_prompt,
                                     generation_config=GenerationConfig(temperature=0.1),
                                     tools=[self.ont_activation_tool],
                                     safety_settings= self.safety_config,
                                    )
        

        self.chat = self.model.start_chat(responder = None)
        self.step = 0

        
    async def ask_model(self, session_manager,session_id, prompt = "continue"):
        #print(f"Asking model with prompt: {prompt}")
        #print(prompt)
        response = self.chat.send_message(prompt)
        #print("initial response: ", response)
        #print(response)
        api_response = {}
        data = {}
        input_needed = True
        if prompt == 'continue' or prompt == 'i need help with ont activation':userinput = ''
        else: userinput = prompt
        try:
            #print("function_call: ", response.candidates[0].function_calls[0].name)
            print("step: " ,self.step)
            api_response = await orchestrator.agent_executor(session_manager, session_id, userinput, tool = response.candidates[0].function_calls[0].name, step = self.step)
            #print("step from the model", api_response['step'])
            #print(api_response)
            self.step = api_response['step']
            del api_response['step']
            input_needed = api_response["input_needed"]
            data = api_response["data"]
            if api_response['parameters'] != []:
                data = api_response['parameters']
            del api_response["data"]
            print("orchestrator response final: ", api_response)
            response = self.chat.send_message(
                Part.from_function_response(
                    name="ont_activation",
                    response={
                        "result": str(api_response)},
                ),)
        except Exception as e:
            print("exception in agent: ", e)
            print(traceback.format_exc())
            pass
            
        #print(f"final Model response: {response.text}")
        return response.text, data, api_response, input_needed