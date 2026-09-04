import json,io,re,numpy as np,torch,warnings,librosa; warnings.filterwarnings("ignore")
from speechbrain.inference.speaker import EncoderClassifier
from sklearn.cluster import KMeans
src=r"C:\Users\Mahdi\AppData\Local\Temp\claude\C--Claude\b4922477-31d0-4ffd-b5c6-f94db85d4f0c\scratchpad\aug25.mp3"
ch=json.load(io.open("data/aug25/whisper_dialectal_8s.json",encoding="utf-8"))["segments"]
segs=[]
for c in ch:
    s,e,t=c["start"] or 0,c["end"],c["text"].strip()
    if not t or e is None or e<=s or e-s>20: continue
    toks=t.split()
    if len(toks)>=4 and len(set(toks))<=2: continue
    segs.append({"s":s,"e":e,"toks":toks})
y,sr=librosa.load(src,sr=16000,mono=True); wav=torch.from_numpy(y)
enc=EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb",run_opts={"device":"cuda:0"})
win,hop=1.5,0.25; T=len(y)/sr; starts=np.arange(0,max(0,T-win),hop); embs=[]
with torch.no_grad():
    for i in range(0,len(starts),64):
        b=torch.stack([wav[int(a*sr):int((a+win)*sr)] for a in starts[i:i+64]]).cuda(); embs.append(enc.encode_batch(b).squeeze(1).cpu().numpy())
X=np.concatenate(embs); X/=np.linalg.norm(X,axis=1,keepdims=True)
speech=np.zeros(len(starts),bool)
for g in segs:
    lo=int(max(0,(g["s"]-win/2)/hop)); hi=int(min(len(starts)-1,(g["e"]-win/2)/hop)); speech[lo:hi+1]=True
lab=KMeans(n_clusters=2,n_init=20,random_state=25).fit(X[speech]).predict(X)
def spk_at(t): return int(lab[int(np.clip((t-win/2)/hop,0,len(lab)-1))])
# assign each token a time by spreading the chunk's tokens evenly, then a speaker
words=[]
for g in segs:
    n=len(g["toks"]); dur=g["e"]-g["s"]
    for i,tk in enumerate(g["toks"]):
        ts=g["s"]+dur*(i+0.5)/n; words.append({"w":tk,"s":round(g["s"]+dur*i/n,2),"e":round(g["s"]+dur*(i+1)/n,2),"c":spk_at(ts)})
score={0:0,1:0}
for w in words: score[w["c"]]+=len(re.findall(r'[A-Za-z]{3,}',w["w"]))
medi=max(score,key=score.get)
for w in words: w["spk"]="Medi" if w["c"]==medi else "Amal"
for i in range(1,len(words)-1):
    if words[i]["spk"]!=words[i-1]["spk"] and words[i-1]["spk"]==words[i+1]["spk"]: words[i]["spk"]=words[i-1]["spk"]
turns=[];cur=None
for w in words:
    if w["spk"]!=cur or (turns and w["s"]-turns[-1]["e"]>2.5): cur=w["spk"]; turns.append({"spk":cur,"s":w["s"],"e":w["e"],"text":w["w"]})
    else: turns[-1]["e"]=w["e"]; turns[-1]["text"]+=" "+w["w"]
json.dump({"engine":"dialect 8-s chunks (complete) + ecapa speech k-means, words spread by time","words":words,"turns":turns},open("data/aug25/turns.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
open("data/aug25/transcript_turns.txt","w",encoding="utf-8").write("\n".join(f"[{int(t['s']//60):02d}:{int(t['s']%60):02d}] {t['spk']}: {t['text']}" for t in turns))
c={"Medi":0,"Amal":0}
for t in turns: c[t["spk"]]+=1
print("done words",len(words),"turns",len(turns),c)
