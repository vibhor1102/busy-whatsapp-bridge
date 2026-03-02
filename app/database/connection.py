import pyodbc
import structlog
import time
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple
from app.config import get_settings

logger = structlog.get_logger()
pyodbc.pooling = False


class BusyDatabase:
    """Database handler for Busy Accounting .bds files using ODBC."""
    
    def __init__(self):
        self.settings = get_settings()
        self._connection: Optional[pyodbc.Connection] = None
        self._last_test_error: Optional[str] = None
    
    def refresh_settings(self):
        """Refresh settings from config file."""
        get_settings.cache_clear()
        self.settings = get_settings()
        self._connection = None  # Force reconnection on next use
        logger.info("database_settings_refreshed")
        
        # Update reminder config scope
        try:
            from app.services.reminder_config_service import reminder_config_service
            scope_key = reminder_config_service.set_scope(self.settings.BDS_FILE_PATH)
            logger.info("reminder_config_scope_updated", path=self.settings.BDS_FILE_PATH, scope_key=scope_key)
        except Exception as e:
            logger.warning("reminder_config_scope_update_failed", error=str(e))
    
    def connect(self) -> pyodbc.Connection:
        """Establish database connection."""
        conn_str = self.settings.database_connection_string
        last_error: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                self._connection = pyodbc.connect(conn_str, timeout=30)
                logger.info("database_connected", path=self.settings.BDS_FILE_PATH, attempt=attempt)
                return self._connection
            except pyodbc.Error as e:
                last_error = e
                error_text = str(e)
                logger.error("database_connection_failed", error=error_text, attempt=attempt)
                if "Too many client tasks" in error_text and attempt < 3:
                    time.sleep(0.4 * attempt)
                    continue
                raise
        raise last_error  # pragma: no cover
    
    def disconnect(self):
        """Close database connection."""
        if self._connection:
            try:
                self._connection.close()
            except pyodbc.ProgrammingError:
                # Connection may already be closed by an earlier failure path.
                logger.warning("database_already_closed")
            except pyodbc.Error as e:
                logger.warning("database_disconnect_failed", error=str(e))
            self._connection = None
            logger.info("database_disconnected")
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor."""
        conn = None
        cursor = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except pyodbc.Error as e:
            if conn:
                conn.rollback()
            logger.error("database_error", error=str(e))
            raise
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
                if self._connection is conn:
                    self._connection = None
    
    def test_connection_with_error(self, retries: int = 2, delay_seconds: float = 0.35) -> Tuple[bool, Optional[str]]:
        """Test database connectivity with retry and return error context."""
        attempts = max(1, retries + 1)
        last_error: Optional[str] = None

        for attempt in range(1, attempts + 1):
            try:
                with self.get_cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM Master1")
                    result = cursor.fetchone()
                    self._last_test_error = None
                    logger.info("database_test_successful", master1_count=result[0], attempt=attempt)
                    return True, None
            except Exception as e:
                last_error = str(e)
                if attempt < attempts:
                    logger.warning("database_test_retry", attempt=attempt, error=last_error)
                    time.sleep(delay_seconds)
                else:
                    logger.error("database_test_failed", error=last_error, attempts=attempts)

        self._last_test_error = last_error
        return False, last_error

    def test_connection(self) -> bool:
        """Backward-compatible boolean connectivity check."""
        ok, _ = self.test_connection_with_error()
        return ok
    
    def get_party_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Fetch party details from Master1 by phone number."""
        try:
            # Clean phone number - remove spaces and common prefixes
            clean_phone = phone.replace(" ", "").replace("-", "")
            if clean_phone.startswith("+91"):
                clean_phone = clean_phone[3:]
            elif clean_phone.startswith("0"):
                clean_phone = clean_phone[1:]
            
            with self.get_cursor() as cursor:
                # Try exact match first
                query = """
                    SELECT 
                        Code,
                        Name,
                        PrintName,
                        Phone,
                        Email,
                        Address1,
                        Address2,
                        Address3,
                        Address4,
                        GSTNo
                    FROM Master1
                    WHERE Phone LIKE ?
                """
                cursor.execute(query, (f"%{clean_phone}%",))
                row = cursor.fetchone()
                
                if row:
                    columns = [column[0] for column in cursor.description]
                    party_data = dict(zip(columns, row))
                    
                    logger.info(
                        "party_found",
                        phone=phone,
                        code=party_data.get("Code"),
                        name=party_data.get("Name")
                    )
                    return party_data
                else:
                    logger.warning("party_not_found", phone=phone)
                    return None
                    
        except Exception as e:
            logger.error("get_party_error", phone=phone, error=str(e))
            return None
    
    def get_party_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Fetch party details from Master1 by party code."""
        try:
            with self.get_cursor() as cursor:
                query = """
                    SELECT 
                        Code,
                        Name,
                        PrintName,
                        Phone,
                        Email,
                        Address1,
                        Address2,
                        Address3,
                        Address4,
                        GSTNo
                    FROM Master1
                    WHERE Code = ?
                """
                cursor.execute(query, (code,))
                row = cursor.fetchone()
                
                if row:
                    columns = [column[0] for column in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error("get_party_by_code_error", code=code, error=str(e))
            return None
    
    def get_voucher_by_party(
        self, 
        party_code: str, 
        vch_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch recent vouchers for a party from Tran1."""
        try:
            limit = max(1, min(int(limit), 1000))
            with self.get_cursor() as cursor:
                if vch_type:
                    query = """
                        SELECT 
                            TOP {limit}
                            VchCode,
                            VchType,
                            VchNo,
                            VchDate,
                            PartyCode,
                            NetAmt,
                            Narration
                        FROM Tran1
                        WHERE PartyCode = ? AND VchType = ?
                        ORDER BY VchDate DESC
                    """.format(limit=limit)
                    cursor.execute(query, (party_code, vch_type))
                else:
                    query = """
                        SELECT 
                            TOP {limit}
                            VchCode,
                            VchType,
                            VchNo,
                            VchDate,
                            PartyCode,
                            NetAmt,
                            Narration
                        FROM Tran1
                        WHERE PartyCode = ?
                        ORDER BY VchDate DESC
                    """.format(limit=limit)
                    cursor.execute(query, (party_code,))
                
                rows = cursor.fetchall()
                if rows:
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
                return []
                
        except Exception as e:
            logger.error("get_voucher_error", party_code=party_code, error=str(e))
            return []
    
    def search_parties(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search parties by name or code."""
        try:
            limit = max(1, min(int(limit), 1000))
            with self.get_cursor() as cursor:
                query = """
                    SELECT 
                        TOP {limit}
                        Code,
                        Name,
                        PrintName,
                        Phone,
                        Email,
                        GSTNo
                    FROM Master1
                    WHERE Name LIKE ? OR Code LIKE ? OR PrintName LIKE ?
                    ORDER BY Name
                """.format(limit=limit)
                search_pattern = f"%{search_term}%"
                cursor.execute(query, (search_pattern, search_pattern, search_pattern))
                
                rows = cursor.fetchall()
                if rows:
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
                return []
                
        except Exception as e:
            logger.error("search_parties_error", search_term=search_term, error=str(e))
            return []


# Global database instance
db = BusyDatabase()
