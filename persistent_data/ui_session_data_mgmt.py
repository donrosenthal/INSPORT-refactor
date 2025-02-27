from dataclasses import dataclass # decorator that automatically adds special methods like __init__() and __repr__() to the class.
from typing import List, Optional, Dict # Optional is used for type hinting to indicate that a value might be of a certain type or None.

from pathlib import Path


# Singleton class to manage the overall session state
### ----->>>>> VERSION AS OF 7/24/2024 IS NOT THREAD SAFE
class SessionData:

    _instance = None  # Class variable to hold the single instance

    def __new__(cls):
        # Ensure only one instance of SessionData is created
        if cls._instance is None: # This checks if an instance of SessionData has already been created.
            cls._instance = super(SessionData, cls).__new__(cls) #If no instance exists, this creates a new instance using the superclass's new method.
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize instance variables."""
        self.is_initialized = False
        self.session_id = ""
        self.user_id = ""
        self.first_name = ""
        self.last_name = ""
        self.number_policies = 0
        self.policy_list: Optional[UserPolicies] = None
        self.selected_policy: Optional[Policy] = None # used whenever user selects a new policy
        self.selected_policy_index = None # ints can be initialized to None
        

    def __repr__(self) -> str:
        return f"SessionData(is_initialized={self.is_initialized}, policy_list={self.policy_list}, selected_policy={self.selected_policy})"

    def clear_session_data(self) -> None:
        """Clear all session-related data."""
        self.is_initialized = False
        self.session_id = ""
        self.user_id = ""
        self.first_name = ""
        self.last_name = ""
        self.number_policies = 0
        self.policy_list: Optional[UserPolicies] = None
        self.selected_policy: Optional[Policy] = None 
        self.selected_policy_index = None
       
    def set_initialized_to_true(self):
        """Set the session as initialized."""
        self.is_initialized = True

    def get_is_initialized(self) -> bool:
        """Return whether the session is initialized."""
        return (self.is_initialized)
    
    def set_user_id(self, id: str) -> None:
        self.user_id = id

    def get_user_id(self) -> str:
        return(self.user_id)




# Policy class to represent individual insurance policies
@dataclass
class Policy:
    file_id: str  # Unique identifier for the policy file
    path:   str # URL or file path
    policy_type: str  # Type of policy (e.g., "auto", "home")
    print_name: str  # Display name for the policy
    carrier: str  # Insurance carrier name
    format: str  # File format (e.g., "pdf", "docx")
    is_extracted: bool # Has the pdf file been extracted to a txt file?
    extracted_file_path = str
    additional_metadata: Optional[Dict] = None  # Optional dictionary for extra information which can either be a dict or None

    def __init__(self):
        self.file_id = ""  # Unique identifier for the policy file
        self.path = "" # URL or file path
        self.policy_type = "" # Type of policy (e.g., "auto", "home")
        self.print_name = ""  # Display name for the policy
        self.carrier = ""  # Insurance carrier name
        self.format = ""  # File format (e.g., "pdf", "docx")
        self.is_extracted = False # Has the pdf file been extracted to a txt file?
        self.extracted_file_path = ''
    
        self.additional_metadata = {}

    def to_dict(self):
        result  = {
            "file_id": self.file_id,
            "path": self.path,
            "policy_type": self.policy_type,
            "print_name": self.print_name,
            "carrier": self.carrier,
            "format": self.format,
            "is_extracted": self.is_extracted,
            "extracted_file_path": self.extracted_file_path,
            "additional_metadata": self.additional_metadata
        }

        # Convert any Path objects to strings
        for key, value in result.items():
            if isinstance(value, Path):
                result[key] = str(value)
        

        return(result)
        

# Class to manage all policies for a single user
class UserPolicies:
    def __init__(self, user_id: str):
        self.user_id: str = user_id  # Unique identifier for the user
        self.policy_list: List[Policy] = []  # List to store Policy objects
        self.number_of_policies: int  # Number of stored policies for this user


        

   

    def add_policy(self, policy: Policy):
        # Add a new policy to the list
        self.policies.append(policy)

    def get_policy_by_id(self, file_id: str) -> Optional[Policy]:
        # Retrieve a policy by its file_id, return None if not found
        return next((policy for policy in self.policies if policy.file_id == file_id), None)

    def get_policies_by_type(self, policy_type: str) -> List[Policy]:
        # Return a list of all policies of a specific type
        return [policy for policy in self.policies if policy.policy_type == policy_type]
    
    def get_number_of_policies(self) -> int:
        return self.number_of_policies
    
    def set_number_of_policies(self, num_policies: int) -> None:
        self.number_of_policies = num_policies

    def remove_policy(self, file_id: str) -> bool:
        # Remove a policy by its file_id, return True if successful
        # These lines remove the policy by creating a new list without the matching policy, then check if the length changed to determine if a policy was removed.
        initial_length = len(self.policies)
        self.policies = [policy for policy in self.policies if policy.file_id != file_id]
        return len(self.policies) < initial_length

    def __iter__(self):
        # Make UserPolicies iterable
        return iter(self.policies)
    




    
    



