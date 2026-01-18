from typing import List, Callable, Optional


class CerberusMindLogger:
    """
    A logger that agents can use to emit logs to the Cerberus Mind UI.
    
    Logs are formatted as "[Agent Name] Message" and can be collected
    for display in the Streamlit dashboard.
    """
    
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the logger.
        
        Args:
            callback: Optional callback function to invoke with each log message.
                     Useful for real-time streaming in async contexts.
        """
        self._logs: List[str] = []
        self._callback = callback
    
    def log(self, agent_name: str, message: str) -> None:
        """
        Log a message from a specific agent.
        
        Args:
            agent_name: The name/identifier of the agent emitting the log
            message: The log message content
        """
        formatted_log = f"[{agent_name}] {message}"
        self._logs.append(formatted_log)
        
        # Invoke callback if provided (for real-time streaming)
        if self._callback:
            try:
                self._callback(formatted_log)
            except Exception as e:
                # Silently fail if callback errors (e.g., Streamlit context issues)
                print(f"Logger callback error: {e}")
    
    def get_logs(self) -> List[str]:
        """
        Retrieve all collected logs.
        
        Returns:
            List of formatted log messages
        """
        return self._logs.copy()
    
    def clear(self) -> None:
        """Clear all collected logs."""
        self._logs.clear()
    
    def __len__(self) -> int:
        """Return the number of logs collected."""
        return len(self._logs)
