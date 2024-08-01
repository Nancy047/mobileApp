import uuid
import json
 
class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.session_id = 'init'
    def create_session(self):
        self.session_id = str(uuid.uuid4())
        self.sessions[self.session_id] = {}
        return self.session_id
    
    def save_conversation(self,message):
        with open('conversation.json','r+') as file:
            data = json.load(file)
        with open('conversation.json','w') as file:
            data.append(message)
            json.dump(data, file, indent = 4)

    def get_session_data(self, session_id):
        return self.sessions.get(session_id, None)
 
    def update_session_data(self, session_id, key = None, value = None, data = {}):
        if session_id in self.sessions:
            if len(data) != 0:
                self.sessions[session_id].update(data)
            else:
                self.sessions[session_id][key] = value
            
    def end_session(self, session_id):
        if session_id in self.sessions:
            client_id = self.sessions[session_id]['client_id']
            del self.sessions[session_id]
            del self.active_connections[client_id]
 
    def is_session_active(self, client_id):
        return client_id in self.active_connections

session_manager = SessionManager()