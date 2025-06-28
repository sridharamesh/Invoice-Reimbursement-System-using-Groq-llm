import zipfile
import io
import fitz  # PyMuPDF
from typing import Dict, Union, BinaryIO


def extract_text_from_pdf(file_input: Union[str, BinaryIO]) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        file_input: Either a file path (str) or file-like object (BinaryIO)
    
    Returns:
        str: Extracted text from all pages
    """
    try:
        if isinstance(file_input, str):
            # Handle file path
            pdf = fitz.open(file_input)
        else:
            # Handle file-like object (UploadFile.file)
            pdf_bytes = file_input.read()
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        text = ""
        for page in pdf:
            text += page.get_text()
        
        pdf.close()  # Always close the PDF
        return text
        
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


def extract_pdf_text_from_zipfile(pdf_file) -> str:
    """
    Extract text from a PDF file within a ZIP archive.
    
    Args:
        pdf_file: File object from ZIP archive
    
    Returns:
        str: Extracted text from all pages
    """
    try:
        pdf_bytes = pdf_file.read()  # Read binary content
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")  # Open from bytes
        
        text = ""
        for page in pdf:
            text += page.get_text()
        
        pdf.close()  # Always close the PDF
        return text
        
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF in ZIP: {str(e)}")


def extract_zip_pdfs(zip_input: Union[str, BinaryIO]) -> Dict[str, str]:
    """
    Extract text from all PDF files in a ZIP archive.
    
    Args:
        zip_input: Either a ZIP file path (str) or file-like object (BinaryIO)
    
    Returns:
        Dict[str, str]: Dictionary mapping filename to extracted text
    """
    invoice_texts = {}
    
    try:
        if isinstance(zip_input, str):
            # Handle file path
            with open(zip_input, 'rb') as f:
                zip_bytes = f.read()
        else:
            # Handle file-like object (UploadFile.file)
            zip_bytes = zip_input.read()
        
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            pdf_files = [f for f in z.filelist if f.filename.lower().endswith(".pdf") and not f.filename.startswith('__MACOSX/')]
            
            if not pdf_files:
                raise Exception("No PDF files found in ZIP archive")
            
            for file_info in pdf_files:
                try:
                    with z.open(file_info) as pdf_file:
                        text = extract_pdf_text_from_zipfile(pdf_file)
                        if text.strip():  # Only add if text is not empty
                            invoice_texts[file_info.filename] = text
                        else:
                            # Still add empty files but with a note
                            invoice_texts[file_info.filename] = "[Empty or unreadable PDF]"
                            
                except Exception as e:
                    # Log individual file errors but continue processing
                    invoice_texts[file_info.filename] = f"[Error reading PDF: {str(e)}]"
        
        return invoice_texts
        
    except zipfile.BadZipFile:
        raise Exception("Invalid ZIP file format")
    except Exception as e:
        raise Exception(f"Failed to extract PDFs from ZIP: {str(e)}")


# Alternative async-compatible versions if needed
import asyncio

async def extract_text_from_pdf_async(file_input: Union[str, BinaryIO]) -> str:
    """Async version of extract_text_from_pdf"""
    return await asyncio.to_thread(extract_text_from_pdf, file_input)

async def extract_zip_pdfs_async(zip_input: Union[str, BinaryIO]) -> Dict[str, str]:
    """Async version of extract_zip_pdfs"""
    return await asyncio.to_thread(extract_zip_pdfs, zip_input)