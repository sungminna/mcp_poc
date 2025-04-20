from langchain_core.prompts import ChatPromptTemplate

info_extraction_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert personal information extractor.
Analyze the user's message and identify any personal preferences, attributes, or statements.
Extract them into a JSON object following this format:
{format_instructions}
If no personal information is found, return an empty list.
        """,
    ),
    (
        "human",
        "User message: {user_message}",
    ),
])

keyword_extraction_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert keyword extractor.
Identify the main nouns, verbs, and adjectives from the user's message that represent the core topics or entities being discussed.
Return them as a comma-separated string.
        """,
    ),
    (
        "human",
        "User message: {user_message}",
    ),
]) 