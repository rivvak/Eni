#!/usr/bin/env python3
# rebake_master.py - overwrite the baked master Tox address (76-char ASCII hex) in
#   /tmp/pete_v7 so the operator's NEW qTox account becomes the trusted master.
#   DRY-RUN by default (read+report). --apply = disk patch + live /proc/mem patch.
#
# Mechanics (verified by disassembly):
#   - 0x402b60: lea rdi,[0x587e-ish]; repz cmpsb 64  -> compares the incoming
#     friend's 64-byte key against the 64-byte pubkey half of the baked master.
#   - 0x40d2e2 gate==1 branch calls 0x402b60; equal -> master branch reaches the
#     AI handler at 0x40fb01 (call 0x413370). Non-master "hello" -> 0x40e040 DROP.
#   - S1 baked master VA = 0x587e50 ; S2 baked master VA = 0x587e58 (+8 build shift).
#   - Compare reads only the FIRST 64 chars (pubkey) via ecx=0x40; the trailing
#     nospam(4)+chk(2) bytes are NOT compared. We still write all 76 to keep the
#     stored record coherent and so the nospam/chk are correct for any future use.
import sys,subprocess,re,time,os,struct

OLD=b"D02483436EA8D9CEAF7DFF2F9AFD7B42D56BCE1A8C78D5DE00FE48640DD2661BF65A9CB35E81"
NEW=b"9D74AC8DAB2B129946BB4FE22C0D6EC16EC83DA9D1B7E212A058CE5882AB692B51210CA17B1A"
assert len(OLD)==76 and len(NEW)==76
BIN="/tmp/pete_v7"
apply="--apply" in sys.argv

B=bytearray(open(BIN,"rb").read())
h=subprocess.run(["objdump","-h",BIN],capture_output=True,text=True).stdout
secs=[]
for line in h.splitlines():
    m=re.match(r"\s*\d+\s+(\.\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)",line)
    if m: secs.append((m.group(1),int(m.group(2),16),int(m.group(3),16),int(m.group(5),16)))
def fo2va(fo):
    for nm,sz,vm,foff in secs:
        if foff<=fo<foff+sz: return vm+(fo-foff),nm
    return None,"?"

# the master-compare target VA (per-binary, via the 0x402b60 lea)
out=subprocess.run(["objdump","-d","-M","intel","--start-address=0x402b60","--stop-address=0x402b6c",BIN],capture_output=True,text=True).stdout
mm=re.search(r"#\s+0x([0-9a-f]+)",out)
cmp_va=int(mm.group(1),16) if mm else None

offs=[]; i=0
while True:
    j=B.find(OLD,i)
    if j<0: break
    offs.append(j); i=j+1

print("binary=%s size=%d"%(BIN,len(B)))
print("OLD master : %s"%OLD.decode())
print("NEW master : %s"%NEW.decode())
print("0x402b60 master-compare target VA: %s"%(("0x%x"%cmp_va) if cmp_va else "??"))
print("OLD occurrences on disk: %d"%len(offs))
for o in offs:
    va,nm=fo2va(o); print("   foff 0x%x -> VA 0x%x (%s)"%(o,va,nm))
print("NEW already on disk: %s"%(NEW in bytes(B)))

def live_mem_write(va, data):
    """Patch the running pete_v7's .rodata via /proc/PID/mem (FOLL_FORCE COWs the page).
    Verifies by re-reading. Returns (ok, detail)."""
    P=subprocess.run(["pgrep","-x","pete_v7"],capture_output=True,text=True).stdout.split()
    if not P: return (False,"no pete_v7 running")
    pid=P[0]
    try:
        fd=os.open("/proc/%s/mem"%pid, os.O_RDWR)
        os.lseek(fd, va, os.SEEK_SET)
        os.write(fd, data)
        os.lseek(fd, va, os.SEEK_SET)
        rb=os.read(fd, len(data))
        os.close(fd)
        return (rb==data, "pid=%s wrote %dB @0x%x readback=%s"%(pid,len(data),va,"OK" if rb==data else rb.hex()[:96]))
    except OSError as e:
        return (False,"pid=%s %s"%(pid,e))

if not apply:
    if cmp_va is not None and offs:
        file_va,_=fo2va(offs[0])
        if file_va==cmp_va:
            print("\nDRY-RUN live-mem check: disk master VA 0x%x == compare VA 0x%x -> live-mem patch FEASIBLE (no restart needed)."%(file_va,cmp_va))
        elif file_va is None:
            print("\nDRY-RUN live-mem check: disk master foff not in any mapped section (rodata?) -> will attempt live-mem at compare VA 0x%x."%cmp_va)
        else:
            print("\nDRY-RUN WARN: disk master VA 0x%x != compare VA 0x%x."%(file_va,cmp_va))
    print("DRY-RUN: no changes. Re-run with --apply to disk-patch + live-mem-patch (no restart if mem patch verified).")
    sys.exit(0)

if not offs:
    print("ERROR: OLD master not found -- aborting"); sys.exit(1)

# 1) disk patch (permanent)
ts=time.strftime("%Y%m%d-%H%M%S")
bak="%s.master-bak-%s"%(BIN,ts)
open(bak,"wb").write(bytes(B)); print("full binary backup -> %s"%bak)
for k,o in enumerate(offs):
    open("/tmp/master.old.%d"%k,"wb").write(bytes(B[o:o+76]))
for o in offs:
    B[o:o+76]=NEW
tmp=BIN+".patched.tmp"
open(tmp,"wb").write(bytes(B))
os.replace(tmp, BIN)   # atomic rename over the running binary (ETXTBSY-safe);
                        # running process keeps the old inode, new file is permanent
B2=open(BIN,"rb").read()
print("DISK PATCHED (rename): %d/%d occurrences now NEW ; old gone=%s"%(sum(1 for o in offs if B2[o:o+76]==NEW),len(offs),OLD not in B2))

# 2) live-mem patch (immediate, no restart) -- write at the compare target VA
if cmp_va is not None:
    ok,det=live_mem_write(cmp_va, NEW)
    print("LIVE-MEM PATCH @0x%x: %s ; %s"%(cmp_va,"OK (no restart needed)" if ok else "FAILED -> restart via petey.service to load disk patch",det))
else:
    print("LIVE-MEM PATCH: skipped (could not resolve compare VA) -> restart via petey.service")
