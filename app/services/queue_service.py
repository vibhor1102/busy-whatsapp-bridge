"""
Message Queue Service
Handles message queuing, processing, and retry logic.
"""

import asyncio
import httpx
import os
import uuid
import random
from datetime import datetime
from typing import Optional
from app.database.message_queue import message_db
from app.models.schemas import WhatsAppMessage, WhatsAppResponse
from app.services.whatsapp import get_whatsapp_provider
import random
import structlog

logger = structlog.get_logger()


class MessageQueueService:
    """Service for managing message queue operations."""
    
    def __init__(self):
        self._processing = False
        self._worker_task: Optional[asyncio.Task] = None
        self._last_prune_date: Optional[str] = None

    @staticmethod
    def _is_local_file_path(value: Optional[str]) -> bool:
        if not value:
            return False
        return os.path.isabs(value) or value.startswith(".\\") or value.startswith("./")

    @staticmethod
    def _cleanup_local_media(value: Optional[str]):
        if not value:
            return
        if not MessageQueueService._is_local_file_path(value):
            return
        try:
            if os.path.exists(value):
                os.remove(value)
        except Exception as e:
            logger.warning("queue_media_cleanup_failed", path=value, error=str(e))
    
    async def enqueue_invoice_notification(
        self,
        phone: str,
        message: str,
        pdf_url: Optional[str] = None,
        file_name: Optional[str] = None,
        provider: str = "baileys",
        source: str = "busy"
    ) -> dict:
        """Add an invoice notification to the queue."""
        queue_id = message_db.enqueue_message(
            phone=phone,
            message=message,
            pdf_url=pdf_url,
            file_name=file_name,
            provider=provider,
            source=source
        )
        
        return {
            "success": True,
            "queue_id": queue_id,
            "status": "pending",
            "message": "Message queued for delivery"
        }
    
    async def process_single_message(self, message: dict) -> bool:
        """Process a single message from the queue."""
        queue_id = message['id']
        phone = message['phone']
        text = message['message']
        pdf_url = message['pdf_url']
        file_name = message['file_name'] if 'file_name' in message else None
        provider_name = message['provider']
        
        try:
            logger.info(
                "processing_queue_message",
                queue_id=queue_id,
                phone=phone,
                provider=provider_name,
                retry_count=message['retry_count']
            )
            
            # Get the appropriate provider
            provider = get_whatsapp_provider(provider_name)
            
            # Create WhatsApp message
            media_url = pdf_url
            if self._is_local_file_path(pdf_url) and not os.path.exists(pdf_url):
                logger.warning(
                    "queue_media_missing_fallback_to_text",
                    queue_id=queue_id,
                    media_path=pdf_url
                )
                media_url = None

            # PDF Randomization for invoices
            is_invoice = message.get('source') in ['busy', 'invoice']
            original_media_url = pdf_url
            
            if is_invoice and pdf_url:
                pdf_url = await self._handle_pdf_randomization(pdf_url)
                
            # Apply behavioral simulation
            is_reminder = message.get('source') == 'payment_reminder'
            if is_invoice or is_reminder:
                await self._simulate_behavior(provider, phone, text)
            
            if is_invoice:
                text = self._inflate_message(text)

            wa_message = WhatsAppMessage(
                to=phone,
                body=text,
                media_url=pdf_url,
                file_name=file_name,
            )
            
            # Send the message
            result = await provider.send_message(wa_message)
            
            if result.success:
                delivery_status = result.delivery_status
                if not delivery_status:
                    delivery_status = "delivered"
                # Mark as sent
                message_db.mark_message_sent(
                    queue_id=queue_id,
                    message_id=result.message_id or f"msg_{queue_id}",
                    provider=provider_name,
                    delivery_status=delivery_status,
                    resolved_phone=result.normalized_to,
                )
                logger.info(
                    "queue_message_sent",
                    queue_id=queue_id,
                    message_id=result.message_id,
                    delivery_status=delivery_status,
                    phone=result.normalized_to or phone,
                )
                
                # Cleanup: If we created a temporary file for invoice, clean it up always.
                # If it was a legacy local file, clean it up only on success.
                if is_invoice and pdf_url != original_media_url:
                    self._cleanup_local_media(pdf_url)
                else:
                    self._cleanup_local_media(original_media_url)
                return True
            else:
                # Mark as failed - will be retried
                message_db.mark_message_failed(
                    queue_id=queue_id,
                    error_message=result.error or "Unknown error"
                )
                logger.warning(
                    "queue_message_failed",
                    queue_id=queue_id,
                    error=result.error
                )
                # Cleanup temporary file even on failure (retry will create fresh one)
                if is_invoice and pdf_url != original_media_url:
                    self._cleanup_local_media(pdf_url)
                return False
                
        except Exception as e:
            error_msg = f"Processing Error: {str(e)}"
            message_db.mark_message_failed(queue_id=queue_id, error_message=error_msg)
            logger.error(
                "queue_message_exception",
                queue_id=queue_id,
                error=str(e),
                exc_info=True
            )
            return False

    async def _simulate_behavior(self, provider: any, phone: str, message: str):
        """Simulate human-like behavior (reading and typing) before sending."""
        from app.services.anti_spam_service import anti_spam_service
        
        # 1. Reading time (2s base)
        reading_time = anti_spam_service.calculate_reading_time()
        logger.debug("simulating_reading", phone=phone, duration=round(reading_time, 2))
        await asyncio.sleep(reading_time)
        
        # 2. Typing indicator
        typing_duration = anti_spam_service.calculate_typing_duration(len(message))
        if hasattr(provider, 'send_typing_indicator'):
            logger.debug("simulating_typing", phone=phone, duration=round(typing_duration, 2))
            await provider.send_typing_indicator(phone, duration_ms=int(typing_duration * 1000))
        else:
            # Fallback to just sleeping if provider doesn't support indicator (unlikely for Baileys)
            await asyncio.sleep(typing_duration)

    async def _handle_pdf_randomization(self, pdf_url: str) -> str:
        """Download URL PDF, randomize it, and return local path."""
        from app.config import get_roaming_appdata_path
        from app.services.pdf_inflation_service import pdf_inflation_service
        
        temp_dir = get_roaming_appdata_path() / "data" / "temp_media"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = temp_dir / f"invoice_{uuid.uuid4().hex}.pdf"
        
        try:
            if pdf_url.startswith('http'):
                # Download
                async with httpx.AsyncClient() as client:
                    response = await client.get(pdf_url, timeout=30.0)
                    response.raise_for_status()
                    with open(target_path, 'wb') as f:
                        f.write(response.content)
                
                # Randomize in place
                pdf_inflation_service.inflate_pdf(str(target_path), str(target_path), target_multiplier=2.0)
                return str(target_path)
            
            elif self._is_local_file_path(pdf_url):
                # Randomize local file (copy to temp)
                pdf_inflation_service.inflate_pdf(pdf_url, str(target_path), target_multiplier=2.0)
                return str(target_path)
                
        except Exception as e:
            logger.error("pdf_randomization_failed", url=pdf_url, error=str(e))
            if target_path.exists():
                try: os.remove(target_path)
                except: pass
            return pdf_url
            
        return pdf_url

    def _inflate_message(self, text: str) -> str:
        """Apply message inflation/randomization (max 2x)."""
        from app.services.message_inflation_service import message_inflation_service
        return message_inflation_service.inject_invisible_chars(text, target_multiplier=2.0)
    
    async def process_queue_batch(self, batch_size: int = 10):
        """Process a batch of pending messages."""
        messages = message_db.get_pending_messages(limit=batch_size)
        
        if not messages:
            return 0
        
        # 1. Startup Delay (3-10s)
        startup_delay = random.uniform(3.0, 10.0)
        logger.info("queue_batch_startup_delay", delay_seconds=round(startup_delay, 2))
        await asyncio.sleep(startup_delay)

        # 2. Go Online
        provider = get_whatsapp_provider("baileys")
        if hasattr(provider, 'set_presence'):
            await provider.set_presence(online=True)

        logger.info("processing_queue_batch", count=len(messages))
        
        processed = 0
        from app.services.anti_spam_service import anti_spam_service
        for message in messages:
            if not self._processing:
                break
            
            success = await self.process_single_message(message)
            processed += 1
            
            # Small delay between messages to avoid rate limiting
            if processed < len(messages):
                # Use a smaller version of the anti-spam delay
                delay = anti_spam_service.calculate_delay() / 3.0
                await asyncio.sleep(max(1.0, delay))
        
        return processed
    
    async def _worker_loop(self):
        """Background worker loop."""
        logger.info("message_queue_worker_started")
        
        while self._processing:
            try:
                # 1. Prune history once a day
                await self._check_prune_history()

                # 2. Process batch of messages
                processed = await self.process_queue_batch(batch_size=10)
                
                if processed == 0:
                    # No messages to process, sleep longer
                    await asyncio.sleep(5)
                else:
                    # Processed some messages, brief pause
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error("queue_worker_error", error=str(e), exc_info=True)
                await asyncio.sleep(5)
        
        logger.info("message_queue_worker_stopped")

    async def _check_prune_history(self):
        """Check and run message history pruning once a day."""
        today = datetime.now().strftime('%Y-%m-%d')
        if self._last_prune_date == today:
            return

        try:
            logger.info("scheduled_history_prune_start")
            removed_count = message_db.prune_history(days=90)
            self._last_prune_date = today
            if removed_count > 0:
                logger.info("scheduled_history_prune_complete", records_removed=removed_count)
        except Exception as e:
            logger.error("scheduled_history_prune_failed", error=str(e), exc_info=True)
    
    def start_worker(self):
        """Start the background worker."""
        if self._processing:
            logger.warning("queue_worker_already_running")
            return
        
        self._processing = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("message_queue_worker_started")
    
    def stop_worker(self):
        """Stop the background worker."""
        if not self._processing:
            return
        
        self._processing = False
        if self._worker_task:
            self._worker_task.cancel()
        logger.info("message_queue_worker_stopped")
    
    def get_status(self) -> dict:
        """Get current queue status."""
        stats = message_db.get_queue_stats()
        return {
            "worker_running": self._processing,
            **stats
        }
    
    async def force_retry(self, queue_id: int) -> bool:
        """Force immediate retry of a specific message."""
        message = message_db.get_message_by_id(queue_id)
        if not message:
            return False
        
        if message['status'] not in ['pending', 'retrying']:
            return False
        
        return await self.process_single_message(message)
    
    async def retry_dead_letter(self, dead_letter_id: int) -> bool:
        """Move a dead letter message back to queue for retry."""
        return message_db.retry_dead_letter(dead_letter_id)


# Global instance
queue_service = MessageQueueService()
