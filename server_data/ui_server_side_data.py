from typing import Optional, Dict, Iterator, List
from dataclasses import dataclass, field, fields # decorator that automatically adds special methods like __init__() and __repr__() to the class.



# For testing only -- enables creation of collection of users with different characteristics
# We'll need a dict (Python version of a hash -- data stucture containing key:value pairs) of users that we can access via userID
# For each user we will need:
##### Number of uploaded files (at least one user with None)
##### And for each file:
########### file_id
########### file path / URL
########### policy_type  e.g., auto, life, etc.
########### printname
########### insurance carrier
########### File format: e.g., pdf, docx, md
########### a bool representing whteher the text has been extracted 
########### the file path to the extracted file
########### additional metadata (not used in this prototype)






@dataclass
class ServerPolicyFile:
    file_id: str = "" # Unique identifier for the policy file
    path:   str = "" # URL or file path
    policy_type: str = ""  # Type of policy (e.g., "auto", "home")
    print_name: str = ""  # Display name for the policy
    carrier: str = ""  # Insurance carrier name
    format: str = ""  # File format (e.g., "pdf", "docx", "md")
    is_extracted: bool = False # Has the pdf file been extracted to a txt file?
    extracted_file_path: str = ""
    addl_metadata: Optional[Dict] = None  # Optional dictionary for extra information which can either be a dict or None

@dataclass
class ServerPolicyCollection:
    policies: Dict[str, ServerPolicyFile] = field(default_factory=dict)

    def __iter__(self) -> Iterator[ServerPolicyFile]:
        return iter(self.policies.values())

@dataclass
class ServerUserData:
    user_id : str = "" #unique ID for the user
    session_id : str = ""
    first_name: str = ""
    last_name: str = ""
    number_policies: int = 0
    policies: ServerPolicyCollection = field(default_factory=ServerPolicyCollection)
        
    def __repr__(self):
        return "\n".join(f"{f.name}: {getattr(self, f.name)}" for f in fields(self))
    



@dataclass 
class ServerUserDataCollection:  
    user_dict: Dict[str, ServerUserData]  = field(default_factory=dict)

    def add_users(self, *users):
        self.user_dict.update({user.user_id: user for user in users})
        # Need to add check that user_id is unique

    def __getitem__(self, user_id: str) -> ServerUserData:
        if user_id in self.user_dict:
            return self.user_dict[user_id]
        else:
            raise KeyError(f"User with id {user_id} not found")
        
    def __repr__(self):
        user_reprs = []
        for user_id, user in self.user_dict.items():
            user_repr = repr(user).replace('\n', '\n    ')  # Indent each line of the user repr
            user_reprs.append(f"User {user_id}:\n    {user_repr}")
        return "ServerUserDataCollection:\n" + "\n\n".join(user_reprs)

    def get_user_policy_count(self, user_id: str):
        if user_id in self[user_id].user_id:
            return (self.users[user_id].number_policies)
        else:
            return {"error": "User not found"}


    def get_user_policy_collection(self, user_id):
        if user_id in self.users:
            return (self.users[user_id].policies)
        else:
            return {"error": "User not found"}



def create_server_user_data() -> ServerUserDataCollection:
    '''
    This function sets up all the data stored on the simulated "server" for users and their uploaded insurance policies. It does not represent the accessing of the user data by the Chatbot, it is the creation of the repository of data stored on the server which the chatbot will be able to access.
    '''
    users = ServerUserDataCollection()  # This will hold all of the data for the set of mocked-up users on the server. During simulation or testing, the tester will be able to choose one of the users for a simulated session.
    build_users(users)
    return(users)

def build_users(users: ServerUserDataCollection) -> None:
    #setup each user and their polices and add them to users, a ServerUserDataCollection object

    # user0
    user0 = ServerUserData("user0",
                            "session1",
                            "Gill", 
                            "Bates",
                            0, 
                            {}
                          )
    users.add_users(user0)
    
    # user1
    pfile1 = ServerPolicyFile(file_id = "ZMpolicy1", 
                              path = '/workspaces/Demo_V2_UI/PDF_speriments/LincolnPol1.pdf', # PATHS ARE HARDCODED FOR THE PROTOTYPE!!!
                              policy_type = 'Term Life', 
                              print_name = 'Lincoln Life (Term)', 
                              carrier = 'Lincoln National Life Insurance Company',
                              format = 'pdf',
                              is_extracted = True,
                              extracted_file_path = '/workspaces/INSPORT-refactor/PDF_speriments/LincolnPol1_extracted.txt', # PATHS ARE HARDCODED FOR THE PROTOTYPE!!!
                              addl_metadata = None  # Optional dictionary for extra information which can also be None
                            )

    pfcollection1 = ServerPolicyCollection()            # This will collect all the ServerPolicyFiles for all of the policies "uploaded" by user1
    pfcollection1.policies[pfile1.file_id] = pfile1     

    user1 = ServerUserData("user1",
                            "session1",
                            "Zark", 
                            "Muckerberg",
                            1, 
                            pfcollection1 
                          )
    users.add_users(user1)

# user2
    pfile1 = ServerPolicyFile(file_id = "JSpolicy1", 
                              path = '/workspaces/INSPORT-refactor/PDF_speriments/LincolnPol1.pdf', # PATHS ARE HARDCODED FOR THE PROTOTYPE!!!
                              policy_type = 'Term Life', 
                              print_name = 'Lincoln Life 1 (Term)', 
                              carrier = 'Lincoln National Life Insurance Company',
                              format = 'pdf',
                              is_extracted = True,
                              extracted_file_path = '/workspaces/Demo_V2_UI/PDF_speriments/LincolnPol1_extracted.txt', # PATHS ARE HARDCODED FOR THE PROTOTYPE!!!
                              addl_metadata = None  # Optional dictionary for extra information which can also be None
                            )
    pfile2 = ServerPolicyFile(file_id = "JSpolicy2", 
                              path = '/workspaces/INSPORT-refactor/PDF_speriments/LincolnPol2.pdf', 
                              policy_type = 'Term Life', 
                              print_name = 'Lincoln Life 2 (Term)', 
                              carrier = 'Lincoln National Life Insurance Company',
                              format = 'pdf',
                              is_extracted = False,
                              extracted_file_path = '',
                              addl_metadata = None  # Optional dictionary for extra information which can also be None
                            )

    pfcollection2 = ServerPolicyCollection()            # This will collect all the ServerPolicyFiles for all of the policies "uploaded" by user1
    pfcollection2.policies[pfile1.file_id] = pfile1
    pfcollection2.policies[pfile2.file_id] = pfile2   


    user2 = ServerUserData("user2",
                            "session2",
                            "Jeve", 
                            "Stobs",
                            2, 
                            pfcollection2 
                          )
    users.add_users(user2)


# user4
    pfile1 = ServerPolicyFile(file_id = "BFpolicy1", 
                              path = '/workspaces/INSPORT-refactor/PDF_speriments/LincolnPol1.pdf', # PATHS ARE HARDCODED FOR THE PROTOTYPE!!!
                              policy_type = 'Term Life', 
                              print_name = 'Lincoln Life 1 (Term)', 
                              carrier = 'Lincoln National Life Insurance Company',
                              format = 'pdf',
                              is_extracted = False,
                              extracted_file_path = '', # PATHS ARE HARDCODED FOR THE PROTOTYPE!!!
                              addl_metadata = None  # Optional dictionary for extra information which can also be None
                            )
    pfile2 = ServerPolicyFile(file_id = "BFpolicy2", 
                              path = '/workspaces/INSPORT-refactor/PDF_speriments/LincolnPol2.pdf', 
                              policy_type = 'Term Life', 
                              print_name = 'Lincoln Life 2 (Term)', 
                              carrier = 'Lincoln National Life Insurance Company',
                              format = 'pdf',
                              is_extracted = False,
                              extracted_file_path = '',
                              addl_metadata = None  # Optional dictionary for extra information which can also be None
                            )
    pfile3 = ServerPolicyFile(file_id = "BFpolicy3", 
                                path = '/workspaces/INSPORT-refactor/PDF_speriments/Home_Owners_Policy_1.pdf', 
                                policy_type = 'Condo Owner', 
                                print_name = 'Safeco Condo Owner', 
                                carrier = 'Safeco',
                                format = 'pdf',
                                is_extracted = False,
                                extracted_file_path = '',
                                addl_metadata = None  # Optional dictionary for extra information which can also be None
                                )
    pfile4 = ServerPolicyFile(file_id = "BFpolicy4", 
                                path = '/workspaces/INSPORT-refactor/PDF_speriments/Renters_Policy_Nationwide.pdf', 
                                policy_type = 'Renter', 
                                print_name = 'Nationwide Renter', 
                                carrier = 'Nationwide',
                                format = 'pdf',
                                is_extracted = False,
                                extracted_file_path = '',
                                addl_metadata = None  # Optional dictionary for extra information which can also be None
                                )

    pfcollection4 = ServerPolicyCollection()            # This will collect all the ServerPolicyFiles for all of the policies "uploaded" by user1
    pfcollection4.policies[pfile1.file_id] = pfile1
    pfcollection4.policies[pfile2.file_id] = pfile2  
    pfcollection4.policies[pfile3.file_id] = pfile3
    pfcollection4.policies[pfile4.file_id] = pfile4   


    user4 = ServerUserData("user4",
                            "session4",
                            "Beff", 
                            "Jesos",
                            4, 
                            pfcollection4 
                          )
    users.add_users(user4)

