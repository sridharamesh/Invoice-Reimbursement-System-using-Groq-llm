from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.core.pdf_utils import extract_text_from_pdf, extract_zip_pdfs
from app.core.llm_utils import analyze_invoice_with_policy
from app.core.vector_store import VectorStore
import logging
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple
import time
from functools import partial
import threading

router = APIRouter()

def extract_employee_name_from_path(file_path: str) -> str:
    """
    Extract employee name from file path structure.
    Expected format: folder_name/pdf_file_name.pdf
    Returns: employee_{number}_{folder_name}
    
    Example:
    - Input: "Travel bill/book 1.pdf"
    - Output: "employee_1_travel_bill"
    """
    try:
        path = Path(file_path)
        folder_name = path.parent.name if path.parent.name else "unknown"
        pdf_name = path.stem  # filename without extension
        
        # Clean folder name (remove spaces, convert to lowercase)
        clean_folder = re.sub(r'[^a-zA-Z0-9]', '_', folder_name.lower())
        clean_folder = re.sub(r'_+', '_', clean_folder).strip('_')
        
        # Extract number from PDF filename if present
        number_match = re.search(r'\d+', pdf_name)
        employee_number = number_match.group() if number_match else "1"
        
        return f"employee_{employee_number}_{clean_folder}"
    
    except Exception as e:
        logging.warning(f"Error extracting employee name from path {file_path}: {str(e)}")
        return "employee_unknown"

def process_single_invoice_sync(file_path: str, invoice_text: str, policy_text: str, employee_name_fallback: str) -> Dict:
    """
    Process a single invoice synchronously.
    """
    try:
        # Extract employee name from file path
        dynamic_employee_name = extract_employee_name_from_path(file_path)
        
        # Use provided employee_name as fallback if extraction fails
        final_employee_name = dynamic_employee_name if dynamic_employee_name != "employee_unknown" else (employee_name_fallback or "employee_unknown")
        
        if not invoice_text.strip():
            logging.warning(f"Invoice {file_path} appears to be empty")
            status, reason = "error", "Invoice text is empty or unreadable"
        else:
            # This is the potentially time-consuming operation
            status, reason = analyze_invoice_with_policy(invoice_text, policy_text)
        
        metadata = {
            "invoice_id": Path(file_path).name,
            "file_path": file_path,
            "status": status,
            "reason": reason,
            "employee_name": final_employee_name,
            "folder_name": Path(file_path).parent.name,
        }
        
        # Store analysis results
        try:
            VectorStore.store_analysis(invoice_text, status, reason, metadata)
        except Exception as store_error:
            logging.warning(f"Failed to store analysis for {file_path}: {store_error}")
            # Continue processing even if storage fails
        
        return metadata
        
    except Exception as e:
        logging.error(f"Error analyzing invoice {file_path}: {str(e)}")
        error_metadata = {
            "invoice_id": Path(file_path).name,
            "file_path": file_path,
            "status": "error",
            "reason": f"Analysis failed: {str(e)}",
            "employee_name": extract_employee_name_from_path(file_path),
            "folder_name": Path(file_path).parent.name,
        }
        return error_metadata

async def process_invoices_sequential(invoice_data: Dict[str, str], policy_text: str, employee_name: str) -> List[Dict]:
    """
    Process invoices sequentially with async/await to prevent blocking.
    This is more reliable than threading for I/O bound operations.
    """
    results = []
    total_invoices = len(invoice_data)
    
    for i, (file_path, invoice_text) in enumerate(invoice_data.items(), 1):
        try:
            logging.info(f"Processing invoice {i}/{total_invoices}: {file_path}")
            
            # Run the synchronous processing function in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,  # Use default thread pool
                process_single_invoice_sync,
                file_path,
                invoice_text,
                policy_text,
                employee_name
            )
            
            results.append(result)
            
            # Small delay to prevent overwhelming the system
            if i % 5 == 0:  # Every 5 invoices
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logging.error(f"Error processing invoice {file_path}: {str(e)}")
            error_metadata = {
                "invoice_id": Path(file_path).name,
                "file_path": file_path,
                "status": "error",
                "reason": f"Processing error: {str(e)}",
                "employee_name": extract_employee_name_from_path(file_path),
                "folder_name": Path(file_path).parent.name,
            }
            results.append(error_metadata)
    
    return results

async def process_invoices_batch_safe(invoice_data: Dict[str, str], policy_text: str, employee_name: str, batch_size: int = 3) -> List[Dict]:
    """
    Process invoices in small batches with proper error handling and timeouts.
    """
    results = []
    invoice_items = list(invoice_data.items())
    total_batches = (len(invoice_items) + batch_size - 1) // batch_size
    
    for batch_idx in range(0, len(invoice_items), batch_size):
        batch = invoice_items[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        
        logging.info(f"Processing batch {batch_num}/{total_batches} with {len(batch)} invoices")
        
        # Process each invoice in the batch
        batch_tasks = []
        for file_path, invoice_text in batch:
            # Create a task for each invoice
            loop = asyncio.get_event_loop()
            task = loop.run_in_executor(
                None,
                process_single_invoice_sync,
                file_path,
                invoice_text,
                policy_text,
                employee_name
            )
            batch_tasks.append(task)
        
        try:
            # Wait for all tasks in the batch to complete with timeout
            batch_results = await asyncio.wait_for(
                asyncio.gather(*batch_tasks, return_exceptions=True),
                timeout=120  # 2 minutes per batch
            )
            
            # Process results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    file_path = batch[i][0]
                    logging.error(f"Task failed for {file_path}: {result}")
                    error_metadata = {
                        "invoice_id": Path(file_path).name,
                        "file_path": file_path,
                        "status": "error",
                        "reason": f"Task failed: {str(result)}",
                        "employee_name": extract_employee_name_from_path(file_path),
                        "folder_name": Path(file_path).parent.name,
                    }
                    results.append(error_metadata)
                else:
                    results.append(result)
                    
        except asyncio.TimeoutError:
            logging.error(f"Batch {batch_num} timed out")
            # Add error entries for all invoices in the timed-out batch
            for file_path, _ in batch:
                error_metadata = {
                    "invoice_id": Path(file_path).name,
                    "file_path": file_path,
                    "status": "error",
                    "reason": "Processing timed out",
                    "employee_name": extract_employee_name_from_path(file_path),
                    "folder_name": Path(file_path).parent.name,
                }
                results.append(error_metadata)
        
        # Small delay between batches
        if batch_num < total_batches:
            await asyncio.sleep(0.5)
    
    return results

@router.post("/analyze")
async def analyze_invoices(
    hr_policy: UploadFile = File(...),
    invoice_zip: UploadFile = File(...),
    employee_name: str = Form(None),
    batch_size: int = Form(3),  # Reduced default batch size
    processing_mode: str = Form("batch")  # "batch" or "sequential"
):
    start_time = time.time()
    
    try:
        # Validate file types
        if not hr_policy.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="HR policy must be a PDF file")
        
        if not invoice_zip.filename.lower().endswith('.zip'):
            raise HTTPException(status_code=400, detail="Invoice file must be a ZIP archive")
        
        # Limit batch size to prevent system overload
        batch_size = min(max(batch_size, 1), 5)  # Max 5 for safety
        
        # 1. Extract HR policy text from PDF
        try:
            policy_text = extract_text_from_pdf(hr_policy.file)
            if not policy_text.strip():
                raise HTTPException(status_code=400, detail="HR policy PDF appears to be empty or unreadable")
            logging.info(f"HR policy extracted successfully ({len(policy_text)} characters)")
        except Exception as e:
            logging.error(f"Error extracting HR policy: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed to extract text from HR policy PDF")

        # 2. Extract invoice PDFs and their text
        try:
            invoice_data = extract_zip_pdfs(invoice_zip.file)
            if not invoice_data:
                raise HTTPException(status_code=400, detail="No valid PDF files found in the ZIP archive")
            logging.info(f"Extracted {len(invoice_data)} invoices from ZIP file")
        except Exception as e:
            logging.error(f"Error extracting invoices: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed to extract PDFs from ZIP file")

        # Limit the number of invoices to prevent timeout
        max_invoices = 30  # Reduced for better reliability
        if len(invoice_data) > max_invoices:
            logging.warning(f"Too many invoices ({len(invoice_data)}). Processing first {max_invoices} only.")
            invoice_data = dict(list(invoice_data.items())[:max_invoices])

        # 3. Process invoices based on selected mode
        try:
            if processing_mode == "sequential" or len(invoice_data) <= 5:
                # Use sequential processing for small numbers or when requested
                logging.info("Using sequential processing mode")
                results = await process_invoices_sequential(invoice_data, policy_text, employee_name)
            else:
                # Use batch processing for larger numbers
                logging.info(f"Using batch processing mode with batch size {batch_size}")
                results = await process_invoices_batch_safe(invoice_data, policy_text, employee_name, batch_size)
            
            processing_time = time.time() - start_time
            logging.info(f"Processing completed in {processing_time:.2f} seconds")
            
            return {
                "success": True, 
                "results": results,
                "total_invoices": len(results),
                "processed_successfully": len([r for r in results if r["status"] != "error"]),
                "employee_names_generated": list(set([r["employee_name"] for r in results])),
                "processing_time_seconds": round(processing_time, 2),
                "batch_size_used": batch_size if processing_mode == "batch" else 1,
                "processing_mode": processing_mode
            }
            
        except Exception as e:
            logging.error(f"Error during processing: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error in analyze_invoices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Health check endpoint
@router.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "thread_count": threading.active_count()
    }

# System info endpoint
@router.get("/system-info")
async def get_system_info():
    return {
        "max_batch_size": 5,
        "recommended_batch_size": 3,
        "max_invoices_per_request": 30,
        "timeout_per_batch_seconds": 120,
        "processing_modes": ["sequential", "batch"],
        "recommended_mode": "sequential for ≤5 invoices, batch for >5 invoices"
    }