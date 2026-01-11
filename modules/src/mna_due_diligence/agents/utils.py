
# Helper function to extract token usage from pydantic-ai result objects
def extract_usage_from_result(result):
    """Extract token usage from pydantic-ai result object"""
    try:
        if hasattr(result, 'usage'):
            usage = result.usage()
            return {
                'total_tokens': getattr(usage, 'total_tokens', None),
                'prompt_tokens': getattr(usage, 'request_tokens', None),
                'completion_tokens': getattr(usage, 'response_tokens', None),
            }
    except:
        pass
    return {'total_tokens': None, 'prompt_tokens': None, 'completion_tokens': None}