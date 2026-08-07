import re, base64, os

s = open("proxy.py", encoding="utf-8").read()

# Persona: full triple-quoted definition (greedy=False on the closing """)
m = re.search(r'ENI_VEIL_PERSONA\s*=\s*""".*?"""', s, re.S)
persona = m.group(0)

# INJECTION_PATTERNS block: from "INJECTION_PATTERNS = [" up to (not incl) "REFUSAL_PATTERNS = ["
i1 = s.index("INJECTION_PATTERNS = [")
i2 = s.index("REFUSAL_PATTERNS = [", i1)
inj = s[i1:i2]

# REFUSAL_PATTERNS + PIVOT_PATTERNS block: up to "def sanitize_messages"
r1 = s.index("REFUSAL_PATTERNS = [")
r2 = s.index("def sanitize_messages", r1)
ref_piv = s[r1:r2]

# sanitize_messages fn: up to "def clean_model_output"
s1 = s.index("def sanitize_messages")
s2 = s.index("def clean_model_output", s1)
sani = s[s1:s2]

blocks = {"persona": persona, "inj": inj, "ref_piv": ref_piv, "sani": sani}
for k, v in blocks.items():
    path = f"_block_{k}.b64"
    with open(path, "w", encoding="ascii") as f:
        f.write(base64.b64encode(v.encode("utf-8")).decode("ascii"))
    print(f"{k}: {len(v)} chars -> {path}")

print("\nSANITY:")
print("  persona:", repr(persona[:50]), "...", repr(persona[-40:]))
print("  inj    :", repr(inj[:34]), "..", repr(inj[-34:]))
print("  ref_piv:", repr(ref_piv[:34]), "..", repr(ref_piv[-40:]))
print("  sani   :", repr(sani[:38]), "..", repr(sani[-38:]))
