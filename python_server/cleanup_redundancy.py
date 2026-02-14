import sqlite3
import os
import shutil
import sys

def get_db_path():
    # Try current directory first
    current = os.getcwd()
    if os.path.exists(os.path.join(current, "codesynth_history.db")):
        return os.path.join(current, "codesynth_history.db")
    
    # Try parent directory
    parent = os.path.dirname(current)
    if os.path.exists(os.path.join(parent, "codesynth_history.db")):
        return os.path.join(parent, "codesynth_history.db")
        
    return None

def normalize_path(path):
    return os.path.normcase(path)

def cleanup_database():
    print(f"--- CodeSynth Database Cleanup Tool ---")
    
    db_path = get_db_path()
    if not db_path:
        print(f"Error: 'codesynth_history.db' not found in current or parent directory.")
        print(f"Please run this script from the project root or python_server directory.")
        return

    print(f"Target Database: {db_path}")
    backup_path = db_path + ".cleanup_bak"

    # 1. Backup
    print(f"[1/4] Backing up database...")
    try:
        shutil.copy(db_path, backup_path)
        print(f"      Backup saved to {os.path.basename(backup_path)}")
    except IOError as e:
        print(f"Error creating backup: {e}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        # 2. Normalize Paths
        print(f"[2/4] Normalizing file paths...")
        c.execute("SELECT id, file_path FROM history")
        rows = c.fetchall()
        
        updated_count = 0
        for row_id, raw_path in rows:
            norm_path = normalize_path(raw_path)
            if raw_path != norm_path:
                c.execute("UPDATE history SET file_path = ? WHERE id = ?", (norm_path, row_id))
                updated_count += 1
        
        if updated_count > 0:
            conn.commit()
        print(f"      Normalized {updated_count} file paths.")

        # 3. Remove Consecutive Duplicates
        print(f"[3/4] Scanning for redundant content versions...")
        
        # Get all files
        c.execute("SELECT DISTINCT file_path FROM history")
        files = [r[0] for r in c.fetchall()]
        
        deleted_count = 0
        
        for file_path in files:
            # Get all versions for this file, ordered by time
            c.execute("SELECT id, content FROM history WHERE file_path = ? ORDER BY timestamp ASC, id ASC", (file_path,))
            versions = c.fetchall()
            
            if not versions:
                continue
                
            prev_content = None
            
            for v in versions:
                v_id = v[0]
                content = v[1]
                
                if prev_content is not None and content == prev_content:
                    # Found duplicate
                    c.execute("DELETE FROM history WHERE id = ?", (v_id,))
                    deleted_count += 1
                else:
                    prev_content = content
                    
        if deleted_count > 0:
            conn.commit()
        print(f"      Deleted {deleted_count} redundant versions.")

        # 4. Vacuum
        print(f"[4/4] Optimizing database size...")
        c.execute("VACUUM")
        print("      Database optimized.")

    except Exception as e:
        print(f"Error during cleanup: {e}")
        print("Restoring backup...")
        conn.close()
        shutil.copy(backup_path, db_path)
        print("Backup restored.")
        return

    conn.close()
    print("--- CLEANUP SUCCESSFUL ---")
    print("Please refresh the CodeSynth cockpit.")

if __name__ == "__main__":
    cleanup_database()
