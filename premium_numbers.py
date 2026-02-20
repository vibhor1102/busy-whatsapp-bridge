#!/usr/bin/env python3
"""
Premium memorable phone number selector for business use.
Focuses on patterns that are easy to remember and professional.
"""
import json

def load_numbers(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def analyze_premium_candidates(numbers):
    """Find the absolute best business numbers"""
    candidates = []
    
    for num in numbers:
        reasons = []
        priority = 0
        
        # Check for 3+ consecutive same digits
        for digit in '0123456789':
            if digit * 4 in num:
                reasons.append(f"QUADRUPLE {digit}s (rare!)")
                priority += 50
            elif digit * 3 in num:
                reasons.append(f"Triple {digit}s")
                priority += 30
        
        # Sequential patterns (very memorable)
        seq_4up = ['0123', '1234', '2345', '3456', '4567', '5678', '6789',
                   '9876', '8765', '7654', '6543', '5432', '4321', '3210', '2109']
        seq_3 = ['012', '123', '234', '345', '456', '567', '678', '789',
                 '210', '321', '432', '543', '654', '765', '876', '987']
        
        for seq in seq_4up:
            if seq in num:
                reasons.append(f"4-digit sequence {seq} (excellent!)")
                priority += 40
        
        for seq in seq_3:
            if seq in num:
                reasons.append(f"3-digit sequence {seq}")
                priority += 20
        
        # Palindromes 5+ digits
        for i in range(len(num) - 4):
            for j in range(i + 5, min(i + 8, len(num) + 1)):
                substr = num[i:j]
                if substr == substr[::-1]:
                    reasons.append(f"Palindrome: {substr}")
                    priority += 25
                    break
        
        # XY-XY patterns
        for i in range(len(num) - 3):
            if num[i:i+2] == num[i+2:i+4]:
                reasons.append(f"AB-AB pattern: {num[i:i+4]}")
                priority += 15
        
        # Mirror patterns (123321)
        for i in range(len(num) - 5):
            if num[i:i+3] == num[i+3:i+6][::-1]:
                reasons.append(f"Mirror pattern: {num[i:i+6]}")
                priority += 20
        
        # Double-double patterns (AABB, ABAB)
        for i in range(len(num) - 3):
            if num[i] == num[i+1] and num[i+2] == num[i+3] and num[i] != num[i+2]:
                reasons.append(f"AABB pattern: {num[i:i+4]}")
                priority += 12
        
        if priority > 0:
            candidates.append((priority, num, reasons))
    
    return sorted(candidates, reverse=True)

def main():
    numbers = load_numbers('phone_numbers.json')
    
    print("=" * 80)
    print("PREMIUM MEMORABLE PHONE NUMBERS - BUSINESS RECOMMENDATIONS")
    print("=" * 80)
    print(f"Analyzed {len(numbers)} numbers\n")
    
    candidates = analyze_premium_candidates(numbers)
    
    # Categorize recommendations
    print("TIER 1 - EXCEPTIONAL (Premium business numbers)")
    print("-" * 80)
    tier1 = [c for c in candidates if c[0] >= 50]
    for i, (score, num, reasons) in enumerate(tier1[:10], 1):
        print(f"\n{i:2d}. {num}  [Score: {score}]")
        for r in reasons[:5]:
            print(f"    * {r}")
    
    print("\n\nTIER 2 - EXCELLENT (Strong memorable patterns)")
    print("-" * 80)
    tier2 = [c for c in candidates if 35 <= c[0] < 50]
    for i, (score, num, reasons) in enumerate(tier2[:15], 1):
        print(f"\n{i:2d}. {num}  [Score: {score}]")
        for r in reasons[:4]:
            print(f"    * {r}")
    
    print("\n\nTIER 3 - VERY GOOD (Good patterns for business)")
    print("-" * 80)
    tier3 = [c for c in candidates if 25 <= c[0] < 35]
    for i, (score, num, reasons) in enumerate(tier3[:20], 1):
        print(f"{i:2d}. {num}  [{score}] {', '.join(reasons[:2])}")
    
    # Special categories
    print("\n\n" + "=" * 80)
    print("SPECIAL CATEGORIES")
    print("=" * 80)
    
    # Numbers with 4+ repeated digits
    print("\n>> Numbers with 4+ identical digits in a row (RARE):")
    quad_nums = []
    for num in numbers:
        for digit in '0123456789':
            if digit * 4 in num:
                quad_nums.append((num, digit * 4))
                break
    for num, pattern in quad_nums:
        print(f"   {num}  (contains {pattern})")
    
    # 4-digit sequences
    print("\n>> Numbers with 4-digit sequential patterns:")
    seq4_nums = []
    seq_4up = ['0123', '1234', '2345', '3456', '4567', '5678', '6789',
               '9876', '8765', '7654', '6543', '5432', '4321', '3210']
    for num in numbers:
        for seq in seq_4up:
            if seq in num:
                seq4_nums.append((num, seq))
                break
    for num, seq in sorted(seq4_nums, key=lambda x: x[1]):
        print(f"   {num}  (contains {seq})")
    
    # 5+ digit palindromes
    print("\n>> Numbers with 5+ digit palindromes:")
    pal_nums = []
    for num in numbers:
        pals = []
        for i in range(len(num) - 4):
            for j in range(i + 5, min(i + 9, len(num) + 1)):
                substr = num[i:j]
                if substr == substr[::-1]:
                    pals.append(substr)
        if pals:
            pal_nums.append((num, max(pals, key=len)))
    pal_nums.sort(key=lambda x: len(x[1]), reverse=True)
    for num, pal in pal_nums[:15]:
        print(f"   {num}  (palindrome: {pal})")
    
    # Easy-to-dial patterns
    print("\n>> Easy dial patterns (alternating or repeating):")
    easy_patterns = []
    for num in numbers:
        # ABABAB pattern
        if len(num) >= 6:
            ababab = False
            for i in range(len(num) - 5):
                if num[i:i+2] == num[i+2:i+4] == num[i+4:i+6]:
                    easy_patterns.append((num, f"{num[i:i+2]} repeated 3x"))
                    ababab = True
                    break
            if not ababab:
                # AB-AB-CD-CD
                for i in range(len(num) - 7):
                    if num[i:i+2] == num[i+2:i+4] and num[i+4:i+6] == num[i+6:i+8]:
                        easy_patterns.append((num, f"{num[i:i+2]}-{num[i+4:i+6]} pairs"))
                        break
    
    for num, pattern in easy_patterns[:10]:
        print(f"   {num}  ({pattern})")

if __name__ == '__main__':
    main()
