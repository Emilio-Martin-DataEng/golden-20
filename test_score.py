"""Checks for score.match. Usage: python test_score.py  (prints [OK])"""
from score import match

YES = [("4,745,125.35", "4745125.35"), ("49.91%", "49.91"), ("+5.79%", "5.79"),
       ("August 2025 | 5,223,973.95", "2025-08 | 5223973.95"),
       ("tailspin toys | 17,422,095.90", "Tailspin Toys | 17422095.9"),
       ("Lily Code", "Lily Code | 3781278.35")]
NO = [("4,745,126.35", "4745125.35"), ("49.9%", "49.91"),
      ("Wingtip Toys (Birds, IL) | 28,000", "Wingtip Toys (Birds, IL) | 28280.8"),
      ("Someone Else", "Lily Code | 3781278.35"), ("", "1842"), ("about 4.7 million", "4745125.35")]

for a, g in YES:
    assert match(a, g), (a, g)
for a, g in NO:
    assert not match(a, g), (a, g)
print("[OK]")
