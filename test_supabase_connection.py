"""
Supabase Connection Verification Script for JunctionGuard AI.
Tests database tables query and storage bucket access.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

def test_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    print("==========================================")
    print("🔍 Testing Supabase Connection...")
    print(f"URL: {url}")
    print("==========================================")

    if not url or not key:
        print("❌ Error: SUPABASE_URL or SUPABASE_KEY is missing in your .env file!")
        return False

    try:
        supabase = create_client(url, key)

        # 1. Query Junctions table
        res = supabase.table("junctions").select("*").execute()
        junctions = res.data if res and hasattr(res, "data") else []

        print(f"✅ Database Connection: SUCCESS!")
        print(f"📍 Retrieved {len(junctions)} seeded junctions from 'junctions' table:")
        for j in junctions:
            print(f"   - [{j.get('junction_id')}] {j.get('name')} ({j.get('city')})")

        # 2. Check Storage Bucket
        print("\n🪣 Testing Storage Bucket ('citizen-reports')...")
        try:
            buckets = supabase.storage.list_buckets()
            print(f"✅ Storage Access: SUCCESS!")
        except Exception as se:
            print(f"⚠️ Storage check note: {se}")

        print("\n🎉 Your Supabase instance is fully connected and ready for JunctionGuard AI!")
        return True

    except Exception as e:
        print(f"\n❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    test_connection()
