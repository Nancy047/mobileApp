## Overview
This document provides a detailed explanation of the FastAPI-based orchestrator with WebSocket communication. It covers the flow of the application, the scripts involved, methods, and their functionalities.
 
## Project Structure
 
```
/your_project
│
├── orchestrator.py
├── client.py
├── inner_agent.py
├── session_manager.py
├── tools.py
├── installation_plan.json
├── repair_plan.json
├── README.md
```
 
## Application Flow
 
1. **Client Initiation**
- **Script**: `client.py`
   - **Methods**: `interact()`
   - **Functionality**: The client connects to the FastAPI WebSocket server, sends initial user input (e.g., technician CUID), and handles incoming messages from the server, sending responses back as needed.
 
2. **Orchestrator Initialization**
- **Script**: `orchestrator.py`
   - **Methods**: `run_task()`
   - **Functionality**:
     - Receives user input and creates a session.
     - Retrieves the order list if not already provided, and prioritizes it based on timestamps.
     - Confirms with the technician whether to proceed with the prioritized order.
     - Loads the appropriate plan based on the order type and initiates the execution of the plan steps.
 
3. **Plan Execution**
- **Script**: `orchestrator.py`
   - **Methods**: `execute_plan_steps()`
   - **Functionality**:
     - Iterates through each step in the plan.
     - Validates and requests necessary parameters from the technician.
     - Executes the step using the `InnerAgent` class and updates intermediate parameters.
     - Persists intermediate parameters in the session data to ensure continuity.
 
4. **Post Task Interaction**
- **Script**: `orchestrator.py`
   - **Methods**: `post_task_interaction()`
   - **Functionality**:
     - After completing the steps, interacts with the technician to determine if they want to move to the next order or need further help.
     - If moving to the next order, updates the order list, clears intermediate parameters except for the order list, and starts the execution of the next order's plan.
     - If further help is needed, continues interacting with the technician until the session ends gracefully.
 
5. **Session Management**
- **Script**: `session_manager.py`
   - **Class**: `SessionManager`
   - **Methods**: `create_session()`, `update_session_data()`, `get_session_data()`
   - **Functionality**:
     - Manages session data including user input, intermediate parameters, and order list.
     - Ensures continuity and state management across multiple orders or assistance requests.
 
## Detailed Script Explanations
 
### 1. `client.py`
- **Purpose**: Manages the client-side communication with the FastAPI server using WebSockets.
- **Main Method**: `interact()`
  - Connects to the server.
  - Sends initial user input.
  - Handles ongoing interactions by receiving messages from the server and sending back responses.
 
### 2. `orchestrator.py`
- **Purpose**: Acts as the central orchestrator, managing the flow of tasks and interactions with the technician.
- **Key Methods**:
  - **`run_task()`**:
    - Initiates the task based on user input.
    - Retrieves and prioritizes the order list.
    - Confirms with the technician to proceed with the order.
    - Loads the appropriate plan and starts the execution of steps.
  - **`execute_plan_steps()`**:
    - Executes each step of the plan.
    - Validates and requests parameters.
    - Uses the `InnerAgent` to perform specific tasks.
    - Updates and persists intermediate parameters.
  - **`post_task_interaction()`**:
    - Handles post-task interactions with the technician.
    - Determines whether to proceed with the next order or provide additional help.
    - Updates the order list and restarts the task if necessary.
 
### 3. `inner_agent.py`
- **Purpose**: Contains the `InnerAgent` class which is responsible for executing specific tasks using defined tools.
- **Key Method**: `execute_task()`
- Executes a given task using tools defined in `tools.py`.
  - Returns the result of the task execution to the orchestrator.
 
### 4. `session_manager.py`
- **Purpose**: Manages session data to ensure continuity across multiple orders or assistance requests.
- **Key Methods**:
  - **`create_session()`**: Creates a new session.
  - **`update_session_data()`**: Updates session data with new information.
  - **`get_session_data()`**: Retrieves current session data.
 
### 5. `tools.py`
- **Purpose**: Contains utility functions used by the `InnerAgent` to perform specific tasks.
- **Key Functions**:
  - Functions to interact with databases, perform logic operations, or make API calls necessary for task execution.
 
### 6. `installation_plan.json` & `repair_plan.json`
- **Purpose**: Define the task plans for installation and repair orders.
- **Structure**: JSON files outlining the steps and parameters required for executing installation and repair tasks.