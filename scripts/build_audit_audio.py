from pathlib import Path
import json,hashlib,subprocess,math,concurrent.futures,statistics
import sys
W=Path(sys.argv[1]);R=Path(__file__).resolve().parents[1];tmp=W/'audit-audio';tmp.mkdir(exist_ok=True)
events=json.loads((W/'audited-events.json').read_text(encoding='utf8'));paths=json.loads((W/'audio-source-map.json').read_text())
sources={}
for e in events:
 sources.setdefault(e['lesson_date'],{})[e['source_sha256']]={'path':paths[e['source_sha256']],'speaker':'Mixed' if 'meeting-recording' in e['source_id'] else e['speaker'],'offset':e['t_start']-e['local_start']}
def run(args):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*args],check=True,capture_output=True)
durations={}
for date,ss in sources.items():
 out=tmp/(date+'.wav');args=[];filters=[]
 for i,s in enumerate(ss.values()):
  args+=['-i',s['path']];filters.append(f'[{i}:a]adelay={round(s["offset"]*1000)}:all=1[a{i}]')
  info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',s['path']]))
  s['end']=s['offset']+float(info['format']['duration'])
 if not out.exists():
  chain=';'.join(filters)+';'+''.join(f'[a{i}]' for i in range(len(ss)))+f'amix=inputs={len(ss)}:duration=longest:normalize=0,alimiter=limit=0.95[out]'
  run(args+['-filter_complex',chain,'-map','[out]','-ar','16000','-ac','1',str(out)])
 durations[date]=max(s['end'] for s in ss.values());print('Prepared',date,flush=True)
jobs={};manifest={};missing=[]
for e in events:
 if e['speaker']!='Medi':continue
 date=e['lesson_date'];ctx=e.get('context',[])
 start=max(0,math.floor(min([e['t_start']]+[r['timeline_start'] for r in ctx if isinstance(r.get('timeline_start'),(int,float))])-1))
 end=math.ceil(max([e['t_end']]+[r['timeline_end'] for r in ctx if isinstance(r.get('timeline_end'),(int,float))])+1)
 if end>durations[date]+2 or end<=start:missing.append(e['id']);continue
 end=min(end,durations[date]);key=(date,start,end)
 name='context-'+hashlib.sha256(str(key).encode()).hexdigest()[:16]+'.mp3';url=f'lessons/{date}/clips/{name}'
 jobs[key]=(R/'docs'/url)
 coverage=[s['speaker'] for s in sources[date].values() if s['offset']<=start and s['end']>=end]
 manifest[e['id']]={'event_id':e['id'],'lesson':date,'source_sha256':e['source_sha256'],'sentence_audio_url':url,'start':start,'end':end,'duration':end-start,'speakers':coverage,'partial_coverage':coverage!=['Mixed'] and set(coverage)!={'Medi','Amal'},'source_bound':True,'contains_displayed_context':True}
def clip(job):
 (date,start,end),out=job;out.parent.mkdir(parents=True,exist_ok=True)
 if not out.exists():run(['-ss',str(start),'-i',str(tmp/(date+'.wav')),'-t',str(end-start),'-ar','16000','-ac','1','-c:a','libmp3lame','-b:a','48k',str(out)])
 return out.relative_to(R).as_posix(),hashlib.sha256(out.read_bytes()).hexdigest()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:hashes=dict(pool.map(clip,jobs.items()))
for c in manifest.values():c['clip_sha256']=hashes['docs/'+c['sentence_audio_url']]
(R/'docs/data/word-bank-clips.json').write_text(json.dumps({'version':3,'clips':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(W/'audit-audio-report.json').write_text(json.dumps({'attached':len(manifest),'unique_clips':len(jobs),'missing':missing,'bytes':sum(p.stat().st_size for p in jobs.values())},indent=2))
print('Complete',len(manifest),'events',len(jobs),'clips; missing',len(missing),flush=True)
