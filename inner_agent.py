from vertexai.preview import reasoning_engines
from tools import autodiscover_tool, activation_tool,retrieve_orders



class InnerAgent:
    def __init__(self):
        # Initialize the reasoning engine
        
        self.reasoning_agent = reasoning_engines.LangchainAgent(
            model="gemini-1.5-flash-001",
            model_kwargs={"temperature": 0.5},
            tools=[
                retrieve_orders,
                autodiscover_tool,
                activation_tool
            ],
            enable_tracing=False,
            agent_executor_kwargs={"return_intermediate_steps": True}
        )
 
    async def execute_task(self, task, parameters):
        print(f"Executing task: {task} with parameters: {parameters}")
        try:
            response = self.reasoning_agent.query(input= f" {task}, Available parameters: {parameters}")
            print(f"Result from reasoning agent for task {task}: {response}")
            return response['output'], response['intermediate_steps'][-1][-1]
        except Exception as e:
            print(f"Error executing task {task} with reasoning agent: {str(e)}")
            return {"error": str(e)}
 