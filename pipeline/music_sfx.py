import sys, json, numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import audio as AU
from scipy.io import wavfile
tl = json.load(open("timeline.json")); DUR = tl["DUR"]
AU.SFX["whoosh_s"] = lambda: AU.sfx_whoosh(0.25)
AU.SFX["impact"] = AU.impact
# music: dark modern beat, intro sparse until end of hook, drop at intro start
m = AU.track("x", DUR, 100, [("A", "m"), ("F", "M"), ("C", "M"), ("G", "M")], "dark", drop_at=tl["SC"][1], outro=2.6)
sf = [(t, n, g) for (t, n, g) in tl["SFX"]]
AU.finish(m, sf, "music_sfx.wav", music_gain=0.55)
# separate stems: music only and sfx only for mixing control
m2 = AU.track("x", DUR, 100, [("A", "m"), ("F", "M"), ("C", "M"), ("G", "M")], "dark", drop_at=tl["SC"][1], outro=2.6)
AU.finish(m2, [], "music.wav", music_gain=0.55)
s = AU.Mix(DUR)
for (t, n, g) in sf: s.add(AU.SFX[n](), t, g=g)
o = s.out / max(1e-6, np.abs(s.out).max()) * 0.9
wavfile.write("sfx.wav", AU.SR, (o * 32767).astype(np.int16))
print("ok", DUR)
