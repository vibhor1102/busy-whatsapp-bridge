"""
Message Inflation Service

Inflates message size using invisible Unicode characters to:
1. Defy fingerprinting detection
2. Increase message entropy
3. Make bulk detection harder

Target: 3-5x size inflation
"""

import random
import structlog
from typing import List

logger = structlog.get_logger()


class MessageInflationService:
    """
    Service to inflate message size using invisible characters.
    
    Uses various Unicode invisible characters:
    - Zero-width space (ZWSP): \u200B
    - Zero-width non-joiner (ZWNJ): \u200C
    - Zero-width joiner (ZWJ): \u200D
    - Left-to-right mark (LRM): \u200E
    - Right-to-left mark (RLM): \u200F
    - Non-breaking space (NBSP): \u00A0
    - Variation selectors: \uFE00-\uFE0F
    - Combining grapheme joiner: \u034F
    """
    
    # Invisible/zero-width characters
    INVISIBLE_CHARS = [
        '\u200B',  # Zero-width space
        '\u200C',  # Zero-width non-joiner
        '\u200D',  # Zero-width joiner
        '\u200E',  # Left-to-right mark
        '\u200F',  # Right-to-left mark
        '\u00A0',  # Non-breaking space (invisible in most contexts)
        '\u034F',  # Combining grapheme joiner
    ]
    
    # Variation selectors (can be appended to emoji)
    VARIATION_SELECTORS = [chr(i) for i in range(0xFE00, 0xFE10)]
    
    def __init__(self):
        self._enabled = True
    
    def set_enabled(self, enabled: bool):
        """Toggle inflation on/off."""
        self._enabled = enabled
        logger.info("message_inflation_toggled", enabled=enabled)
    
    def calculate_inflation_ratio(self, target_multiplier: float = 3.0) -> float:
        """
        Calculate inflation multiplier.
        
        Args:
            target_multiplier: Target size multiplier (3-5x)
            
        Returns:
            Inflation multiplier to apply
        """
        # Randomize between 2.5x and 5x
        multiplier = random.uniform(2.5, min(5.0, target_multiplier + 1))
        return multiplier
    
    def inject_invisible_chars(
        self,
        text: str,
        target_multiplier: float = 3.0
    ) -> str:
        """
        Inject invisible characters into text to inflate size.
        
        Strategy:
        1. Add invisible chars between words (most effective)
        2. Add invisible chars at end of message
        3. Occasionally replace spaces with non-breaking spaces
        4. Add variation selectors after certain characters
        
        Args:
            text: Original message text
            target_multiplier: Target size multiplier
            
        Returns:
            Inflated text with invisible characters
        """
        if not self._enabled or not text:
            return text
        
        original_length = len(text)
        multiplier = self.calculate_inflation_ratio(target_multiplier)
        
        # Split into words and spaces
        words = text.split(' ')
        result_parts = []
        
        for i, word in enumerate(words):
            result_parts.append(word)
            
            # Add invisible chars between words (not after last word)
            if i < len(words) - 1:
                # Random number of invisible chars: 2-10 per space
                num_invisible = random.randint(2, 10)
                invisible = ''.join(random.choice(self.INVISIBLE_CHARS) 
                                  for _ in range(num_invisible))
                
                # Occasionally use non-breaking space instead of regular space
                if random.random() < 0.1:  # 10% chance
                    result_parts.append('\u00A0' + invisible)
                else:
                    result_parts.append(' ' + invisible)
        
        # Join parts
        result = ''.join(result_parts)
        
        # Add invisible block at end (substantial inflation)
        # This ensures we hit target multiplier even for short messages
        end_invisible_count = int(original_length * (multiplier - 1) * 0.3)
        if end_invisible_count > 0:
            end_invisible = ''.join(random.choice(self.INVISIBLE_CHARS) 
                                   for _ in range(end_invisible_count))
            result += end_invisible
        
        # Add variation selectors to some characters (if applicable)
        result = self._add_variation_selectors(result)
        
        # Verify inflation
        inflated_length = len(result)
        actual_multiplier = inflated_length / original_length if original_length > 0 else 1.0
        
        logger.debug(
            "message_inflated",
            original_length=original_length,
            inflated_length=inflated_length,
            multiplier=round(actual_multiplier, 2)
        )
        
        return result
    
    def _add_variation_selectors(self, text: str) -> str:
        """
        Add variation selectors to certain characters.
        
        This is subtle and won't affect rendering but adds bytes.
        
        Args:
            text: Text to modify
            
        Returns:
            Modified text with variation selectors
        """
        chars = list(text)
        result = []
        
        for char in chars:
            result.append(char)
            
            # Add variation selector after certain characters
            # Only add to letters and digits to avoid breaking emojis
            if char.isalnum() and random.random() < 0.05:  # 5% chance
                vs = random.choice(self.VARIATION_SELECTORS)
                result.append(vs)
        
        return ''.join(result)
    
    def inject_random_whitespace(self, text: str) -> str:
        """
        Add random extra whitespace that won't affect display.
        
        Uses:
        - Multiple regular spaces (collapsed in HTML/WhatsApp)
        - Tab characters
        - Non-breaking spaces
        
        Args:
            text: Original text
            
        Returns:
            Text with extra whitespace
        """
        if not self._enabled:
            return text
        
        words = text.split(' ')
        result_parts = []
        
        for i, word in enumerate(words):
            result_parts.append(word)
            
            if i < len(words) - 1:
                # Random whitespace type
                ws_type = random.choice([' ', '  ', '\t', '\u00A0'])
                result_parts.append(ws_type)
        
        return ''.join(result_parts)
    
    def create_invisible_block(self, size: int) -> str:
        """
        Create a block of invisible characters.
        
        Args:
            size: Number of invisible characters
            
        Returns:
            String of invisible characters
        """
        chars = []
        for _ in range(size):
            # Mix different types of invisible chars
            if random.random() < 0.7:
                # 70% zero-width chars
                chars.append(random.choice(self.INVISIBLE_CHARS))
            else:
                # 30% variation selectors
                chars.append(random.choice(self.VARIATION_SELECTORS))
        
        return ''.join(chars)
    
    def calculate_entropy(self, text: str) -> float:
        """
        Calculate Shannon entropy of text.
        
        Higher entropy = more randomness = harder to fingerprint.
        
        Args:
            text: Text to analyze
            
        Returns:
            Entropy value (0-8 for bytes)
        """
        if not text:
            return 0.0
        
        import math
        
        # Count character frequencies
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # Calculate entropy
        length = len(text)
        entropy = 0.0
        
        for count in char_counts.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def get_inflation_stats(self, original: str, inflated: str) -> dict:
        """
        Get statistics about inflation.
        
        Args:
            original: Original text
            inflated: Inflated text
            
        Returns:
            Dictionary with stats
        """
        original_entropy = self.calculate_entropy(original)
        inflated_entropy = self.calculate_entropy(inflated)
        
        return {
            "original_length": len(original),
            "inflated_length": len(inflated),
            "multiplier": round(len(inflated) / len(original), 2) if original else 0,
            "original_entropy": round(original_entropy, 2),
            "inflated_entropy": round(inflated_entropy, 2),
            "entropy_increase": round(inflated_entropy - original_entropy, 2)
        }


# Global instance
message_inflation_service = MessageInflationService()
