from pathlib import Path

def get_repo_root():
    """Returns the repository root path by looking for markers like .git"""
    current_path = Path(__file__).parent.absolute()
    
    # Look for .git directory or other repo markers
    while current_path != current_path.parent:
        if (current_path / ".git").exists():
            return current_path
        current_path = current_path.parent
        
    # If no marker found, fall back to the directory containing this file
    return Path(__file__).parent.absolute()

def get_policy_file_path(filename):     
    """Returns the path to a policy file."""     
    return get_repo_root() / "PDF_speriments" / filename