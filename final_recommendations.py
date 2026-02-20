#!/usr/bin/env python3
"""
Final business recommendations - organized by use case
"""
import json

def load_numbers(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def main():
    numbers = load_numbers('phone_numbers.json')
    
    print("=" * 80)
    print("FINAL BUSINESS RECOMMENDATIONS - MEMORABLE PHONE NUMBERS")
    print("=" * 80)
    print()
    
    # THE ABSOLUTE BEST
    print("*** TOP 5 - THE ELITE CHOICES ***")
    print("-" * 80)
    print()
    print("1. 9485556788")
    print("   WHY: Triple 5s + 5678 sequence. Reads like '555-6788'")
    print("   PERFECT FOR: Any business, premium service")
    print("   MEMORABILITY: ***** (Triple fives + counting up)")
    print()
    print("2. 8278087655")
    print("   WHY: 8765 countdown sequence. Pattern: 8-7-6-5")
    print("   PERFECT FOR: Tech, modern businesses")
    print("   MEMORABILITY: ***** (Easy countdown pattern)")
    print()
    print("3. 8278012109")
    print("   WHY: 012 sequence + 2109 pattern. Reads smoothly")
    print("   PERFECT FOR: Creative, startup companies")
    print("   MEMORABILITY: ***** (Near-palindrome)")
    print()
    print("4. 9499154320")
    print("   WHY: Counting down 5432 + ends in 20")
    print("   PERFECT FOR: Corporate, established businesses")
    print("   MEMORABILITY: ***** (Classic countdown)")
    print()
    print("5. 9485858492")
    print("   WHY: 85-85 pattern. Reads: '85-85-8492'")
    print("   PERFECT FOR: Sales, marketing firms")
    print("   MEMORABILITY: ***** (Perfect repetition)")
    print()
    
    print("=" * 80)
    print("CATEGORY WINNERS")
    print("=" * 80)
    print()
    
    print("BEST PALINDROME (reads same forwards/backwards):")
    print("  WINNER: 8278118740 or 8278118792")
    print("  Pattern: 781187 (mirror in middle)")
    print("  Alternative: 9466493360 (946649 - longer palindrome)")
    print()
    
    print("BEST TRIPLE DIGIT:")
    print("  WINNER: 9485556788 (555 + 6788)")
    print("  Runner up: 9499246667 (666 - considered lucky in business)")
    print("  Alternative: 9499388810 (888 - lucky in Asian markets)")
    print()
    
    print("BEST SEQUENTIAL:")
    print("  WINNER: 9467894311 (contains 6789)")
    print("  Runner up: 9485556788 (contains 5678)")
    print("  Alternative: 9416543506 (contains 6543)")
    print()
    
    print("BEST REPEATING PATTERN:")
    print("  WINNER: 9499191938 (9191 + 1919)")
    print("  Pattern: '91-91-1938' or '19-19-1938'")
    print("  Alternative: 9485554463 (AABB: 5544)")
    print()
    
    print("=" * 80)
    print("INDUSTRY RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    print("FOR SALES/MARKETING:")
    print("  9485556788 - Triple 5s (555) = 'Call me!'")
    print("  9485858492 - 85-85 repetition")
    print("  9485554463 - AABB pattern 5544")
    print()
    
    print("FOR TECH/STARTUPS:")
    print("  8278087655 - Countdown pattern (8765)")
    print("  8278012109 - 012 sequence")
    print("  9499154320 - 5432 countdown")
    print()
    
    print("FOR LUXURY/PREMIUM:")
    print("  9499388810 - Triple 8s (lucky, prosperous)")
    print("  9499246667 - Triple 6s + sequential pattern")
    print("  9485948880 - Triple 8s")
    print()
    
    print("FOR CONSULTING/PROFESSIONAL:")
    print("  8278118740 - Palindrome 781187")
    print("  8278118792 - Palindrome 781187")
    print("  9499156651 - Palindrome 156651")
    print()
    
    print("FOR CUSTOMER SERVICE:")
    print("  9499151119 - Triple 1s + ends in 19")
    print("  9499152220 - Triple 2s + ends in 20")
    print("  9499153331 - Triple 3s")
    print()
    
    print("=" * 80)
    print("QUICK REFERENCE - BY NUMBER PATTERN")
    print("=" * 80)
    print()
    
    patterns_found = {
        'Triple 0s': [],
        'Triple 1s': [],
        'Triple 2s': [],
        'Triple 3s': [],
        'Triple 4s': [],
        'Triple 5s': [],
        'Triple 6s': [],
        'Triple 7s': [],
        'Triple 8s': [],
        'Triple 9s': [],
    }
    
    for num in numbers:
        for digit in '0123456789':
            if digit * 3 in num:
                key = f'Triple {digit}s'
                if key in patterns_found:
                    patterns_found[key].append(num)
    
    for pattern, nums in sorted(patterns_found.items()):
        if nums:
            print(f"{pattern}:")
            best = sorted(nums, key=lambda x: len([d for d in '0123456789' if d*3 in x]), reverse=True)[:5]
            for n in best:
                print(f"  {n}")
            if len(nums) > 5:
                print(f"  ... and {len(nums)-5} more")
            print()

if __name__ == '__main__':
    main()
