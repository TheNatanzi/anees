import json,time,sys,os,glob,site
for d in glob.glob(os.path.join(site.getsitepackages()[0],"nvidia","*","bin")): os.add_dll_directory(d); os.environ["PATH"]=d+os.pathsep+os.environ["PATH"]
from faster_whisper import WhisperModel
src=r"C:\Users\Mahdi\AppData\Local\Temp\claude\C--Claude\b4922477-31d0-4ffd-b5c6-f94db85d4f0c\scratchpad\aug25.mp3"
t0=time.time()
m=WhisperModel("large-v3",device="cuda",compute_type="float16")
segs,info=m.transcribe(src,language=None,task="transcribe",word_timestamps=True,vad_filter=True,
    initial_prompt="Palestinian Arabic lesson between a tutor and a student, mixed Arabic and English. Keep fillers, hesitations, and self-corrections verbatim.")
out=[];txt=[]
for s in segs:
    out.append({"start":round(s.start,2),"end":round(s.end,2),"text":s.text.strip(),
                "words":[{"w":w.word,"s":round(w.start,2),"e":round(w.end,2),"p":round(w.probability,2)} for w in (s.words or [])]})
    txt.append(f"[{int(s.start//60):02d}:{int(s.start%60):02d}] {s.text.strip()}")
json.dump({"engine":"faster-whisper large-v3","language":info.language,"lang_prob":round(info.language_probability,2),"duration":info.duration,"segments":out},
          open("data/aug25/whisper_large_v3.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
open("data/aug25/whisper_large_v3.txt","w",encoding="utf-8").write("\n".join(txt))
print("done",len(out),"segments","lang",info.language,round(time.time()-t0),"s")
