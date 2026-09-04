import json,time,torch
from transformers import pipeline, WhisperForConditionalGeneration, WhisperProcessor
src=r"C:\Users\Mahdi\AppData\Local\Temp\claude\C--Claude\b4922477-31d0-4ffd-b5c6-f94db85d4f0c\scratchpad\aug25.mp3"
t0=time.time(); mid="openai/whisper-large-v3"
model=WhisperForConditionalGeneration.from_pretrained(mid,torch_dtype=torch.float16).to("cuda"); proc=WhisperProcessor.from_pretrained(mid)
gc=model.generation_config
if isinstance(gc.eos_token_id,list): gc.eos_token_id=gc.eos_token_id[0]
gc.forced_decoder_ids=None
p=pipeline("automatic-speech-recognition",model=model,tokenizer=proc.tokenizer,feature_extractor=proc.feature_extractor,device=0,torch_dtype=torch.float16,chunk_length_s=30,return_timestamps=True)
r=p(src,generate_kwargs={"task":"transcribe"})
segs=[{"start":c["timestamp"][0],"end":c["timestamp"][1],"text":c["text"].strip()} for c in r.get("chunks",[])]
json.dump({"engine":"openai/whisper-large-v3 (transformers)","segments":segs},open("data/aug25/whisper_large_v3.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
open("data/aug25/whisper_large_v3.txt","w",encoding="utf-8").write("\n".join(f"[{int((s['start'] or 0)//60):02d}:{int((s['start'] or 0)%60):02d}] {s['text']}" for s in segs))
print("done",len(segs),"chunks",round(time.time()-t0),"s")
