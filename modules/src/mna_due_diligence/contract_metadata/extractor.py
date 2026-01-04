from datetime import date
from .model import ContractMetadata
from mna_due_diligence.llm import LLMFactory, DEFAULT_LLM_PROVIDER, StructuredLLMInput



class MetadataExtractor:
    def __init__(self, model="gpt-4.1-nano"):
        self.model = model
        self.llm = LLMFactory.create(
            provider=DEFAULT_LLM_PROVIDER,
            model=model
        )

    def extract(self, full_markdown: str) -> ContractMetadata:
        """
        Intelligently selects the start/end of the doc to save tokens,
        then asks LLM for structured data.
        """
        # Heuristic: Metadata is usually at the start (Preamble) or end (Signatures)
        # We take first 4000 chars and last 2000 chars.
        # Markdown parsing preserves headers, so we get good context.
        if len(full_markdown) > 6000:
            context_text = full_markdown[:4000] + "\n...[SKIPPED BODY]...\n" + full_markdown[-2000:]
        else:
            context_text = full_markdown

        prompt = """
        Analyze the following contract text (which may be a snippet of the start and end).
        Extract the key metadata fields.
        - If a date is ambiguous, prefer the "Effective Date" stated at the top.
        - Normalize Company names (e.g., remove 'Inc.' if redundant).
        - If information is strictly missing, return null/None.
        """

        return self.llm.generate_structured(
            inp=StructuredLLMInput(messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": context_text}
            ]),
            output_model=ContractMetadata
        )