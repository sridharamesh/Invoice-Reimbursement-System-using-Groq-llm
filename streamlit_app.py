import streamlit as st
import requests
import zipfile
import os
import tempfile
import time
from pathlib import Path

st.set_page_config(page_title="Invoice Reimbursement System", layout="centered")

API_BASE = "http://localhost:8000/api"

st.title("🧾 Invoice Reimbursement System")

tab1, tab2 = st.tabs(["📥 Analyze Invoices", "💬 Chatbot"])

# --- TAB 1: INVOICE ANALYSIS ---
with tab1:
    st.header("Upload Policy and Invoices")
    
    st.info("💡 **Note:** Employee names will be automatically extracted from your ZIP file structure. Expected format: `folder_name/invoice.pdf` → `employee_{number}_{folder_name}`")

    # Performance settings
    st.subheader("⚙️ Processing Settings")
    col1, col2, col3 = st.columns(3)
    with col1:
        processing_mode = st.selectbox(
            "Processing Mode",
            ["auto", "sequential", "batch"],
            index=0,
            help="Auto: sequential for ≤5 invoices, batch for >5. Sequential: one at a time (stable). Batch: multiple at once (faster)."
        )
    with col2:
        batch_size = st.slider(
            "Batch Size", 
            min_value=1, 
            max_value=5,  # Reduced max for stability
            value=3,
            help="Number of invoices to process simultaneously (only for batch mode)."
        )
    with col3:
        timeout_minutes = st.slider(
            "Timeout (minutes)", 
            min_value=5, 
            max_value=30, 
            value=15,  # Increased default timeout
            help="Maximum time to wait for processing to complete."
        )

    # Make employee name optional since we're extracting it from file structure
    employee_name = st.text_input(
        "Employee Name (Optional - Fallback)", 
        help="This will be used as fallback if employee name cannot be extracted from file structure"
    )

    policy_file = st.file_uploader("Upload HR Policy (PDF)", type=["pdf"])
    zip_file = st.file_uploader("Upload Invoices (ZIP)", type=["zip"])
    
    # Add a preview of ZIP structure if file is uploaded
    if zip_file is not None:
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                pdf_files = [f for f in file_list if f.lower().endswith('.pdf')]
                
                if pdf_files:
                    with st.expander(f"📁 Preview ZIP Structure ({len(pdf_files)} PDF files found)"):
                        # Show warning if too many files
                        if len(pdf_files) > 50:
                            st.warning(f"⚠️ Large number of invoices detected ({len(pdf_files)}). This may take a while to process. Consider processing in smaller batches.")
                        elif len(pdf_files) > 20:
                            st.info(f"ℹ️ Processing {len(pdf_files)} invoices. This may take several minutes.")
                        
                        st.write("**Expected employee names based on structure:**")
                        for pdf_file in pdf_files[:10]:  # Show first 10 files
                            path = Path(pdf_file)
                            folder_name = path.parent.name if path.parent.name else "root"
                            pdf_name = path.stem
                            
                            # Simulate the employee name extraction logic
                            import re
                            clean_folder = re.sub(r'[^a-zA-Z0-9]', '_', folder_name.lower())
                            clean_folder = re.sub(r'_+', '_', clean_folder).strip('_')
                            number_match = re.search(r'\d+', pdf_name)
                            employee_number = number_match.group() if number_match else "1"
                            expected_name = f"employee_{employee_number}_{clean_folder}"
                            
                            st.write(f"- `{pdf_file}` → **{expected_name}**")
                        
                        if len(pdf_files) > 10:
                            st.write(f"... and {len(pdf_files) - 10} more files")
                else:
                    st.warning("⚠️ No PDF files found in the ZIP archive")
        except Exception as e:
            st.warning(f"⚠️ Could not preview ZIP file: {str(e)}")

    if st.button("Analyze Invoices", type="primary"):
        # Validate inputs - employee name is now optional
        if not policy_file:
            st.error("Please upload an HR Policy PDF.")
        elif not zip_file:
            st.error("Please upload a ZIP file containing invoices.")
        else:
            try:
                # Create temporary files using context managers and tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_policy:
                    temp_policy.write(policy_file.getvalue())
                    temp_policy_path = temp_policy.name

                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
                    temp_zip.write(zip_file.getvalue())
                    temp_zip_path = temp_zip.name

                # Prepare files for API request with correct parameter names
                with open(temp_policy_path, "rb") as policy_fp, open(temp_zip_path, "rb") as zip_fp:
                    files = {
                        "hr_policy": (policy_file.name, policy_fp, "application/pdf"),
                        "invoice_zip": (zip_file.name, zip_fp, "application/zip")
                    }
                    # Send processing mode, batch size and employee name
                    data = {
                        "batch_size": batch_size,
                        "processing_mode": "sequential" if processing_mode == "sequential" else ("batch" if processing_mode == "batch" else "batch")
                    }
                    if employee_name and employee_name.strip():
                        data["employee_name"] = employee_name.strip()

                    # Create progress indicators
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    start_time = time.time()
                    
                    timeout_seconds = timeout_minutes * 60
                    
                    with st.spinner("🔄 Analyzing invoices... This may take several minutes."):
                        try:
                            status_text.text("📤 Uploading files and starting analysis...")
                            progress_bar.progress(10)
                            
                            response = requests.post(
                                f"{API_BASE}/analyze", 
                                files=files, 
                                data=data,
                                timeout=timeout_seconds
                            )
                            
                            progress_bar.progress(100)
                            processing_time = time.time() - start_time
                            
                            if response.status_code == 200:
                                result = response.json()
                                if result.get("success", False):
                                    results = result.get("results", [])
                                    total = result.get("total_invoices", 0)
                                    successful = result.get("processed_successfully", 0)
                                    employee_names_generated = result.get("employee_names_generated", [])
                                    server_processing_time = result.get("processing_time_seconds", 0)
                                    batch_size_used = result.get("batch_size_used", batch_size)
                                    processing_mode_used = result.get("processing_mode", "unknown")
                                    
                                    st.success(f"✅ Analysis Complete! {successful}/{total} invoices processed successfully in {processing_time:.1f} seconds.")
                                    
                                    # Performance info
                                    st.info(f"⚡ **Performance:** Mode: {processing_mode_used} | Server time: {server_processing_time:.1f}s | Batch size: {batch_size_used} | Total time: {processing_time:.1f}s")
                                    
                                    # Show generated employee names
                                    if employee_names_generated:
                                        st.info(f"👥 **Generated Employee Names:** {', '.join(employee_names_generated)}")
                                    
                                    # Display results in a more organized way
                                    if results:
                                        st.subheader("📊 Analysis Results")
                                        
                                        # Summary statistics
                                        status_counts = {}
                                        for result_item in results:
                                            status = result_item.get('status', 'Unknown')
                                            status_counts[status] = status_counts.get(status, 0) + 1
                                        
                                        # Display status summary
                                        cols = st.columns(len(status_counts))
                                        for i, (status, count) in enumerate(status_counts.items()):
                                            with cols[i]:
                                                if status == 'Fully Reimbursed':
                                                    st.metric(f"✅ {status}", count)
                                                elif status == 'Partially Reimbursed':
                                                    st.metric(f"⚠️ {status}", count)
                                                elif status == 'Declined':
                                                    st.metric(f"❌ {status}", count)
                                                else:
                                                    st.metric(f"ℹ️ {status}", count)
                                        
                                        # Group results by employee name for better organization
                                        employee_groups = {}
                                        for result_item in results:
                                            emp_name = result_item.get('employee_name', 'Unknown')
                                            if emp_name not in employee_groups:
                                                employee_groups[emp_name] = []
                                            employee_groups[emp_name].append(result_item)
                                        
                                        for emp_name, emp_results in employee_groups.items():
                                            st.markdown(f"### 👤 {emp_name}")
                                            
                                            for i, result_item in enumerate(emp_results, 1):
                                                with st.expander(f"Invoice {i}: {result_item.get('invoice_id', 'Unknown')} (from {result_item.get('folder_name', 'root')})"):
                                                    col1, col2 = st.columns(2)
                                                    with col1:
                                                        status = result_item.get('status', 'Unknown')
                                                        if status == 'Fully Reimbursed':
                                                            st.success(f"Status: {status}")
                                                        elif status == 'Partially Reimbursed':
                                                            st.warning(f"Status: {status}")
                                                        elif status == 'Declined':
                                                            st.error(f"Status: {status}")
                                                        else:
                                                            st.info(f"Status: {status}")
                                                    with col2:
                                                        st.write(f"**File Path:** {result_item.get('file_path', 'N/A')}")
                                                    
                                                    reason = result_item.get('reason', 'No reason provided')
                                                    st.write(f"**Reason:** {reason}")
                                else:
                                    st.error("Analysis failed. Please check your files and try again.")
                            else:
                                error_detail = response.json().get('detail', 'Unknown error occurred')
                                st.error(f"❌ Error {response.status_code}: {error_detail}")
                                
                        except requests.exceptions.Timeout:
                            st.error(f"⏰ Request timed out after {timeout_minutes} minutes. Try reducing the batch size or processing fewer invoices at once.")
                            st.info("💡 **Suggestions:**\n- Reduce batch size to 1-2\n- Process invoices in smaller ZIP files\n- Increase timeout duration")
                        except requests.exceptions.ConnectionError:
                            st.error("🔌 Connection error. Please ensure the API server is running.")
                        except requests.exceptions.RequestException as e:
                            st.error(f"🚫 Request failed: {str(e)}")
                        except Exception as e:
                            st.error(f"💥 Unexpected error: {str(e)}")
                        finally:
                            # Clear progress indicators
                            progress_bar.empty()
                            status_text.empty()

            except Exception as e:
                st.error(f"💥 File processing error: {str(e)}")
            finally:
                # Clean up temporary files
                try:
                    if 'temp_policy_path' in locals():
                        os.unlink(temp_policy_path)
                    if 'temp_zip_path' in locals():
                        os.unlink(temp_zip_path)
                except Exception as cleanup_error:
                    st.warning(f"⚠️ Could not clean up temporary files: {cleanup_error}")

# --- TAB 2: CHATBOT ---
with tab2:
    st.header("Ask About Invoices")
    
    query = st.text_area("Enter your question:", placeholder="e.g., What invoices were declined for employee_1_travel_bill?")
    
    # Improved filter section
    st.subheader("🔍 Filters (Optional)")
    filters = {}

    col1, col2 = st.columns(2)
    with col1:
        emp_filter = st.text_input("Filter by Employee Name", placeholder="e.g., employee_1_travel_bill")
        if emp_filter.strip():
            filters["employee_name"] = emp_filter.strip()
    
    with col2:
        status_filter = st.selectbox(
            "Filter by Status", 
            ["", "Fully Reimbursed", "Partially Reimbursed", "Declined", "error"],
            help="Select a status to filter results"
        )
        if status_filter:
            filters["status"] = status_filter

    # Show active filters
    if filters:
        st.info(f"🏷️ Active filters: {', '.join([f'{k}: {v}' for k, v in filters.items()])}")

    if st.button("Ask", disabled=not query.strip()):
        if not query.strip():
            st.error("Please enter a question.")
        else:
            payload = {
                "question": query.strip(),
                "filters": filters if filters else {}
            }
            
            with st.spinner("🤔 Thinking..."):
                try:
                    response = requests.post(
                        f"{API_BASE}/chat", 
                        json=payload,
                        timeout=60,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        answer = result.get("answer", "No answer provided")
                        sources = result.get("sources", [])
                        
                        st.markdown("### 🧠 Answer")
                        st.markdown(answer, unsafe_allow_html=True)

                        if sources:
                            with st.expander(f"🗂 Sources ({len(sources)} found)"):
                                for i, source in enumerate(sources, 1):
                                    st.markdown(f"**Source {i}:**")
                                    st.json(source)
                                    st.markdown("---")
                        else:
                            st.info("ℹ️ No sources found for this query.")
                            
                    else:
                        error_detail = response.json().get('detail', 'Unknown error occurred')
                        st.error(f"❌ Error {response.status_code}: {error_detail}")
                        
                except requests.exceptions.Timeout:
                    st.error("⏰ Request timed out. Please try again.")
                except requests.exceptions.ConnectionError:
                    st.error("🔌 Connection error. Please ensure the API server is running.")
                except requests.exceptions.RequestException as e:
                    st.error(f"🚫 Request failed: {str(e)}")
                except Exception as e:
                    st.error(f"💥 Unexpected error: {str(e)}")

# Add a sidebar with information
with st.sidebar:
    st.markdown("## ℹ️ How to Use")
    st.markdown("""
    ### Tab 1: Analyze Invoices
    1. **Adjust Processing Settings:**
       - Lower batch size for stability
       - Increase timeout for large files
    2. Upload HR policy PDF
    3. Upload ZIP file with invoice PDFs organized in folders
    4. Employee names will be auto-generated from folder structure
    5. Click 'Analyze Invoices'
    
    **ZIP Structure Example:**
    ```
    invoices.zip
    ├── Travel bill/
    │   ├── book 1.pdf → employee_1_travel_bill
    │   └── receipt 5.pdf → employee_5_travel_bill
    └── Medical expenses/
        └── invoice 2.pdf → employee_2_medical_expenses
    ```
    
    ### Tab 2: Chatbot
    1. Enter your question about invoices
    2. Use generated employee names for filtering
    3. Click 'Ask' to get answers
    
    ### Performance Tips
    - **Few invoices (≤5):** Use Sequential mode
    - **Many invoices (>5):** Use Batch mode with batch size 2-3
    - **Timeout issues:** Try Sequential mode or increase timeout
    - **Memory issues:** Process invoices in smaller ZIP files
    - **Persistent errors:** Check API logs for detailed error messages
    """)
    
    st.markdown("---")
    st.markdown("**API Status:**")
    try:
        health_check = requests.get(f"{API_BASE}/health", timeout=5)
        if health_check.status_code == 200:
            st.success("🟢 API Online")
        else:
            st.error("🔴 API Issues")
    except:
        st.error("🔴 API Offline")
    
    # System info
    try:
        system_info = requests.get(f"{API_BASE}/system-info", timeout=5)
        if system_info.status_code == 200:
            info = system_info.json()
            st.markdown("**System Limits:**")
            st.text(f"Max batch size: {info.get('max_batch_size', 'N/A')}")
            st.text(f"Max invoices: {info.get('max_invoices_per_request', 'N/A')}")
            st.text(f"Processing modes: {', '.join(info.get('processing_modes', []))}")
    except:
        pass