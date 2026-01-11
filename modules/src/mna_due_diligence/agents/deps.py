

class WorkerDeps:
    def __init__(self, mcp_client, logging_service=None):
        self.client = mcp_client
        self.logging_service = logging_service