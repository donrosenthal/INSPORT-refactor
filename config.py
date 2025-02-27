from pathlib import Path

def get_repo_root():
    """Returns the repository root path."""
    # Start with the directory where this config file is located
    current_path = Path(__file__).parent.absolute()
    
    # You can add marker-based searching here if needed
    return current_path

def get_policy_file_path(filename):
    """Returns the path to a policy file."""
    return get_repo_root() / "PDF_speriments" / filename

# Create commonly used paths
POLICY_DIR = get_repo_root() / "PDF_speriments"