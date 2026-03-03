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
        self._connections: Dict[str, pyodbc.Connection] = {}
        self._last_test_errors: Dict[str, Optional[str]] = {}
    
    def refresh_settings(self):
        """Refresh settings from config file."""
        get_settings.cache_clear()
        self.settings = get_settings()
        # Force reconnection on next use for all companies
        for conn in self._connections.values():
            try:
                conn.close()
            except Exception:
                pass
        self._connections.clear()
        logger.info("database_settings_refreshed")
        
        # Update reminder config scope
        try:
            from app.services.reminder_config_service import reminder_config_service
            scope_key = reminder_config_service.set_scope(self.settings.BDS_FILE_PATH)
            logger.info("reminder_config_scope_updated", path=self.settings.BDS_FILE_PATH, scope_key=scope_key)
        except Exception as e:
            logger.warning("reminder_config_scope_update_failed", error=str(e))
    
    def connect(self, company_id: str = "default") -> pyodbc.Connection:
        """Establish database connection."""
        conn_str = self.settings.get_database_connection_string(company_id=company_id)
        last_error: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                connection = pyodbc.connect(conn_str, timeout=30)
                self._connections[company_id] = connection
                logger.info("database_connected", company_id=company_id, attempt=attempt)
                return connection
            except pyodbc.Error as e:
                last_error = e
                error_text = str(e)
                logger.error("database_connection_failed", company_id=company_id, error=error_text, attempt=attempt)
                if "Too many client tasks" in error_text and attempt < 3:
                    time.sleep(0.4 * attempt)
                    continue
                raise
        raise last_error  # pragma: no cover
    
    def disconnect(self, company_id: Optional[str] = None):
        """Close database connection."""
        if company_id:
            connection = self._connections.pop(company_id, None)
            if connection:
                try:
                    connection.close()
                except pyodbc.ProgrammingError:
                    # Connection may already be closed by an earlier failure path.
                    logger.warning("database_already_closed", company_id=company_id)
                except pyodbc.Error as e:
                    logger.warning("database_disconnect_failed", company_id=company_id, error=str(e))
                logger.info("database_disconnected", company_id=company_id)
        else:
            for c_id, connection in list(self._connections.items()):
                try:
                    connection.close()
                except Exception as e:
                    logger.warning("database_disconnect_failed", company_id=c_id, error=str(e))
                logger.info("database_disconnected", company_id=c_id)
            self._connections.clear()
    
    @contextmanager
    def get_cursor(self, company_id: str = "default"):
        """Context manager for database cursor."""
        conn = None
        cursor = None
        try:
            conn = self.connect(company_id=company_id)
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except pyodbc.Error as e:
            if conn:
                conn.rollback()
            logger.error("database_error", company_id=company_id, error=str(e))
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
                if self._connections.get(company_id) is conn:
                    self._connections.pop(company_id, None)
    
    def test_connection_with_error(self, company_id: str = "default", retries: int = 2, delay_seconds: float = 0.35) -> Tuple[bool, Optional[str]]:
        """Test database connectivity with retry and return error context."""
        attempts = max(1, retries + 1)
        last_error: Optional[str] = None

        for attempt in range(1, attempts + 1):
            try:
                with self.get_cursor(company_id=company_id) as cursor:
                    cursor.execute("SELECT COUNT(*) FROM Master1")
                    result = cursor.fetchone()
                    self._last_test_errors[company_id] = None
                    logger.info("database_test_successful", company_id=company_id, master1_count=result[0], attempt=attempt)
                    return True, None
            except Exception as e:
                last_error = str(e)
                if attempt < attempts:
                    logger.warning("database_test_retry", company_id=company_id, attempt=attempt, error=last_error)
                    time.sleep(delay_seconds)
                else:
                    logger.error("database_test_failed", company_id=company_id, error=last_error, attempts=attempts)

        self._last_test_errors[company_id] = last_error
        return False, last_error

    def test_connection(self, company_id: str = "default") -> bool:
        """Backward-compatible boolean connectivity check."""
        ok, _ = self.test_connection_with_error(company_id=company_id)
        return ok
    
    def get_party_by_phone(self, phone: str, company_id: str = "default") -> Optional[Dict[str, Any]]:
        """Fetch party details from Master1 by phone number."""
        try:
            # Clean phone number - remove spaces and common prefixes
            clean_phone = phone.replace(" ", "").replace("-", "")
            if clean_phone.startswith("+91"):
                clean_phone = clean_phone[3:]
            elif clean_phone.startswith("0"):
                clean_phone = clean_phone[1:]
            
            with self.get_cursor(company_id=company_id) as cursor:
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
            logger.error("get_party_error", company_id=company_id, phone=phone, error=str(e))
            return None
    
    def get_party_by_code(self, code: str, company_id: str = "default") -> Optional[Dict[str, Any]]:
        """Fetch party details from Master1 by party code."""
        try:
            with self.get_cursor(company_id=company_id) as cursor:
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
            logger.error("get_party_by_code_error", company_id=company_id, code=code, error=str(e))
            return None
    
    def get_voucher_by_party(
        self, 
        party_code: str, 
        vch_type: Optional[str] = None,
        limit: int = 10,
        company_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Fetch recent vouchers for a party from Tran1."""
        try:
            limit = max(1, min(int(limit), 1000))
            with self.get_cursor(company_id=company_id) as cursor:
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
            logger.error("get_voucher_error", company_id=company_id, party_code=party_code, error=str(e))
            return []
    
    def search_parties(self, search_term: str, limit: int = 20, company_id: str = "default") -> List[Dict[str, Any]]:
        """Search parties by name or code."""
        try:
            limit = max(1, min(int(limit), 1000))
            with self.get_cursor(company_id=company_id) as cursor:
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
            logger.error("search_parties_error", company_id=company_id, search_term=search_term, error=str(e))
            return []


# Global database instance
db = BusyDatabase()
