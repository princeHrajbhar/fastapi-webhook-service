"""Database storage layer with async SQLite access."""
import aiosqlite
from typing import Optional, List, Tuple
from datetime import datetime
import os


class Storage:
    """Async SQLite storage for messages."""
    
    def __init__(self, database_url: str):
        # Extract path from sqlite:////data/app.db format
        self.db_path = database_url.replace("sqlite:///", "")
        
    async def init_db(self):
        """Initialize database schema."""
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    from_msisdn TEXT NOT NULL,
                    to_msisdn TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    text TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            await db.commit()
    
    async def is_ready(self) -> bool:
        """Check if database is reachable and schema exists."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
                )
                result = await cursor.fetchone()
                return result is not None
        except Exception:
            return False
    
    async def insert_message(
        self,
        message_id: str,
        from_msisdn: str,
        to_msisdn: str,
        ts: str,
        text: Optional[str]
    ) -> Tuple[bool, bool]:
        """
        Insert message into database.
        
        Returns:
            (success, is_duplicate) tuple
            - success: True if insert succeeded or was duplicate
            - is_duplicate: True if message_id already existed
        """
        created_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (message_id, from_msisdn, to_msisdn, ts, text, created_at)
                )
                await db.commit()
                return (True, False)
        except aiosqlite.IntegrityError:
            # Primary key violation - duplicate message_id
            return (True, True)
    
    async def get_messages(
        self,
        limit: int = 50,
        offset: int = 0,
        from_filter: Optional[str] = None,
        since: Optional[str] = None,
        q: Optional[str] = None
    ) -> Tuple[List[dict], int]:
        """
        Get paginated and filtered messages.
        
        Returns:
            (messages, total_count) tuple
        """
        # Build WHERE clause
        where_clauses = []
        params = []
        
        if from_filter:
            where_clauses.append("from_msisdn = ?")
            params.append(from_filter)
        
        if since:
            where_clauses.append("ts >= ?")
            params.append(since)
        
        if q:
            where_clauses.append("text LIKE ?")
            params.append(f"%{q}%")
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get total count
            count_cursor = await db.execute(
                f"SELECT COUNT(*) as count FROM messages WHERE {where_sql}",
                params
            )
            count_row = await count_cursor.fetchone()
            total = count_row["count"]
            
            # Get paginated data
            data_cursor = await db.execute(
                f"""
                SELECT message_id, from_msisdn, to_msisdn, ts, text
                FROM messages
                WHERE {where_sql}
                ORDER BY ts ASC, message_id ASC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset]
            )
            rows = await data_cursor.fetchall()
            
            messages = [
                {
                    "message_id": row["message_id"],
                    "from": row["from_msisdn"],
                    "to": row["to_msisdn"],
                    "ts": row["ts"],
                    "text": row["text"]
                }
                for row in rows
            ]
            
            return (messages, total)
    
    async def get_stats(self) -> dict:
        """Get message statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Total messages
            cursor = await db.execute("SELECT COUNT(*) as count FROM messages")
            row = await cursor.fetchone()
            total_messages = row["count"]
            
            # Senders count
            cursor = await db.execute(
                "SELECT COUNT(DISTINCT from_msisdn) as count FROM messages"
            )
            row = await cursor.fetchone()
            senders_count = row["count"]
            
            # Top 10 senders
            cursor = await db.execute(
                """
                SELECT from_msisdn, COUNT(*) as count
                FROM messages
                GROUP BY from_msisdn
                ORDER BY count DESC
                LIMIT 10
                """
            )
            rows = await cursor.fetchall()
            messages_per_sender = [
                {"from": row["from_msisdn"], "count": row["count"]}
                for row in rows
            ]
            
            # First and last message timestamps
            cursor = await db.execute(
                "SELECT MIN(ts) as first_ts, MAX(ts) as last_ts FROM messages"
            )
            row = await cursor.fetchone()
            first_message_ts = row["first_ts"]
            last_message_ts = row["last_ts"]
            
            return {
                "total_messages": total_messages,
                "senders_count": senders_count,
                "messages_per_sender": messages_per_sender,
                "first_message_ts": first_message_ts,
                "last_message_ts": last_message_ts
            }
