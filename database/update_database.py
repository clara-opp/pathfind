#!/usr/bin/env python3
"""
update_database.py
Automated database update script - runs API fetchers and rebuilds the database.

Usage:
    python update_database.py [--skip-apis] [--skip-tugo] [--skip-foreign-office]

Options:
    --skip-apis              Skip all API calls, only rebuild database
    --skip-tugo              Skip TuGo API call
    --skip-foreign-office    Skip Foreign Office API call
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
import argparse

# Paths
SCRIPT_DIR = Path(__file__).parent
TUGO_SCRIPT = SCRIPT_DIR / "tugo_api.py"
FOREIGN_OFFICE_SCRIPT = SCRIPT_DIR / "foreign_office_api.py"
NUMBEO_UPDATE_SCRIPT = SCRIPT_DIR / "update_numbeo.py"
DATABASE_SCRIPT = SCRIPT_DIR / "database_final.py"

def print_header(message):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {message}")
    print("=" * 70 + "\n")

def run_script(script_path, description):
    """Run a Python script and handle errors."""
    print_header(f"Running: {description}")
    print(f"Script: {script_path}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    start_time = time.time()
    
    try:
        # Run the script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        elapsed = time.time() - start_time
        print(f"\n✅ SUCCESS ({elapsed:.1f}s)")
        return True
        
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"\n❌ FAILED ({elapsed:.1f}s)")
        print(f"\nError output:")
        if e.stderr:
            print(e.stderr)
        if e.stdout:
            print(e.stdout)
        return False
    
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ FAILED ({elapsed:.1f}s)")
        print(f"Exception: {e}")
        return False

def main():
    """Main orchestration function."""
    parser = argparse.ArgumentParser(
        description="Update travel database with fresh API data"
    )
    parser.add_argument(
        "--skip-apis",
        action="store_true",
        help="Skip all API calls, only rebuild database"
    )
    parser.add_argument(
        "--skip-tugo",
        action="store_true",
        help="Skip TuGo API call"
    )
    parser.add_argument(
        "--skip-foreign-office",
        action="store_true",
        help="Skip Foreign Office API call"
    )
    
    args = parser.parse_args()
    
    # Start
    overall_start = time.time()
    print_header("🌍 DATABASE UPDATE AUTOMATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Step 1: TuGo API
    if not args.skip_apis and not args.skip_tugo:
        if TUGO_SCRIPT.exists():
            results["TuGo API"] = run_script(
                TUGO_SCRIPT,
                "TuGo Travel Warnings API"
            )
        else:
            print(f"⚠️  Warning: {TUGO_SCRIPT} not found, skipping")
            results["TuGo API"] = "skipped"
    else:
        print_header("⏭️  Skipping TuGo API (--skip-tugo or --skip-apis)")
        results["TuGo API"] = "skipped"
    
    # Step 2: Foreign Office API
    if not args.skip_apis and not args.skip_foreign_office:
        if FOREIGN_OFFICE_SCRIPT.exists():
            results["Foreign Office API"] = run_script(
                FOREIGN_OFFICE_SCRIPT,
                "German Foreign Office Travel Warnings"
            )
        else:
            print(f"⚠️  Warning: {FOREIGN_OFFICE_SCRIPT} not found, skipping")
            results["Foreign Office API"] = "skipped"
    else:
        print_header("⏭️  Skipping Foreign Office API (--skip-foreign-office or --skip-apis)")
        results["Foreign Office API"] = "skipped"
    
    # Step 3: Numbeo Update (indices + exchange rates)
    if not args.skip_apis:
        if NUMBEO_UPDATE_SCRIPT.exists():
            results["Numbeo Update"] = run_script(
                NUMBEO_UPDATE_SCRIPT,
                "Numbeo Update (indices + exchange rates)"
            )
        else:
            print(f"⚠️  Warning: {NUMBEO_UPDATE_SCRIPT} not found, skipping")
            results["Numbeo Update"] = "skipped"
    else:
        print_header("⏭️  Skipping Numbeo Update (--skip-apis)")
        results["Numbeo Update"] = "skipped"


    # Step 4: Rebuild Database
    if DATABASE_SCRIPT.exists():
        results["Database Build"] = run_script(
            DATABASE_SCRIPT,
            "Database Builder (database_final.py)"
        )
    else:
        print(f"❌ Error: {DATABASE_SCRIPT} not found!")
        results["Database Build"] = False
    
    # Summary
    overall_time = time.time() - overall_start
    print_header("📊 EXECUTION SUMMARY")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {overall_time / 60:.1f} minutes ({overall_time:.1f}s)\n")
    
    print("Results:")
    for step, result in results.items():
        if result == "skipped":
            status = "⏭️  SKIPPED"
        elif result:
            status = "✅ SUCCESS"
        else:
            status = "❌ FAILED"
        print(f"  {status}  {step}")
    
    # Exit code
    if any(result is False for result in results.values()):
        print("\n⚠️  Some steps failed. Check logs above.")
        sys.exit(1)
    else:
        print("\n🎉 All steps completed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
