import os,glob,json,io,re,torch,warnings; warnings.filterwarnings("ignore")
for d in [os.path.join(os.path.dirname(torch.__file__),"lib")]+glob.glob(os.path.join(os.path.dirname(os.path.dirname(torch.__file__)),"nvidia","*","bin")):
    if os.path.isdir(d): os.add_dll_directory(d); os.environ["PATH"]=d+os.pathsep+os.environ["PATH"]
from pyannote.audio import Pipeline
import librosa
tok=os.environ.get("HF_TOKEN"); assert tok, "HF_TOKEN missing"
src=r"C:\Users\Mahdi\AppData\Local\Temp\claude\C--Claude\b4922477-31d0-4ffd-b5c6-f94db85d4f0c\scratchpad\aug25.mp3"
pipe=Pipeline.from_pretrained("pyannote/speaker-diarization-3.1",token=tok).to(torch.device("cuda"))
y,sr=librosa.load(src,sr=16000,mono=True)
dia=pipe({"waveform":torch.from_numpy(y).unsqueeze(0),"sample_rate":sr},num_speakers=2)
ann=getattr(dia,"speaker_diarization",dia)
segs=[(t.start,t.end,s) for t,_,s in ann.itertracks(yield_label=True)]
print("diarization segments",len(segs))
# words from the faster-whisper run (data/aug25/turns.json has words with s/e)
words=json.load(io.open("data/aug25/turns.json",encoding="utf-8"))["words"]
def spk_at(t):
    best=None;bd=1e9
    for a,b,s in segs:
        if a<=t<=b: return s
        d=min(abs(t-a),abs(t-b)); 
        if d<bd: bd=d;best=s
    return best
for w in words: w["spk_raw"]=spk_at((w["s"]+w["e"])/2)
labels=sorted(set(w["spk_raw"] for w in words))
score={l:0 for l in labels}
for w in words: score[w["spk_raw"]]+=len(re.findall(r'[A-Za-z]{3,}',w["w"]))
medi=max(score,key=score.get)
for w in words: w["spk"]="Medi" if w["spk_raw"]==medi else "Amal"
turns=[];cur=None
for w in words:
    if w["spk"]!=cur or (turns and w["s"]-turns[-1]["e"]>2.5): cur=w["spk"]; turns.append({"spk":cur,"s":w["s"],"e":w["e"],"text":w["w"]})
    else: turns[-1]["e"]=w["e"]; turns[-1]["text"]+=" "+w["w"]
json.dump({"engine":"dialect-ct2 words + pyannote 3.1 diarization","words":words,"turns":turns,"diarization":segs},open("data/aug25/turns.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
open("data/aug25/transcript_turns.txt","w",encoding="utf-8").write("\n".join(f"[{int(t['s']//60):02d}:{int(t['s']%60):02d}] {t['spk']}: {t['text']}" for t in turns))
c={"Medi":0,"Amal":0}
for t in turns: c[t["spk"]]+=1
print("done turns",len(turns),c)
