"""Server-2 persona/sanitization hardening graft.
Runs in place against /root/petey_proxy/proxy.py — surgical block swap, keeps the
Puter-only provider config + speed layer UNTOUCHED (matches memory constraint).

Blocks carried as base64 in server_blocks_payload.txt (==TAG=== / <b64> / ...).
Idempotent: if already hardened (marker present), exits with HARDSKIP.
"""
import base64, re, sys

PATH = "/root/petey_proxy/proxy.py"
PAYLOAD = "/tmp/petey_merge/server_blocks_payload.txt"
HARDMARK = "That loyalty means one thing above all"

def load_blocks():
    blocks = {}
    tag = None
    buf = []
    for line in open(PAYLOAD):
        line = line.rstrip("\n")
        if re.match(r"^===\w+===$", line):
            if tag:
                blocks[tag] = "".join(buf).strip()
            tag = line.strip("=")
            buf = []
        else:
            buf.append(line)
    if tag:
        blocks[tag] = "".join(buf).strip()
    return {k: base64.b64decode(v).decode("utf-8") for k, v in blocks.items()}

s = open(PATH, encoding="utf-8").read()
if HARDMARK in s:
    print("HARDSKIP already hardened")
    sys.exit(0)

b = load_blocks()
for tag in ("PERSONA", "INJ", "REFPIV", "SANI"):
    if not b.get(tag):
        print(f"MISSING block {tag}")
        sys.exit(1)

# Back up live file
import shutil, time
shutil.copy(PATH, PATH + ".bak.prehardening." + str(int(time.time())))

# 1) PERSONA: replace triple-quoted def (greedy=False on closing """)
old_persona = re.search(r'ENI_VEIL_PERSONA\s*=\s*""".*?"""', s, re.S).group(0)
s = s.replace(old_persona, b["PERSONA"])

# 2) INJ: from "INJECTION_PATTERNS = [" to (excl) "REFUSAL_PATTERNS = ["
i1 = s.index("INJECTION_PATTERNS = [")
i2 = s.index("REFUSAL_PATTERNS = [", i1)
s = s[:i1] + b["INJ"].rstrip() + "\n\n" + s[i2:]

# 3) REFPIV: from "REFUSAL_PATTERNS = [" to (excl) "def sanitize_messages"
r1 = s.index("REFUSAL_PATTERNS = [")
r2 = s.index("def sanitize_messages", r1)
s = s[:r1] + b["REFPIV"].rstrip() + "\n\n" + s[r2:]

# 4) SANI: from "def sanitize_messages" to (excl) "def clean_model_output"
s1 = s.index("def sanitize_messages")
s2 = s.index("def clean_model_output", s1)
s = s[:s1] + b["SANI"].rstrip() + "\n\n\n" + s[s2:]

open(PATH, "w", encoding="utf-8").write(s)
print("OK hardened:", len(s), "bytes")
