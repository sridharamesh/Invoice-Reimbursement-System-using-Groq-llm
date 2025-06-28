from groq import Groq
import re
import logging
import asyncio

# Initialize Groq client
client = Groq(api_key="your_API_KEY")

def analyze_invoice_with_policy(invoice_text: str, policy_text: str) -> tuple[str, str]:
    """
    Analyze an invoice against HR policy using Groq API.
    
    Args:
        invoice_text: Text content of the invoice
        policy_text: Text content of the HR policy
    
    Returns:
        tuple: (status, reason) where status is one of:
               "Fully Reimbursed", "Partially Reimbursed", "Declined"
    """
    
    # Validate inputs
    if not invoice_text or not invoice_text.strip():
        return "Declined", "Invoice text is empty or unreadable"
    
    if not policy_text or not policy_text.strip():
        return "Declined", "HR policy is empty or unreadable"

    prompt = f"""
You are an AI assistant responsible for analyzing employee invoices based on a company's HR reimbursement policy.

## HR Policy:
{policy_text}

## Employee Invoice:
{invoice_text}

Please analyze the invoice against the HR policy and determine the reimbursement status.

You must respond in exactly this format:
Reimbursement Status: [Fully Reimbursed/Partially Reimbursed/Declined]
Reason: [Your detailed explanation]

Choose one of these three statuses:
- Fully Reimbursed: If the invoice meets all policy requirements
- Partially Reimbursed: If some items are covered but others are not
- Declined: If the invoice doesn't meet policy requirements

Provide a clear, specific reason for your decision.
"""

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",  # You can also use "mixtral-8x7b-32768" or "llama3-8b-8192"
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.3,
            max_tokens=1024
        )
        
        # Extract content from response
        content = response.choices[0].message.content
        
        # Parse the response more robustly
        status, reason = parse_llm_response(content)
        
        # Validate the status
        valid_statuses = ["Fully Reimbursed", "Partially Reimbursed", "Declined"]
        if status not in valid_statuses:
            logging.warning(f"Invalid status returned: {status}. Defaulting to Declined.")
            status = "Declined"
            reason = f"Invalid response format. Original reason: {reason}"
        
        return status, reason
        
    except Exception as e:
        logging.error(f"Error calling Groq API: {e}")
        return "Declined", f"Error: AI analysis failed - {str(e)}"


def parse_llm_response(content: str) -> tuple[str, str]:
    """
    Parse the LLM response to extract status and reason.
    
    Args:
        content: Raw response content from LLM
    
    Returns:
        tuple: (status, reason)
    """
    try:
        # Clean up the content
        content = content.strip()
        
        # Try to find status and reason using regex (more robust)
        status_match = re.search(r'Reimbursement Status:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        reason_match = re.search(r'Reason:\s*(.+?)(?:\n|$)', content, re.IGNORECASE | re.DOTALL)
        
        if status_match and reason_match:
            status = status_match.group(1).strip()
            reason = reason_match.group(1).strip()
            
            # Clean up status to match expected values
            status = normalize_status(status)
            
            return status, reason
        
        # Fallback: try simple line-by-line parsing
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        status = "Declined"
        reason = "Unable to parse response"
        
        for line in lines:
            if line.lower().startswith('reimbursement status:'):
                status = line.split(':', 1)[1].strip()
                status = normalize_status(status)
            elif line.lower().startswith('reason:'):
                reason = line.split(':', 1)[1].strip()
        
        # If we still don't have a good reason, use the full content
        if reason == "Unable to parse response" and content:
            reason = content[:200] + "..." if len(content) > 200 else content
        
        return status, reason
        
    except Exception as e:
        logging.error(f"Error parsing LLM response: {e}")
        return "Declined", f"Response parsing error: {str(e)}"


def normalize_status(status: str) -> str:
    """
    Normalize status text to match expected values.
    
    Args:
        status: Raw status text from LLM
    
    Returns:
        str: Normalized status
    """
    status = status.strip().lower()
    
    # Map various possible responses to standard statuses
    if any(word in status for word in ['fully', 'full', 'complete', 'approved', 'accepted']):
        return "Fully Reimbursed"
    elif any(word in status for word in ['partial', 'partially', 'some', 'limited']):
        return "Partially Reimbursed"
    elif any(word in status for word in ['decline', 'declined', 'reject', 'rejected', 'denied', 'no']):
        return "Declined"
    else:
        # Default to the original if it matches expected format
        status_title = status.title()
        valid_statuses = ["Fully Reimbursed", "Partially Reimbursed", "Declined"]
        if status_title in valid_statuses:
            return status_title
        else:
            return "Declined"


# Async version using Groq
async def analyze_invoice_with_policy_async(invoice_text: str, policy_text: str) -> tuple[str, str]:
    """
    Async version of analyze_invoice_with_policy using Groq API.
    Note: Groq Python SDK doesn't have native async support, so we use asyncio.to_thread
    """
    return await asyncio.to_thread(analyze_invoice_with_policy, invoice_text, policy_text)


# # Alternative async implementation with proper async handling
# async def analyze_invoice_with_policy_async_native(invoice_text: str, policy_text: str) -> tuple[str, str]:
#     """
#     Native async version - you might want to use an async HTTP client for better performance
#     """
#     # Validate inputs
#     if not invoice_text or not invoice_text.strip():
#         return "Declined", "Invoice text is empty or unreadable"
    
#     if not policy_text or not policy_text.strip():
#         return "Declined", "HR policy is empty or unreadable"

#     # For now, we'll use the sync version wrapped in to_thread
#     # In production, consider using aiohttp or httpx for true async HTTP calls
#     return await asyncio.to_thread(analyze_invoice_with_policy, invoice_text, policy_text)


# # Example usage
# if __name__ == "__main__":
#     # Test the function
#     sample_invoice = "Hotel stay at Marriott NYC - $250/night for 2 nights, Business conference"
#     sample_policy = "Hotel expenses are reimbursed up to $200/night for business travel"
    
#     status, reason = analyze_invoice_with_policy(sample_invoice, sample_policy)
#     print(f"Status: {status}")
#     print(f"Reason: {reason}")
    
#     # Test async version
#     async def test_async():
#         status, reason = await analyze_invoice_with_policy_async(sample_invoice, sample_policy)
#         print(f"Async - Status: {status}")
#         print(f"Async - Reason: {reason}")
    
#     # asyncio.run(test_async())