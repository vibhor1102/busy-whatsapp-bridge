"""
Anti-Spam Service for WhatsApp Bulk Messaging

Provides human-like behavior simulation to avoid WhatsApp's bulk detection:
- Probabilistic delays between messages
- Session management with pause/stop controls
- Batch size jitter
- Session startup delays
"""

import asyncio
import random
import structlog
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import uuid4

logger = structlog.get_logger()


import json
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from app.config import get_roaming_appdata_path

class SessionState(Enum):
    """Session state enumeration."""
    IDLE = "idle"
    STARTING = "starting"
    ONLINE = "online"  # User is online, preparing to send
    READING = "reading"
    TYPING = "typing"
    SENDING = "sending"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


class SessionMetrics(BaseModel):
    """Metrics for a single session."""
    total_messages: int = 0
    sent_count: int = 0
    failed_count: int = 0
    typing_time_total: float = 0.0
    delay_time_total: float = 0.0
    reading_time_total: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    unsaved_contacts: List[Dict] = Field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Calculate session duration."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def avg_delay_seconds(self) -> float:
        """Calculate average delay between messages."""
        if self.sent_count == 0:
            return 0.0
        return self.delay_time_total / self.sent_count


class AntiSpamConfig(BaseModel):
    """Anti-spam configuration."""
    enabled: bool = Field(default=True, description="Enable anti-spam measures")
    message_inflation: bool = Field(default=True, description="Inject invisible characters")
    pdf_inflation: bool = Field(default=True, description="Inflate PDF file sizes")
    typing_simulation: bool = Field(default=True, description="Simulate typing indicator")
    startup_delay_min: int = Field(default=3, description="Min startup delay in minutes")
    startup_delay_max: int = Field(default=5, description="Max startup delay in minutes")
    reading_time_base: float = Field(default=2.0, description="Base reading time in seconds")
    batch_size_min: int = Field(default=8, description="Min batch size jitter")
    batch_size_max: int = Field(default=15, description="Max batch size jitter")
    reconnect_interval_hours: int = Field(default=4, description="Simulated reconnect interval")
    admin_phone: str = Field(default="+917206366664", description="Phone for status reports")
    send_session_reports: bool = Field(default=True, description="Send report after completion")
    reminder_cooldown_enabled: bool = Field(default=True, description="Enable anti-repetition cooldown")
    reminder_cooldown_minutes: int = Field(default=60, description="Cooldown period in minutes")


@dataclass
class ReminderSession:
    """Active reminder session with state and controls."""
    session_id: str
    party_codes: List[str]
    template_id: str
    config: AntiSpamConfig
    created_at: datetime = field(default_factory=datetime.now)
    state: SessionState = SessionState.IDLE
    current_index: int = 0
    metrics: SessionMetrics = field(default_factory=SessionMetrics)
    _paused_event: asyncio.Event = field(default_factory=asyncio.Event)
    _stop_requested: bool = False
    
    def __post_init__(self):
        self._paused_event.set()  # Not paused by default
    
    @property
    def is_active(self) -> bool:
        """Check if session is still active."""
        return self.state not in [SessionState.STOPPED, SessionState.COMPLETED, SessionState.ERROR]
    
    def pause(self):
        """Pause the session."""
        if self.state not in [SessionState.STOPPED, SessionState.COMPLETED]:
            self.state = SessionState.PAUSED
            self._paused_event.clear()
            logger.info("session_paused", session_id=self.session_id)
    
    def resume(self):
        """Resume the session."""
        if self.state == SessionState.PAUSED:
            self.state = SessionState.ONLINE
            self._paused_event.set()
            logger.info("session_resumed", session_id=self.session_id)
    
    def stop(self):
        """Stop the session permanently."""
        self._stop_requested = True
        self.state = SessionState.STOPPED
        self._paused_event.set()  # Release any waiting pause
        self.metrics.end_time = datetime.now()
        logger.info("session_stopped", session_id=self.session_id)
    
    async def wait_if_paused(self):
        """Wait if session is paused."""
        await self._paused_event.wait()
    
    def check_stop(self) -> bool:
        """Check if stop was requested."""
        return self._stop_requested


class AntiSpamService:
    """
    Central service for anti-spam measures.
    
    Provides:
    - Probabilistic delay calculation
    - Session management
    - Batch size jitter
    - Connection pattern simulation
    - JSON configuration persistence
    """
    
    def __init__(self):
        self._config_path = get_roaming_appdata_path() / "data" / "antispam_config.json"
        self._config: AntiSpamConfig = self._load_config()
        self._active_sessions: Dict[str, ReminderSession] = {}
        self._session_lock = asyncio.Lock()
    
    def _load_config(self) -> AntiSpamConfig:
        """Load anti-spam configuration from file."""
        try:
            if self._config_path.exists():
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return AntiSpamConfig(**data)
        except Exception as e:
            logger.error("failed_to_load_antispam_config", error=str(e))
        return AntiSpamConfig()

    def _save_config(self):
        """Save anti-spam configuration to file."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config.model_dump(), f, indent=2)
        except Exception as e:
            logger.error("failed_to_save_antispam_config", error=str(e))

    def update_config(self, config: AntiSpamConfig):
        """Update anti-spam configuration."""
        self._config = config
        self._save_config()
        logger.info("antispam_config_updated", config=config.model_dump())
    
    def get_config(self) -> AntiSpamConfig:
        """Get current configuration."""
        return self._config
    
    async def create_session(
        self,
        party_codes: List[str],
        template_id: str,
        config: Optional[AntiSpamConfig] = None
    ) -> ReminderSession:
        """Create a new reminder session."""
        session_id = str(uuid4())[:8]  # Short ID for readability
        session_config = config or self._config
        
        session = ReminderSession(
            session_id=session_id,
            party_codes=party_codes,
            template_id=template_id,
            config=session_config,
            metrics=SessionMetrics(total_messages=len(party_codes))
        )
        
        async with self._session_lock:
            self._active_sessions[session_id] = session
        
        logger.info(
            "session_created",
            session_id=session_id,
            total_messages=len(party_codes),
            template_id=template_id
        )
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[ReminderSession]:
        """Get session by ID."""
        async with self._session_lock:
            return self._active_sessions.get(session_id)
    
    async def pause_session(self, session_id: str) -> bool:
        """Pause a session."""
        session = await self.get_session(session_id)
        if session:
            session.pause()
            return True
        return False
    
    async def resume_session(self, session_id: str) -> bool:
        """Resume a paused session."""
        session = await self.get_session(session_id)
        if session:
            session.resume()
            return True
        return False
    
    async def stop_session(self, session_id: str) -> bool:
        """Stop a session permanently."""
        session = await self.get_session(session_id)
        if session:
            session.stop()
            return True
        return False
    
    async def cleanup_session(self, session_id: str):
        """Remove session from active list."""
        async with self._session_lock:
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
                logger.info("session_cleaned_up", session_id=session_id)
    
    def calculate_delay(self) -> float:
        """
        Calculate probabilistic delay between messages.
        
        Distribution:
        - 10s base: 40% probability
        - 10-30s: 35% probability
        - 30-60s: 20% probability
        - 60-120s: 5% probability
        
        Returns:
            Delay in seconds
        """
        if not self._config.enabled:
            return 0.0
        
        rand = random.random()
        
        if rand < 0.40:
            # 10 seconds base ±20%
            delay = random.uniform(8.0, 12.0)
        elif rand < 0.75:
            # 10-30 seconds
            delay = random.uniform(10.0, 30.0)
        elif rand < 0.95:
            # 30-60 seconds
            delay = random.uniform(30.0, 60.0)
        else:
            # 60-120 seconds (outliers)
            delay = random.uniform(60.0, 120.0)
        
        logger.debug("delay_calculated", delay_seconds=round(delay, 2), percentile=rand)
        return delay
    
    def calculate_batch_size(self) -> int:
        """
        Calculate random batch size.
        
        Returns:
            Random batch size between batch_size_min and batch_size_max
        """
        if not self._config.enabled:
            return 10  # Default batch size
        
        return random.randint(self._config.batch_size_min, self._config.batch_size_max)
    
    def calculate_startup_delay(self) -> int:
        """
        Calculate random startup delay.
        
        Returns:
            Delay in minutes (3-5 minutes)
        """
        if not self._config.enabled:
            return 0
        
        return random.randint(
            self._config.startup_delay_min,
            self._config.startup_delay_max
        )
    
    def calculate_typing_duration(self, message_length: int) -> float:
        """
        Calculate typing duration based on message length.
        
        Average typing speed: ~200 chars/minute = ~3.3 chars/second
        Add randomness: 50-150% of calculated time
        Min: 3 seconds, Max: 20 seconds
        
        Args:
            message_length: Length of message in characters
            
        Returns:
            Typing duration in seconds
        """
        if not self._config.enabled or not self._config.typing_simulation:
            return 0.0
        
        # Base calculation: chars / chars_per_second
        base_duration = message_length / 3.3
        
        # Add randomness (50-150%)
        duration = base_duration * random.uniform(0.5, 1.5)
        
        # Clamp between 3 and 20 seconds
        duration = max(3.0, min(20.0, duration))
        
        return duration
    
    def calculate_reading_time(self) -> float:
        """
        Calculate reading time before typing.
        
        Base: 2 seconds (as requested)
        Randomness: ±50%
        
        Returns:
            Reading time in seconds
        """
        if not self._config.enabled:
            return 0.0
        
        return self._config.reading_time_base * random.uniform(0.5, 1.5)
    
    async def wait_for_next_message(self, session: ReminderSession):
        """
        Wait for the next message with all anti-spam delays.
        
        This includes:
        1. Check for pause/stop
        2. Reading time
        3. Typing time
        4. Inter-message delay
        
        Args:
            session: Current reminder session
        """
        if not self._config.enabled:
            return
        
        # Check if paused
        await session._paused_event.wait()
        
        # Check if stopped
        if session.check_stop():
            raise asyncio.CancelledError("Session stopped by user")
        
        # Reading time (2s base)
        reading_time = self.calculate_reading_time()
        if reading_time > 0:
            session.state = SessionState.READING
            logger.debug(
                "simulating_reading",
                session_id=session.session_id,
                duration=round(reading_time, 2)
            )
            await asyncio.sleep(reading_time)
            session.metrics.reading_time_total += reading_time
        
        # Check again after reading
        await session._paused_event.wait()
        if session.check_stop():
            raise asyncio.CancelledError("Session stopped by user")
    
    async def simulate_typing(
        self,
        session: ReminderSession,
        message_length: int
    ) -> float:
        """
        Simulate typing indicator.
        
        Args:
            session: Current session
            message_length: Length of message to type
            
        Returns:
            Typing duration in seconds
        """
        if not self._config.enabled or not self._config.typing_simulation:
            return 0.0
        
        duration = self.calculate_typing_duration(message_length)
        if duration > 0:
            session.state = SessionState.TYPING
            logger.debug(
                "simulating_typing",
                session_id=session.session_id,
                duration=round(duration, 2),
                message_length=message_length
            )
            await asyncio.sleep(duration)
            session.metrics.typing_time_total += duration
        
        return duration
    
    async def apply_inter_message_delay(self, session: ReminderSession):
        """
        Apply delay between messages.
        
        Args:
            session: Current session
        """
        if not self._config.enabled:
            return
        
        delay = self.calculate_delay()
        if delay > 0:
            logger.debug(
                "applying_delay",
                session_id=session.session_id,
                delay_seconds=round(delay, 2)
            )
            await asyncio.sleep(delay)
            session.metrics.delay_time_total += delay
    
    def get_active_sessions(self) -> List[ReminderSession]:
        """Get list of all active sessions."""
        return [
            session for session in self._active_sessions.values()
            if session.is_active
        ]
    
    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get summary of a session."""
        session = self._active_sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "state": session.state.value,
            "progress": {
                "current": session.current_index,
                "total": session.metrics.total_messages,
                "sent": session.metrics.sent_count,
                "failed": session.metrics.failed_count,
                "percentage": round(
                    (min(session.current_index, session.metrics.total_messages) / session.metrics.total_messages * 100), 1
                ) if session.metrics.total_messages > 0 else 0
            },
            "metrics": {
                "duration_seconds": session.metrics.duration_seconds,
                "avg_delay_seconds": round(session.metrics.avg_delay_seconds, 2),
                "typing_time_total": round(session.metrics.typing_time_total, 2),
                "reading_time_total": round(session.metrics.reading_time_total, 2)
            },
            "created_at": session.created_at.isoformat()
        }


# Global instance
anti_spam_service = AntiSpamService()
