import json,io,re,numpy as np,torch,warnings,librosa; warnings.filterwarnings("ignore")
from transformers import pipeline, WhisperForConditionalGeneration, WhisperProcessor
from speechbrain.inference.speaker import EncoderClassifier
from sklearn.cluster import KMeans
src=r"C:\Users\Mahdi\AppData\Local\Temp\claude\C--Claude\b4922477-31d0-4ffd-b5c6-f94db85d4f0c\scratchpad\aug25.mp3"
# 1) word timestamps from the dialect model
mid="oddadmix/whisper-large-v3-turbo-arabic-dialectal"
model=WhisperForConditionalGeneration.from_pretrained(mid,torch_dtype=torch.float16).to("cuda"); proc=WhisperProcessor.from_pretrained(mid)
gc=model.generation_config
if isinstance(gc.eos_token_id,list): gc.eos_token_id=gc.eos_token_id[0]
gc.forced_decoder_ids=None
p=pipeline("automatic-speech-recognition",model=model,tokenizer=proc.tokenizer,feature_extractor=proc.feature_extractor,device=0,torch_dtype=torch.float16,chunk_length_s=8,stride_length_s=(1,1),return_timestamps="word")
r=p(src,generate_kwargs={"task":"transcribe"})
words=[{"w":c["text"].strip(),"s":c["timestamp"][0],"e":c["timestamp"][1]} for c in r["chunks"] if c["text"].strip() and c["timestamp"][0] is not None]
for w in words:
    if w["e"] is None or w["e"]<w["s"]: w["e"]=w["s"]+0.3
print("words",len(words))
# 2) speaker embeddings on sliding windows
y,sr=librosa.load(src,sr=16000,mono=True); wav=torch.from_numpy(y)
enc=EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb",run_opts={"device":"cuda:0"})
win,hop=1.5,0.25; T=len(y)/sr; starts=np.arange(0,max(0,T-win),hop)
embs=[]
B=64
with torch.no_grad():
    for i in range(0,len(starts),B):
        batch=torch.stack([wav[int(s*sr):int((s+win)*sr)] for s in starts[i:i+B]]).cuda()
        e=enc.encode_batch(batch).squeeze(1).cpu().numpy(); embs.append(e)
X=np.concatenate(embs); X=X/np.linalg.norm(X,axis=1,keepdims=True)
lab=KMeans(n_clusters=2,n_init=20,random_state=25).fit_predict(X)
def spk_at(t):
    i=int(np.clip((t-win/2)/hop,0,len(lab)-1)); return lab[i]
for w in words: w["c"]=int(spk_at((w["s"]+w["e"])/2))
# 3) which cluster is Medi: more Latin-letter words / "how do you say"
score={0:0,1:0}
for w in words: score[w["c"]]+=len(re.findall(r'[A-Za-z]{3,}',w["w"]))
medi=max(score,key=score.get)
for w in words: w["spk"]="Medi" if w["c"]==medi else "Amal"
# 4) smooth: flip isolated single-word islands
for i in range(1,len(words)-1):
    if words[i]["spk"]!=words[i-1]["spk"] and words[i]["spk"]!=words[i+1]["spk"] and words[i-1]["spk"]==words[i+1]["spk"]: words[i]["spk"]=words[i-1]["spk"]
# 5) turns
turns=[];cur=None
for w in words:
    if w["spk"]!=cur or (turns and w["s"]-turns[-1]["e"]>2.5):
        cur=w["spk"]; turns.append({"spk":cur,"s":w["s"],"e":w["e"],"text":w["w"]})
    else: turns[-1]["e"]=w["e"]; turns[-1]["text"]+=" "+w["w"]
json.dump({"engine":mid+" word-ts + ecapa sliding kmeans","words":words,"turns":turns},open("data/aug25/turns.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
open("data/aug25/transcript_turns.txt","w",encoding="utf-8").write("\n".join(f"[{int(t['s']//60):02d}:{int(t['s']%60):02d}] {t['spk']}: {t['text']}" for t in turns))
c={"Medi":0,"Amal":0}
for t in turns: c[t["spk"]]+=1
print("done turns",len(turns),c)
