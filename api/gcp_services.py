"""
GCP Services wrapper for Parallax.
Handles Firestore DB operations and Cloud Storage (GCS) uploads.
"""

import os
import json
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

# Optional Google Cloud imports
try:
    from google.cloud import firestore
    from google.cloud import storage
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False


class GCPClient:
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.bucket_name = os.getenv("GCS_BUCKET")
        self.enabled = GCP_AVAILABLE and self.project_id
        
        self.db = None
        self.storage_client = None
        
        if self.enabled:
            try:
                self.db = firestore.AsyncClient(project=self.project_id)
                self.storage_client = storage.Client(project=self.project_id)
                print(f"✅ GCP Services initialized for project: {self.project_id}")
            except Exception as e:
                print(f"⚠️ Failed to initialize GCP clients: {e}")
                print("💡 TIP: Run 'gcloud auth application-default login' in your terminal.")
                self.enabled = False

    async def save_run(self, run_id: str, run_data: dict) -> bool:
        """Save a pipeline run (with report and journeys) to Firestore."""
        if not self.enabled or not self.db:
            return False
            
        try:
            doc_ref = self.db.collection('runs').document(run_id)
            await doc_ref.set(run_data)
            return True
        except Exception as e:
            print(f"⚠️ Firestore save error: {e}")
            return False

    async def get_run(self, run_id: str) -> Optional[dict]:
        """Retrieve a specific run from Firestore."""
        if not self.enabled or not self.db:
            return None
            
        try:
            doc_ref = self.db.collection('runs').document(run_id)
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"⚠️ Firestore get error: {e}")
            return None

    async def list_runs(self, limit: int = 50) -> List[dict]:
        """List recent runs from Firestore."""
        if not self.enabled or not self.db:
            return []
            
        try:
            runs_ref = self.db.collection('runs').order_by(
                'created_at', direction=firestore.Query.DESCENDING
            ).limit(limit)
            
            runs = []
            async for doc in runs_ref.stream():
                data = doc.to_dict()
                runs.append(data)
            return runs
        except Exception as e:
            print(f"⚠️ Firestore list error: {e}")
            return []

    async def delete_run(self, run_id: str) -> bool:
        """Delete a run from Firestore."""
        if not self.enabled or not self.db:
            return False
        try:
            doc_ref = self.db.collection('runs').document(run_id)
            await doc_ref.delete()
            return True
        except Exception as e:
            print(f"⚠️ Firestore delete error: {e}")
            return False

    async def create_user(self, email: str, user_data: dict) -> bool:
        """Create a new user in Firestore."""
        if not self.enabled or not self.db:
            return False
        try:
            doc_ref = self.db.collection('users').document(email.lower())
            await doc_ref.set(user_data)
            return True
        except Exception as e:
            print(f"⚠️ Firestore create_user error: {e}")
            return False

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get a user by email from Firestore."""
        if not self.enabled or not self.db:
            return None
        try:
            doc_ref = self.db.collection('users').document(email.lower())
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"⚠️ Firestore get_user error: {e}")
            return None

    def upload_screenshot_str(self, output_dir: str, filename: str, filepath: str) -> Optional[str]:
        """Upload a local screenshot to GCS and return its public URL. This is synchronous for ease of use in run_navigator."""
        if not self.enabled or not self.storage_client or not self.bucket_name:
            return None
            
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            # Store it under the output_dir so paths stay consistent: output_dir/filename
            blob_path = f"{output_dir}/{filename}"
            blob = bucket.blob(blob_path)
            
            blob.upload_from_filename(filepath, content_type="image/png")
            # We assume the bucket is configured for allUsers read access,
            # so we just format the standard public URL:
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{blob_path}"
            return public_url
        except Exception as e:
            print(f"⚠️ GCS upload error: {e}")
            return None


gcp_client = GCPClient()
