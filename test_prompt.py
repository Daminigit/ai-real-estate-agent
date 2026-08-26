import re
text = "Your visit is confirmed. <<BOOK_VISIT: 2026-08-27 14:00>>"
match = re.search(r'<<BOOK_VISIT:\s*(.*?)>>', text)
if match:
    print("Found:", match.group(1))
