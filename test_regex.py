import re

# Test the exact text from your JD
jd_text = "Minimum of 5-7+ years of accounting/finance experience, preferably in a law firm or other professional services environment."
jd_lower = jd_text.lower()

print("="*80)
print("REGEX DIAGNOSTIC TEST")
print("="*80)
print(f"\nOriginal text: '{jd_text}'")
print(f"\nLowercased text: '{jd_lower}'")
print()

# Test range pattern
range_pattern = r'(\d+)\s*(?:[-–—]|to)\s*(\d+)\s*(?:\+)?\s*years?'
range_match = re.search(range_pattern, jd_lower)

print("Testing RANGE pattern:")
print(f"Pattern: {range_pattern}")
if range_match:
    print(f"✓ MATCHED!")
    print(f"  Full match: '{range_match.group()}'")
    print(f"  Group 1 (first number): '{range_match.group(1)}'")
    print(f"  Group 2 (second number): '{range_match.group(2)}'")
    min_val = int(range_match.group(1))
    max_val = int(range_match.group(2))
    result = min(min_val, max_val)
    print(f"  Result: min({min_val}, {max_val}) = {result}")
else:
    print("✗ NO MATCH")

print()

# Test single patterns
single_patterns = [
    (r'(\d+)\+\s*years?', "X+ years"),
    (r'minimum\s+(?:of\s+)?(\d+)\s*years?', "minimum X years"),
    (r'at\s+least\s+(\d+)\s*years?', "at least X years"),
    (r'(\d+)\s*years?\s+(?:of\s+)?(?:experience|exp)', "X years of experience"),
]

print("Testing SINGLE VALUE patterns:")
for pattern, desc in single_patterns:
    matches = re.findall(pattern, jd_lower)
    if matches:
        print(f"\n✓ Pattern '{desc}' MATCHED:")
        print(f"  Pattern: {pattern}")
        print(f"  All matches: {matches}")
        years_found = [int(m) if isinstance(m, str) else int(m[0]) for m in matches]
        print(f"  Years extracted: {years_found}")
        print(f"  Minimum: {min(years_found)}")
    else:
        print(f"\n✗ Pattern '{desc}' - NO MATCH")

print("\n" + "="*80)
