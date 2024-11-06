import http.server
import socketserver
import json
import argparse
import sys
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
import os

load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')
langchain_api_key = os.getenv('LANGCHAIN_API_KEY')

from persistent_data.ui_session_data_mgmt import SessionData
from handlers.ui_handler_functions import handle_focus, handle_query, handle_clear_button_click, handle_policy_selection, memory, HumanMessage, AIMessage
from server_data.ui_server_side_data import create_server_user_data, ServerUserDataCollection

global session_state


# print("server starting...") # Debug print

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Start the Insurance Portal Chat Demo')
parser.add_argument('--user', type=str, required=True, help='Simulated user to load (user0, user1, or user2)')
args = parser.parse_args()

# Validate the user argument
valid_users = ['user0', 'user1', 'user2']
if args.user not in valid_users:
    print(f"Error: '{args.user}' is not a valid user. Please choose from {', '.join(valid_users)}.")
    sys.exit(1)

# If we get here, the user is valid


class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # print(f"Received GET request for path: {self.path}") # Debug print
        if self.path == '/' or self.path == '//':
            # print("Serving home.html") # Debug print
            self.path = '/home.html'  # Redirect root to home.html
            try:
                return http.server.SimpleHTTPRequestHandler.do_GET(self)
            except Exception as e:
                print(f"Error serving request: {str(e)}")
                self.send_error(500, f"Internal server error: {str(e)}")

        elif self.path.startswith('/script.js'):
            self.path = '/script.js'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        
        elif self.path == '/api/init':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response_data = {
                'firstName': session_state.first_name,
                'policies': [policy.to_dict() for policy in session_state.policy_list]  # Assuming policy_list is the correct attribute name
            }
          
            response = json.dumps(response_data)
            self.wfile.write(response.encode())
        
        elif self.path.startswith('/api/chat'):
            self.send_response(200)
            self.send_header('Content-type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()

            query = parse_qs(urlparse(self.path).query).get('message', [''])[0]
            for chunk in handle_query(query, session_state, session_state.user_id):
                self.wfile.write(f"data: {chunk}\n\n".encode('utf-8'))
                self.wfile.flush()

            return
        
        elif self.path.startswith('/api/select_policy'):
            query_params = parse_qs(urlparse(self.path).query)
            policy = query_params.get('policy', [''])[0]
            # print(f"Received policy selection: '{policy}'")  # Debug print
            if policy:
                try:
                    handle_policy_selection(session_state, session_state.user_id, policy)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = json.dumps({"success": True, "selected_policy": policy})
                    self.wfile.write(response.encode())
                except Exception as e:
                    print(f"Error in handle_policy_selection: {str(e)}")  # Debug print
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    error_response = json.dumps({"success": False, "error": str(e)})
                    self.wfile.write(error_response.encode())
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = json.dumps({"success": False, "error": "No policy specified"})
                self.wfile.write(error_response.encode())
                
        elif self.path == '/api/clear':
            handle_clear_button_click(session_state, session_state.user_id)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode())

        elif self.path == '/api/get_conversation_history':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            history = [
                {"type": "human" if isinstance(msg, HumanMessage) else "ai", "content": msg.content}
                for msg in memory.chat_memory.messages
            ]
            response = json.dumps({"history": history})
            self.wfile.write(response.encode())

        elif self.path == '/api/handle_focus':
            # print("Handling focus") # Debug print
            handle_focus(session_state, session_state.user_id, session_state.session_id, server_user_data)
            # print(f"After handle_focus, selected policy: {session_state. selected_policy}") # Debug print
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response_data = {
                "success": True,
                "firstName": session_state.first_name,
                "lastName": session_state.last_name,
                "policies": [policy.to_dict() for policy in session_state.policy_list],
                "selectedPolicy": session_state.selected_policy if isinstance(session_state.selected_policy, str) else session_state.selected_policy.to_dict() if session_state.selected_policy else None,
                "selectedPolicyIndex": session_state.selected_policy_index,
                "numberPolicies": session_state.number_policies
            }
            response = json.dumps(response_data)
            self.wfile.write(response.encode())

        elif self.path == '/favicon.ico':
            # Ignore the request for favicon.ico
            self.send_response(204)  # No Content
            self.end_headers()
            return
        
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
    



if __name__ == "__main__":
    PORT = 8000

    server_user_data = create_server_user_data() 
    # The above data is dynamic, so needs to gathered evry time the focus returns to the Chatbot. 
    # E.g., the user may have added or delted a policy since the last time the Chatbot held focus.
    # There are some additional things that need to be done the first time that focus is given to the Chatbot.

 
    #   Create an instance of the session_state object with default values
    session_state = SessionData()       
    # session_state will hold all the session  data for the simulated user session 
    # A simple set of python data structures is used to define the data that needs to be maintained
    # A single SessionData instance holds all the data required for a full session with a single user aincluding thir currently upoaded policies, if any.

    user_id = args.user #passed in as a command line argument
    session_id = "sesh123ABC"  # Would be accessed from the server by TBD method   
    handle_focus(session_state, user_id, session_id, server_user_data)

    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        # print(f"Server started at http://localhost:{PORT}") # Debug print
        httpd.serve_forever()










