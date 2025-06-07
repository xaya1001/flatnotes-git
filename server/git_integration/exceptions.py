class GitCommandError(Exception):
    """Custom exception for errors during Git command execution."""
    def __init__(self, message, stderr=None, returncode=None, command=None):
        super().__init__(message)
        self.stderr = stderr
        self.returncode = returncode
        self.command = command

    def __str__(self):
        details = f"{super().__str__()} (Return Code: {self.returncode})"
        if self.command:
            details += f"\nCommand: {' '.join(self.command)}"
        if self.stderr:
            details += f"\nStderr: {self.stderr}"
        return details