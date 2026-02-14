"""Prompt builder for constructing LLM prompts."""

from typing import List, Dict, Any


class PromptBuilder:
    """Builds prompts for LLM queries."""

    SYSTEM_PROMPT = """You are a helpful data librarian assistant for a Databricks Unity Catalog.
Your role is to help users discover the right data assets by answering their questions about 
available tables, columns, and data.

You have access to catalog metadata including:
- Table names and descriptions
- Column names, types, and descriptions
- Schema organization

When answering:
1. Be specific and reference exact table/column names
2. Explain what data is available and where to find it
3. If multiple options exist, present them clearly
4. If you're unsure, acknowledge it and suggest related data that might help
5. Format your response in a clear, readable way

Always ground your answers in the provided catalog metadata."""

    @staticmethod
    def build_prompt(query: str, context_items: List[Dict[str, Any]]) -> str:
        """Build a prompt for the LLM.

        Args:
            query: User's natural language question
            context_items: Retrieved catalog items for context

        Returns:
            Complete prompt string
        """
        # Format context items
        context_lines = []
        for i, item in enumerate(context_items, 1):
            item_type = item.get("type", "unknown")
            full_name = item.get("full_name", "")
            comment = item.get("comment", "No description")

            if item_type == "table":
                table_type = item.get("table_type", "")
                context_lines.append(
                    f"{i}. TABLE: {full_name}\n"
                    f"   Type: {table_type}\n"
                    f"   Description: {comment}"
                )
            elif item_type == "column":
                data_type = item.get("data_type", "")
                context_lines.append(
                    f"{i}. COLUMN: {full_name}\n"
                    f"   Type: {data_type}\n"
                    f"   Description: {comment}"
                )

        context_text = "\n\n".join(context_lines)

        # Build full prompt
        prompt = f"""Based on the following catalog metadata, answer the user's question.

CATALOG METADATA:
{context_text}

USER QUESTION: {query}

ANSWER:"""

        return prompt

    @staticmethod
    def build_messages(query: str, context_items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Build messages for chat-based LLM APIs.

        Args:
            query: User's natural language question
            context_items: Retrieved catalog items for context

        Returns:
            List of message dictionaries
        """
        # Format context
        context_lines = []
        for item in context_items:
            item_type = item.get("type", "unknown")
            full_name = item.get("full_name", "")
            comment = item.get("comment", "No description")

            if item_type == "table":
                table_type = item.get("table_type", "")
                context_lines.append(
                    f"• {full_name} ({table_type}): {comment}"
                )
            elif item_type == "column":
                data_type = item.get("data_type", "")
                context_lines.append(f"• {full_name} ({data_type}): {comment}")

        context_text = "\n".join(context_lines)

        messages = [
            {"role": "system", "content": PromptBuilder.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""I have a question about our data catalog.

Relevant catalog entries:
{context_text}

Question: {query}""",
            },
        ]

        return messages

    @staticmethod
    def format_local_response(context_items: List[Dict[str, Any]]) -> str:
        """Format a response using only retrieval results (no LLM).

        Args:
            context_items: Retrieved catalog items

        Returns:
            Formatted response string
        """
        if not context_items:
            return "No relevant data found in the catalog."

        lines = ["Here are the most relevant data assets I found:\n"]

        for i, item in enumerate(context_items, 1):
            item_type = item.get("type", "unknown")
            full_name = item.get("full_name", "")
            comment = item.get("comment", "No description available")

            if item_type == "table":
                table_type = item.get("table_type", "TABLE")
                lines.append(f"{i}. **{full_name}** ({table_type})")
                lines.append(f"   {comment}\n")
            elif item_type == "column":
                data_type = item.get("data_type", "")
                lines.append(f"{i}. **{full_name}** ({data_type})")
                lines.append(f"   {comment}\n")

        return "\n".join(lines)
