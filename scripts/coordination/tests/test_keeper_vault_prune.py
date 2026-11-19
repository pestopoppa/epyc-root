"""2026-11-11: keeper vault() must not re-vault unboundedly: prune to newest 2 versions after a verified tar, and defer
while keep files are <RECENT_S old when a prior verified vault exists. Extracts vault()/prune_vault() from the heredoc and
runs them against temp dirs only (never the real vault)."""
import hashlib, json, os, re, tarfile, tempfile, time, unittest, subprocess, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
KEEPER = os.path.join(os.path.dirname(HERE), "rowflow", "ws58-calendar-keeper-v13.sh")


def load(tmp):
    s = open(KEEPER).read()
    src = s.split("<<'PY'", 1)[1].split("\n", 1)[1].split("\nPY\n")[0]
    body = ""
    for fn in ("sha", "vault", "prune_vault"):
        body += re.search(r"^def %s\(.*?\n(?:(?:    .*|)\n)+" % fn, src, re.M).group(0)
    ns = dict(os=os, json=json, hashlib=hashlib, tarfile=tarfile, subprocess=subprocess, re=re, dt=dt, now=time.time(), RECENT_S=3600,
              FMAX=1 << 29, VMAX=1 << 31, MODE="live", gib=lambda b: "%dB" % b, VAULT=tmp + "/vault/", ST=tmp + "/st/", TRASH=tmp + "/trash", GRM="/workspace/scripts/safety/guarded_rm.sh")
    exec(body, ns)
    return ns


class VaultPrune(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="vp-", dir=os.environ.get("TMPDIR"))
        os.makedirs(self.t + "/st"); os.makedirs(self.t + "/root")
        self.ns = load(self.t); self.f = self.t + "/root/a.txt"

    def write(self, txt, age):
        open(self.f, "w").write(txt); m = time.time() - age; os.utime(self.f, (m, m))

    def vaults(self):
        d = self.t + "/vault/" + dt.datetime.utcfromtimestamp(1e9).strftime("%Y-%m") + "/"
        return sorted(os.listdir(d)) if os.path.isdir(d) else []

    def test_prune_keeps_newest_two_and_defers_recent(self):
        v = self.ns["vault"]
        for i in range(5):
            self.write("v%d" % i, 7200)
            ok, msg = v("nm", self.t + "/root", [self.f], 1e9); self.assertTrue(ok, msg); self.assertIn("VAULTED", msg)
        fs = self.vaults()
        self.assertEqual(sorted(set(re.search(r"\.v(\d+)\.", x).group(1) for x in fs)), ["4", "5"], fs)
        self.assertEqual(len(fs), 6)   # tar, .sha256, .index.json x 2 versions
        self.assertEqual(len(os.listdir(self.t + "/trash")), 9)   # 3 old versions x 3 files reached the trash
        n = len(self.vaults())
        self.write("fresh", 10)   # changed digest, but written <1h ago and a verified vault exists
        ok, msg = v("nm", self.t + "/root", [self.f], 1e9)
        self.assertTrue(ok); self.assertIn("vault deferred: keep files written <1h ago", msg); self.assertEqual(len(self.vaults()), n)

    def test_first_vault_not_deferred_even_if_recent(self):
        self.write("x", 5)
        ok, msg = self.ns["vault"]("nm2", self.t + "/root", [self.f], 1e9)
        self.assertIn("VAULTED", msg)


if __name__ == "__main__":
    unittest.main()
