import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import json
import numpy as np
import os


class VectorStore:
    def __init__(self, collection_name: str = "invoice_reimbursements"):
        """Initialize ChromaDB persistent vector store using SentenceTransformer"""
        # Persistent ChromaDB client
        self.client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        self.collection_name = collection_name

        # Create or load the collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Invoice reimbursement analysis storage"}
            )

        # Load the local sentence transformer model
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using SentenceTransformer"""
        try:
            return self.model.encode(text).tolist()
        except Exception as e:
            print(f"Embedding error: {e}")
            return self._simple_embedding(text)

    def _simple_embedding(self, text: str, dimension: int = 384) -> List[float]:
        """Fallback: Generate a hash-based embedding"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        numbers = [ord(c) / 255.0 for c in text_hash]
        while len(numbers) < dimension:
            numbers.extend(numbers)
        return numbers[:dimension]

    def store_analysis(
        self,
        document_id: str,
        invoice_content: str,
        analysis_result: Dict[str, Any],
        employee_name: str,
        filename: str
    ) -> bool:
        """Store invoice analysis in vector database"""
        try:
            combined_text = f"""
            Invoice Content: {invoice_content}

            Analysis Result:
            Status: {analysis_result['status']}
            Reason: {analysis_result['reason']}
            Amount: {analysis_result.get('amount', 'N/A')}
            Reimbursable Amount: {analysis_result.get('reimbursable_amount', 'N/A')}
            """

            embedding = self.generate_embedding(combined_text)

            metadata = {
                "employee_name": employee_name,
                "filename": filename,
                "status": analysis_result['status'],
                "amount": str(analysis_result.get('amount', 'N/A')),
                "reimbursable_amount": str(analysis_result.get('reimbursable_amount', 'N/A')),
                "timestamp": analysis_result.get('timestamp', datetime.now().isoformat()),
                "reason": analysis_result['reason'][:500],
                "policy_violations": json.dumps(analysis_result.get('policy_violations', [])),
                "compliant_items": json.dumps(analysis_result.get('compliant_items', []))
            }

            self.collection.add(
                ids=[document_id],
                embeddings=[embedding],
                documents=[combined_text],
                metadatas=[metadata]
            )

            return True

        except Exception as e:
            print(f"Error storing analysis: {e}")
            return False

    def search_similar(
        self,
        query: str,
        n_results: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            query_embedding = self.generate_embedding(query)
            where_clause = {k: v for k, v in (metadata_filter or {}).items() if v}

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause,
                include=['documents', 'metadatas', 'distances']
            )

            return [
                {
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity_score': 1 - results['distances'][0][i]
                }
                for i in range(len(results['ids'][0]))
            ]

        except Exception as e:
            print(f"Search error: {e}")
            return []

    def search_by_metadata(
        self,
        metadata_filter: Dict[str, Any],
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search by metadata fields only"""
        try:
            where_clause = {k: v for k, v in metadata_filter.items() if v}
            results = self.collection.get(
                where=where_clause,
                include=['documents', 'metadatas'],
                limit=n_results
            )

            return [
                {
                    'id': results['ids'][i],
                    'document': results['documents'][i],
                    'metadata': results['metadatas'][i],
                    'similarity_score': 1.0
                }
                for i in range(len(results['ids']))
            ]

        except Exception as e:
            print(f"Metadata search error: {e}")
            return []

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents"""
        try:
            results = self.collection.get(include=['documents', 'metadatas'])
            return [
                {
                    'id': results['ids'][i],
                    'document': results['documents'][i],
                    'metadata': results['metadatas'][i]
                }
                for i in range(len(results['ids']))
            ]
        except Exception as e:
            print(f"Error getting documents: {e}")
            return []

    def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        try:
            self.collection.delete(ids=[document_id])
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False

    def clear_all(self) -> bool:
        """Clear all documents"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Invoice reimbursement analysis storage"}
            )
            return True
        except Exception as e:
            print(f"Clear error: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get stats about the collection"""
        try:
            all_docs = self.get_all_documents()
            if not all_docs:
                return {
                    'total_documents': 0,
                    'status_distribution': {},
                    'employee_distribution': {},
                    'date_range': None
                }

            status_counts = {}
            employee_counts = {}
            dates = []

            for doc in all_docs:
                metadata = doc['metadata']
                status = metadata.get('status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1

                employee = metadata.get('employee_name', 'Unknown')
                employee_counts[employee] = employee_counts.get(employee, 0) + 1

                timestamp = metadata.get('timestamp')
                if timestamp:
                    dates.append(timestamp)

            dates.sort()
            return {
                'total_documents': len(all_docs),
                'status_distribution': status_counts,
                'employee_distribution': employee_counts,
                'date_range': {
                    'earliest': dates[0],
                    'latest': dates[-1]
                } if dates else None
            }

        except Exception as e:
            print(f"Stats error: {e}")
            return {'error': str(e)}
