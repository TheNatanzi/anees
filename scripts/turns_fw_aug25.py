import os,glob,json,io,re,numpy as np,torch,warnings,librosa; warnings.filterwarnings("ignore")
for d in [os.path.join(os.path.dirname(torch.__file__),"lib")]+glob.glob(os.path.join(os.path.dirname(os.path.dirname(torch.__file__)),"nvidia","*","bin")):
    if os.path.isdir(d): os.add_dll_directory(d); os.environ["PATH"]=d+os.pathsep+os.environ["PATH"]
from faster_whisper import WhisperModel
from speechbrain.inference.speaker import EncoderClassifier
from sklearn.cluster import KMeans
src=r"C:\Users\Mahdi\AppData\Local\Temp\claude\C--Claude\b4922477-31d0-4ffd-b5c6-f94db85d4f0c\scratchpad\aug25.mp3"
m=WhisperModel("models/dialect-ct2",device="cuda",compute_type="float16")
segs,info=m.transcribe(src,task="transcribe",word_timestamps=True,vad_filter=False,condition_on_previous_text=False,beam_size=5,
  initial_prompt="درس عربي فلسطيني بين معلمة وطالب، عربي وإنجليزي مخلوطين.")
words=[]
for s in segs:
    for w in (s.words or []):
        if w.word.strip(): words.append({"w":w.word.strip(),"s":round(w.start,2),"e":round(w.end,2),"p":round(w.probability,2)})
print("words",len(words),"lang",info.language)
y,sr=librosa.load(src,sr=16000,mono=True); wav=torch.from_numpy(y)
enc=EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb",run_opts={"device":"cuda:0"})
win,hop=1.5,0.25; T=len(y)/sr; starts=np.arange(0,max(0,T-win),hop); embs=[]
with torch.no_grad():
    for i in range(0,len(starts),64):
        b=torch.stack([wav[int(s*sr):int((s+win)*sr)] for s in starts[i:i+64]]).cuda(); embs.append(enc.encode_batch(b).squeeze(1).cpu().numpy())
X=np.concatenate(embs); X/=np.linalg.norm(X,axis=1,keepdims=True)
centers=starts+win/2; speech=np.zeros(len(starts),bool)
for w in words:
    lo=int(max(0,(w["s"]-win/2)/hop)); hi=int(min(len(starts)-1,(w["e"]-win/2)/hop)); speech[lo:hi+1]=True
km=KMeans(n_clusters=2,n_init=20,random_state=25).fit(X[speech]); lab=km.predict(X)
print("speech windows",int(speech.sum()),"of",len(starts))
def spk_at(t): return lab[int(np.clip((t-win/2)/hop,0,len(lab)-1))]
for w in words: w["c"]=int(spk_at((w["s"]+w["e"])/2))
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
json.dump({"engine":"dialect-ct2 faster-whisper word-ts + ecapa sliding kmeans","words":words,"turns":turns},open("data/aug25/turns.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
open("data/aug25/transcript_turns.txt","w",encoding="utf-8").write("\n".join(f"[{int(t['s']//60):02d}:{int(t['s']%60):02d}] {t['spk']}: {t['text']}" for t in turns))
c={"Medi":0,"Amal":0}
for t in turns: c[t["spk"]]+=1
print("done turns",len(turns),c)
