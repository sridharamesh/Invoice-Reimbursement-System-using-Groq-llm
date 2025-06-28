# Invoice Reimbursement System - Setup Guide

## 📋 Overview

This is a complete Streamlit-based Invoice Reimbursement System that uses Large Language Models (LLMs) and vector databases to automatically analyze employee expense invoices against company policies.

## 🚀 Features

- **PDF Invoice Analysis**: Upload and analyze PDF invoices against company policies  
- **Vector Database Storage**: Store analysis results with semantic search capabilities  
- **RAG Chatbot**: Natural language queries to search through processed invoices  
- **Interactive Dashboard**: View analytics and summaries of processed invoices  
- **Streamlit UI**: User-friendly web interface  

## 📁 Project Structure

```

invoice\_reimbursement\_system/
├── main.py                 # Main Streamlit application
├── invoice\_analyzer.py     # Invoice analysis logic
├── vector\_store.py         # Vector database operations
├── chatbot.py             # RAG chatbot implementation
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── output\_images/         # Output UI screenshots
│   ├── 1.png
│   └── 2.png
└── README.md              # This file

````

## 🛠️ Installation

### 1. Clone or Create Project Directory

```bash
mkdir invoice_reimbursement_system
cd invoice_reimbursement_system
````

### 2. Create Python Virtual Environment

```bash
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

Create a `requirements.txt` file with the provided content, then:

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in your project root:

```bash
# .env
Groq_api=your_groq_api_key_here
```

### 5. Create Project Files

Create the following Python files with the provided code:

* `main.py` - Main Streamlit application
* `invoice_analyzer.py` - Invoice analysis module
* `vector_store.py` - Vector store operations
* `chatbot.py` - RAG chatbot implementation

## 🎯 Usage

### 1. Start the Application

```bash
streamlit run main.py
```

The application will open in your browser at `http://localhost:8501`

### 2. Using the System

#### **Invoice Analysis Page**

1. Upload your HR reimbursement policy (PDF)
2. Enter the employee name
3. Upload invoice files (PDF or ZIP containing PDFs)
4. Click "Analyze Invoices"
5. View the analysis results

#### **Chat Interface Page**

1. Ask natural language questions about processed invoices
2. Examples:

   * "Show me all declined invoices"
   * "What invoices did John submit?"
   * "Find invoices over \$500"
   * "Show me partially reimbursed expenses"

#### **Dashboard Page**

* View summary statistics
* See status distribution charts
* Browse all processed invoices

#### **Settings Page**

* Configure API keys
* Check system status
* Export data
* Clear all data

## 🖼️ Output Images

### Invoice Analysis Output

![Invoice Analysis Output](output_images1.png)

### Dashboard Summary View

![Dashboard Summary View](output_images/2.png)

## 🔧 Configuration

### OpenAI API Configuration

* The system uses GPT-4o-mini for invoice analysis
* Embeddings are generated using text-embedding-ada-002
* Fallback mechanisms are provided if API is unavailable

### Vector Database

* Uses ChromaDB for local vector storage
* Automatic embedding generation and similarity search
* Metadata filtering for precise queries

## 📊 Sample Data

### HR Policy Document

Create a sample HR policy PDF with content like:

```
EXPENSE REIMBURSEMENT POLICY

1. ELIGIBLE EXPENSES
   - Business travel (flights, hotels, ground transportation)
   - Business meals (up to $50 per day)
   - Office supplies and equipment
   - Professional development and training

2. LIMITS
   - Meals: Maximum $50 per day
   - Hotel: Maximum $200 per night
   - No alcohol reimbursement
   - Receipts required for expenses over $25

3. SUBMISSION REQUIREMENTS
   - Submit within 30 days of expense
   - Include original receipts
   - Provide business justification
```

### Sample Invoice

Create sample invoice PDFs with content like:

```
HOTEL INVOICE
Date: 2024-01-15
Guest: John Doe
Hotel: Business Inn
Room Rate: $180/night x 2 nights = $360
Tax: $36
Total: $396
```

## 🚨 Troubleshooting

### Common Issues

1. **Groq API Key Error**

   * Ensure your API key is correctly set in the `.env` file
   * Check that you have credits in your OpenAI account

2. **PDF Reading Errors**

   * Ensure PDFs are not password-protected
   * Try with different PDF files if issues persist

3. **ChromaDB Issues**

   * Delete the `chroma.sqlite3` file to reset the database
   * Restart the application

4. **Module Import Errors**

   * Ensure all Python files are in the same directory
   * Check that virtual environment is activated

### Error Handling

The system includes comprehensive error handling:

* Fallback analysis when LLM is unavailable
* Alternative embedding generation methods
* Graceful degradation of features

## 🔒 Security Considerations

* Keep your Groq API key secure and never commit it to version control
* Use environment variables for all sensitive configuration
* Consider implementing user authentication for production use
* Regularly backup your vector database

## 📈 Extending the System

### Adding New Features

1. **Database Integration**: Replace ChromaDB with PostgreSQL + pgvector
2. **User Authentication**: Add login/logout functionality
3. **Email Notifications**: Send alerts for policy violations
4. **Advanced Analytics**: Add more detailed reporting
5. **Mobile Support**: Optimize UI for mobile devices

### Customization Options

* Modify the LLM prompts in `invoice_analyzer.py`
* Adjust vector search parameters in `vector_store.py`
* Customize the UI layout in `main.py`
* Add new reimbursement status categories

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Ensure all dependencies are correctly installed
3. Verify your OpenAI API key is valid
4. Check the Streamlit logs for detailed error messages

## 📝 License

This project is for educational purposes. Ensure compliance with OpenAI's usage policies and any applicable data protection regulations when using in production.

---

**Happy Coding! 🎉**
