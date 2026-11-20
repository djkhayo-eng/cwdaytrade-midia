import numpy as np, subprocess, librosa, json, re, os, soundfile as sf
os.makedirs('al', exist_ok=True)
EXTRA_SAY = json.load(open('say.json')) if os.path.exists('say.json') else {}  # pronúncias extras para o espeak (palavra -> como falar)
SR=16000; HOP=320  # 20ms
lines=open('script.txt').read().strip().split('\n')
words=[]  # (word, para_idx)
for pi,l in enumerate(lines):
    for w in l.split(): words.append((w,pi))
segs=[]; t=0.0; ref=[]
for i,(w,pi) in enumerate(words):
    clean=re.sub(r'[^\wÀ-ú]','',w)
    SAY={'IPO':'i pê ó','Anthropic':'antrópic','Claude':'clóud','Nasdaq':'násdac','SpaceX':'spêicécs','B3':'bê três','BDR':'bê dê érre','hype':'ráipe','ANTH':'a ene tê agá'}
    SAY.update(EXTRA_SAY)
    say=SAY.get(clean, clean)
    f=f'al/w{i}.wav'
    subprocess.run(['espeak-ng','-v','pt-br','-s','150','-w',f,say],check=True)
    y,sr=librosa.load(f,sr=SR)
    yt,idx=librosa.effects.trim(y,top_db=35)
    st=t; ref.append(yt); t+=len(yt)/SR; segs.append((st,t))
    gap=0.0
    if w.endswith(('.',':')): gap=0.30
    elif w.endswith(','): gap=0.18
    if i+1<len(words) and words[i+1][1]!=pi: gap=0.35
    if gap: ref.append(np.zeros(int(gap*SR))); t+=gap
R=np.concatenate(ref)
T,_=librosa.load('voz_raw.wav',sr=SR)
def feat(y):
    m=librosa.feature.mfcc(y=y,sr=SR,n_mfcc=20,hop_length=HOP,n_fft=1024)[1:]
    e=librosa.feature.rms(y=y,hop_length=HOP,frame_length=1024)
    m=np.vstack([m,20*np.log10(e+1e-5)])
    m=(m-m.mean(1,keepdims=True))/(m.std(1,keepdims=True)+1e-6)
    return m
FR=feat(R); FT=feat(T)
print('ref dur',len(R)/SR,'tgt',len(T)/SR, FR.shape, FT.shape)
D,wp=librosa.sequence.dtw(X=FR,Y=FT,metric='cosine',global_constraints=True,band_rad=0.15)
wp=wp[::-1]
# map ref frame -> tgt frame (first occurrence)
m={}
for a,b in wp:
    if a not in m: m[a]=b
def r2t(sec):
    f=int(round(sec*SR/HOP)); f=min(max(f,0),FR.shape[1]-1)
    while f not in m and f>0: f-=1
    return m[f]*HOP/SR
out=[]
for (w,pi),(s,e) in zip(words,segs):
    out.append(dict(w=w,p=pi,s=round(r2t(s),3),e=round(r2t(e),3)))
json.dump(out,open('words.json','w'),ensure_ascii=False,indent=0)
for o in out: print(f"{o['s']:6.2f} {o['e']:6.2f} {o['w']}")
