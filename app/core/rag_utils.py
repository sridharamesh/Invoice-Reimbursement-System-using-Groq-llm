from groq import Groq
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Groq client with API key
# Consider using environment variables for API keys
client = Groq(api_key=os.getenv("GROQ_API_KEY", "your_api_key"))

def answer_query_with_context(question: str, docs: list) -> str:
    """
    Generate an answer to a question using retrieved document context.
    
    Args:
        question (str): The user's question
        docs (list): List of retrieved documents with metadata
        
    Returns:
        str: Generated answer in markdown format
    """
    try:
        # Build context from retrieved documents
        context = "\n\n".join([
            f"**Invoice ID:** {doc['metadata'].get('invoice_id', 'N/A')}\n"
            f"**Employee:** {doc['metadata'].get('employee_name', 'N/A')}\n"
            f"**Status:** {doc['metadata'].get('status', 'N/A')}\n"
            f"**Reason:** {doc['metadata'].get('reason', 'N/A')}\n"
            f"**Content:** {doc.get('document', '')[:500]}..."
            for doc in docs if doc  # Filter out None/empty docs
        ])
        
        # Create the prompt
        prompt = f"""You are an assistant that answers questions about employee invoice reimbursements.

Use the following document context to respond in **markdown format**:

{context}

Now answer the user's question: {question}

Instructions:
- Be precise and factual
- Use markdown formatting for better readability
- Include relevant details from the context
- If the context doesn't contain enough information, acknowledge this
- Structure your response clearly"""

        # Generate response using Groq
        response = client.chat.completions.create(
            model="llama3-70b-8192",  # Alternative models: "mixtral-8x7b-32768", "llama3-8b-8192"
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
            top_p=1,
            stream=False
        )
        
        answer = response.choices[0].message.content
        logger.info(f"Generated answer for question: {question[:50]}...")
        
        return answer
        
    except Exception as e:
        logger.error(f"Error generating answer: {str(e)}")
        return f"I apologize, but I encountered an error while processing your question. Please try again or contact support if the issue persists."

def format_document_context(docs: list) -> str:
    """
    Helper function to format documents for context.
    
    Args:
        docs (list): List of documents with metadata
        
    Returns:
        str: Formatted context string
    """
    if not docs:
        return "No relevant documents found."
    
    formatted_docs = []
    for i, doc in enumerate(docs, 1):
        if not doc:
            continue
            
        metadata = doc.get('metadata', {})
        content = doc.get('document', '')
        
        formatted_doc = f"""
Document {i}:
- Invoice ID: {metadata.get('invoice_id', 'N/A')}
- Employee: {metadata.get('employee_name', 'N/A')}
- Status: {metadata.get('status', 'N/A')}
- Reason: {metadata.get('reason', 'N/A')}
- Content: {content[:300]}{'...' if len(content) > 300 else ''}
"""
        formatted_docs.append(formatted_doc)
    
    return "\n".join(formatted_docs)