#!/usr/bin/env python3
"""
Analyze phone numbers for memorable patterns suitable for business use.
"""
import json
from collections import Counter

def load_numbers(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def has_repeated_digit_pattern(number, min_repeat=3):
    """Find numbers with 3+ same digits in a row"""
    patterns = []
    for digit in '0123456789':
        pattern = digit * min_repeat
        if pattern in number:
            patterns.append(pattern)
    return patterns

def has_sequential_pattern(number, length=4):
    """Find sequential digits (ascending/descending)"""
    seq_patterns = []
    # Ascending
    for i in range(10 - length + 1):
        pattern = ''.join(str(i + j) for j in range(length))
        if pattern in number:
            seq_patterns.append((pattern, 'asc'))
    # Descending
    for i in range(10 - length + 1):
        pattern = ''.join(str(i + length - 1 - j) for j in range(length))
        if pattern in number:
            seq_patterns.append((pattern, 'desc'))
    return seq_patterns

def has_palindrome(number, min_len=4):
    """Find palindromic sequences"""
    pals = []
    for i in range(len(number) - min_len + 1):
        for j in range(i + min_len, len(number) + 1):
            substr = number[i:j]
            if substr == substr[::-1] and len(substr) >= min_len:
                pals.append(substr)
    return pals

def has_xy_pattern(number):
    """Find XY-XY-XY or similar repeating patterns"""
    patterns = []
    # Check for AB-AB pattern
    for i in range(len(number) - 3):
        if number[i:i+2] == number[i+2:i+4]:
            patterns.append(number[i:i+4])
    # Check for ABC-ABC pattern
    for i in range(len(number) - 5):
        if number[i:i+3] == number[i+3:i+6]:
            patterns.append(number[i:i+6])
    return patterns

def has_mirror_pattern(number):
    """Find mirror patterns like 123321"""
    mirrors = []
    for i in range(len(number) - 5):
        first = number[i:i+3]
        second = number[i+3:i+6][::-1]
        if first == second:
            mirrors.append(number[i:i+6])
    return mirrors

def ends_with_special(number):
    """Check for special endings"""
    special = ['000', '111', '222', '333', '444', '555', '666', '777', '888', '999',
               '100', '200', '300', '400', '500', '600', '700', '800', '900']
    for sp in special:
        if number.endswith(sp):
            return sp
    return None

def score_memorability(number):
    """Score how memorable a number is"""
    score = 0
    reasons = []
    
    # Repeated digits (strong indicator)
    repeats = has_repeated_digit_pattern(number, 3)
    if repeats:
        score += len(repeats) * 10
        reasons.append(f"Triples: {repeats}")
    
    # Sequential patterns
    seqs = has_sequential_pattern(number, 3)
    if seqs:
        score += len(seqs) * 8
        reasons.append(f"Sequential: {[s[0] for s in seqs]}")
    
    # Palindromes
    pals = has_palindrome(number, 4)
    if pals:
        score += len(pals) * 7
        reasons.append(f"Palindrome: {pals}")
    
    # XY patterns
    xy = has_xy_pattern(number)
    if xy:
        score += len(xy) * 6
        reasons.append(f"XY Pattern: {xy}")
    
    # Mirror patterns
    mirrors = has_mirror_pattern(number)
    if mirrors:
        score += len(mirrors) * 6
        reasons.append(f"Mirror: {mirrors}")
    
    # Special endings
    special_end = ends_with_special(number)
    if special_end:
        score += 5
        reasons.append(f"Special ending: {special_end}")
    
    return score, reasons

def main():
    numbers = load_numbers('phone_numbers.json')
    
    print("=" * 70)
    print("MEMORABLE PHONE NUMBERS ANALYSIS")
    print("=" * 70)
    print(f"Total numbers analyzed: {len(numbers)}\n")
    
    # Score all numbers
    scored_numbers = []
    for num in numbers:
        score, reasons = score_memorability(num)
        if score > 0:
            scored_numbers.append((score, num, reasons))
    
    # Sort by score descending
    scored_numbers.sort(reverse=True)
    
    # Display top picks
    print("TOP 30 MOST MEMORABLE NUMBERS FOR BUSINESS:")
    print("-" * 70)
    
    for i, (score, num, reasons) in enumerate(scored_numbers[:30], 1):
        print(f"\n{i:2d}. {num[:5]}-{num[5:]} (Score: {score})")
        for reason in reasons:
            print(f"    > {reason}")
    
    # Category breakdown
    print("\n" + "=" * 70)
    print("CATEGORY BREAKDOWN")
    print("=" * 70)
    
    categories = {
        'Triple digits (XXX)': [],
        'Sequential (123, 321)': [],
        'Palindromes': [],
        'XY-XY patterns': [],
        'Mirror (123321)': [],
        'Special endings (100, 777)': []
    }
    
    for num in numbers:
        if has_repeated_digit_pattern(num, 3):
            categories['Triple digits (XXX)'].append(num)
        if has_sequential_pattern(num, 3):
            categories['Sequential (123, 321)'].append(num)
        if has_palindrome(num, 4):
            categories['Palindromes'].append(num)
        if has_xy_pattern(num):
            categories['XY-XY patterns'].append(num)
        if has_mirror_pattern(num):
            categories['Mirror (123321)'].append(num)
        if ends_with_special(num):
            categories['Special endings (100, 777)'].append(num)
    
    for cat, nums in categories.items():
        print(f"\n{cat}: {len(nums)} numbers")
        if nums:
            display_nums = [f"{n[:5]}-{n[5:]}" for n in nums[:10]]
            print(f"  Examples: {', '.join(display_nums)}")
            if len(nums) > 10:
                print(f"  ... and {len(nums) - 10} more")
    
    # Best by ending
    print("\n" + "=" * 70)
    print("BEST BY ENDING PATTERN")
    print("=" * 70)
    
    ending_scores = {}
    for num in numbers:
        last4 = num[-4:]
        score, _ = score_memorability(last4)
        if score > 0:
            if last4 not in ending_scores:
                ending_scores[last4] = []
            ending_scores[last4].append(num)
    
    # Sort endings by count and score
    sorted_endings = sorted(ending_scores.items(), 
                           key=lambda x: (len(x[1]), score_memorability(x[0])[0]), 
                           reverse=True)
    
    print("\nMost memorable 4-digit endings:")
    for ending, nums in sorted_endings[:15]:
        score, reasons = score_memorability(ending)
        print(f"  {ending}: {len(nums)} numbers - {reasons[0] if reasons else ''}")
        examples = [f"{n[:5]}-{n[5:]}" for n in nums[:3]]
        print(f"    Examples: {', '.join(examples)}")

if __name__ == '__main__':
    main()
