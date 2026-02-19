import pyodbc
import structlog
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from app.config import get_settings

logger = structlog.get_logger()


class BusyDatabase:
    """Database handler for Busy Accounting .bds files using ODBC."""
    
    def __init__(self):
        self.settings = get_settings()
        self._connection: Optional[pyodbc.Connection] = None
    
    def connect(self) -> pyodbc.Connection:
        """Establish database connection."""
        try:
            conn_str = self.settings.database_connection_string
            self._connection = pyodbc.connect(conn_str, timeout=30)
            logger.info("database_connected", path=self.settings.BDS_FILE_PATH)
            return self._connection
        except pyodbc.Error as e:
            logger.error("database_connection_failed", error=str(e))
            raise
    
    def disconnect(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("database_disconnected")
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor."""
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("database_error", error=str(e))
            raise
        finally:
            if conn:
                conn.close()
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM Master1")
                result = cursor.fetchone()
                logger.info("database_test_successful", master1_count=result[0])
                return True
        except Exception as e:
            logger.error("database_test_failed", error=str(e))
            return False
    
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
            with self.get_cursor() as cursor:
                if vch_type:
                    query = """
                        SELECT 
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
                        LIMIT ?
                    """
                    cursor.execute(query, (party_code, vch_type, limit))
                else:
                    query = """
                        SELECT 
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
                        LIMIT ?
                    """
                    cursor.execute(query, (party_code, limit))
                
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
            with self.get_cursor() as cursor:
                query = """
                    SELECT 
                        Code,
                        Name,
                        PrintName,
                        Phone,
                        Email,
                        GSTNo
                    FROM Master1
                    WHERE Name LIKE ? OR Code LIKE ? OR PrintName LIKE ?
                    ORDER BY Name
                    LIMIT ?
                """
                search_pattern = f"%{search_term}%"
                cursor.execute(query, (search_pattern, search_pattern, search_pattern, limit))
                
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
