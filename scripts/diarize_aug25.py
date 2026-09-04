import json,io,numpy as np,torch,warnings,librosa; warnings.filterwarnings("ignore")
from speechbrain.inference.speaker import EncoderClassifier
from sklearn.cluster import KMeans
src=r"C:\Users\Mahdi\AppData\Local\Temp\claude\C--Claude\b4922477-31d0-4ffd-b5c6-f94db85d4f0c\scratchpad\aug25.mp3"
y,sr=librosa.load(src,sr=16000,mono=True); wav=torch.from_numpy(y).unsqueeze(0)
enc=EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb",run_opts={"device":"cuda:0"})
d=json.load(io.open('data/aug25/whisper_dialectal_8s.json',encoding='utf-8')); segs=d['segments']
embs=[];keep=[]
for i,s in enumerate(segs):
    st=s['start'] or 0; en=s['end'] if s['end'] and s['end']>st else st+2
    a=wav[:,int(st*sr):int(min(en,st+12)*sr)]
    if a.shape[1]<sr*0.5: continue
    with torch.no_grad(): e=enc.encode_batch(a.cuda()).squeeze().cpu().numpy()
    embs.append(e/np.linalg.norm(e)); keep.append(i)
X=np.stack(embs); lab=KMeans(n_clusters=2,n_init=20,random_state=25).fit_predict(X)
# which cluster is Medi? the one whose chunks contain more English letters / "how do you say"
import re
score={0:0,1:0}
for k,l in zip(keep,lab):
    t=segs[k]['text']; score[l]+=len(re.findall(r'[A-Za-z]{3,}',t))+3*len(re.findall(r'how do (you|i) say|do i know|what\'s',t.lower()))
medi=max(score,key=score.get)
for k,l in zip(keep,lab): segs[k]['speaker']='Medi' if l==medi else 'Amal'
for s in segs: s.setdefault('speaker','?')
json.dump({"engine":d['engine']+" + ecapa 2-speaker clustering","segments":segs},open('data/aug25/whisper_dialectal_8s_spk.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
# turn-merged transcript
lines=[];cur=None
for s in segs:
    if not s['text']: continue
    if s['speaker']!=cur: cur=s['speaker']; lines.append(f"\n{cur}: {s['text']}")
    else: lines[-1]+=" "+s['text']
open('data/aug25/transcript_by_speaker.txt','w',encoding='utf-8').write("".join(lines).strip())
c={'Medi':0,'Amal':0}
for s in segs: c[s['speaker']]=c.get(s['speaker'],0)+1
print('done',c,'turns',len(lines))
