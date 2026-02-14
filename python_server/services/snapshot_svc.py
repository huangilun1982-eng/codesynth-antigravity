import time
import sqlite3
from database.connection import get_db
from utils.security import validate_project_path, validate_file_path
from .ai_svc import log_ai_event
from utils.logger import server_logger # Import logger

def save_snapshot(request_data: dict) -> dict:
    """保存單一檔案快照 - 帶完整錯誤處理"""
    conn = None
    try:
        req_project_path = request_data.get('project_path')
        req_file_path = request_data.get('file_path')
        req_content = request_data.get('content')
        req_trigger = request_data.get('trigger')

        server_logger.debug(f"收到快照請求: {req_file_path}")
        
        # 1. 驗證專案路徑
        try:
            project_path = validate_project_path(req_project_path)
        except ValueError as e:
            server_logger.error(f"專案路徑驗證失敗: {e}")
            return {"status": "error", "message": f"專案路徑無效: {str(e)}"}
        except Exception as e:
            server_logger.error(f"專案路徑驗證異常: {type(e).__name__}: {e}")
            return {"status": "error", "message": f"路徑驗證錯誤: {str(e)}"}
        
        # 2. 驗證檔案路徑
        try:
            file_path = validate_file_path(req_file_path)
        except ValueError as e:
            server_logger.error(f"檔案路徑驗證失敗: {e}")
            return {"status": "error", "message": f"檔案路徑無效: {str(e)}"}
        except Exception as e:
            server_logger.error(f"檔案路徑驗證異常: {type(e).__name__}: {e}")
            return {"status": "error", "message": f"路徑驗證錯誤: {str(e)}"}
        
        # 3. 檔案大小檢查
        content_size = len(req_content)
        MAX_SIZE = 10 * 1024 * 1024  # 10MB
        if content_size > MAX_SIZE:
            error_msg = f"檔案過大 ({content_size/1024/1024:.1f}MB)，限制 10MB"
            server_logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        # 4. 取得資料庫連接
        try:
            conn, _ = get_db(project_path)
            c = conn.cursor()
        except Exception as e:
            server_logger.error(f"資料庫連接失敗: {type(e).__name__}: {e}")
            return {"status": "error", "message": f"資料庫連接失敗: {str(e)}"}
        
        # [Check Redundancy] 檢查是否與上一版相同
        try:
            c.execute("""
                SELECT content, id FROM history 
                WHERE file_path = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (file_path,))
            last_record = c.fetchone()
            
            if last_record:
                last_content = last_record[0]
                last_id = last_record[1]
                # 簡單字串比對 (對於超大檔案可能需要Hash，但在10MB限制下尚可)
                if last_content == req_content:
                    server_logger.info(f"檔案內容未變更，跳過保存: {file_path} (Last ID: {last_id})")
                    return {"status": "skipped", "version_id": last_id, "message": "Content unchanged"}
        except Exception as e:
            server_logger.warning(f"檢查重複內容失敗，將繼續保存: {e}")

        # 5. 插入資料庫（帶重試機制）
        version_id = None
        for attempt in range(5):
            try:
                c.execute("""INSERT INTO history 
                            (file_path, content, timestamp, trigger, status)
                            VALUES (?, ?, ?, ?, 'pending')""",
                         (file_path, req_content, time.time(), req_trigger))
                conn.commit()
                version_id = c.lastrowid
                server_logger.info(f"已保存快照: {file_path} (version_id: {version_id})")
                break
            except sqlite3.OperationalError as e:
                if attempt < 4 and "locked" in str(e).lower():
                    server_logger.warning(f"資料庫鎖定，重試 {attempt + 1}/5")
                    time.sleep(0.1)
                else:
                    server_logger.error(f"資料庫操作失敗: {e}")
                    raise
            except Exception as e:
                server_logger.error(f"插入資料庫失敗: {type(e).__name__}: {e}")
                raise
        
        # 6. 記錄 AI 事件（非關鍵，失敗不影響主流程）
        try:
            # 只有當真的產生新版本時才記錄
            log_ai_event(
                project_path,
                what_happened=f"用戶修改了 {file_path}",
                current_status="等待測試",
                related_files=file_path
            )
        except Exception as e:
            server_logger.warning(f"AI 事件記錄失敗（不影響主流程）: {e}")
        
        return {"status": "ok", "version_id": version_id}
        
    except Exception as e:
        # 捕獲所有未預期的異常
        error_type = type(e).__name__
        error_msg = str(e)
        server_logger.error(f"save_snapshot 未預期錯誤: {error_type}: {error_msg}")
        
        # 嘗試回滾事務
        if conn:
            try:
                conn.rollback()
                server_logger.debug(f"事務已回滾")
            except Exception as rollback_error:
                server_logger.warning(f"回滾失敗: {rollback_error}")
        
        return {"status": "error", "message": f"保存失敗: {error_type}: {error_msg}"}
        
    finally:
        # 確保關閉連接
        if conn:
            try:
                conn.close()
            except Exception as close_error:
                server_logger.warning(f"關閉連接失敗: {close_error}")

def batch_save_snapshot(request_data: dict) -> dict:
    """批次保存多個檔案快照"""
    conn = None
    try:
        project_path = validate_project_path(request_data['project_path'])
        snapshots = request_data.get('snapshots', [])
        
        if not snapshots:
            return {"status": "error", "message": "沒有要保存的快照"}
        
        conn, _ = get_db(project_path)
        c = conn.cursor()
        
        success_count = 0
        skipped_count = 0
        errors = []
        MAX_SIZE = 10 * 1024 * 1024  # 10MB
        
        for snapshot in snapshots:
            try:
                file_path = validate_file_path(snapshot['file_path'])
                content = snapshot['content']
                trigger = snapshot.get('trigger', 'Batch Scan')
                
                # 檔案大小檢查
                if len(content) > MAX_SIZE:
                    errors.append({
                        'file': file_path,
                        'error': f'檔案過大 ({len(content)/1024/1024:.1f}MB)，限制 10MB'
                    })
                    continue

                # [Check Redundancy] 檢查是否與上一版相同
                try:
                    c.execute("""
                        SELECT content FROM history 
                        WHERE file_path = ? 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    """, (file_path,))
                    last_record = c.fetchone()
                    
                    if last_record and last_record[0] == content:
                        # 內容相同，跳過
                        skipped_count += 1
                        continue
                except Exception as e:
                    # Removed dangerous pass, now logging warning
                    server_logger.warning(f"Batch redundancy check failed for {file_path}: {e}")
                
                # 插入資料庫
                c.execute("""INSERT INTO history 
                            (file_path, content, timestamp, trigger, status)
                            VALUES (?, ?, ?, ?, 'pending')""",
                         (file_path, content, time.time(), trigger))
                
                success_count += 1
                
            except ValueError as e:
                errors.append({
                    'file': snapshot.get('file_path', 'unknown'),
                    'error': str(e)
                })
            except Exception as e:
                errors.append({
                    'file': snapshot.get('file_path', 'unknown'),
                    'error': f'儲存失敗: {str(e)}'
                })
        
        conn.commit()
        
        return {
            'status': 'ok',
            'success_count': success_count,
            'skipped_count': skipped_count,
            'total': len(snapshots),
            'errors': errors
        }
        
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        server_logger.error(f"批次快照失敗: {e}")
        if conn:
            conn.rollback()
        return {"status": "error", "message": "批次保存失敗"}
    finally:
        if conn:
            conn.close()
