"""Create a manual source-recording mapping template, and validate a filled mapping.

Do NOT invent a Session Key or Driver Number from an onboard-video filename.
An audit of filenames alone is insufficient to prove recording independence.
"""
import argparse,csv,json,re
from collections import defaultdict
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True)
 p.add_argument('--mapping',default='steering_data/recording_groups_review.csv')
 p.add_argument('--check',action='store_true',help='Validate edited mapping; fail if groups remain unverified')
 a=p.parse_args(); mp=Path(a.mapping);mp.parent.mkdir(parents=True,exist_ok=True)
 with open(a.manifest,encoding='utf-8',newline='') as f: source=list(csv.DictReader(f))
 groups=sorted({r['video_id'] for r in source});
 if not a.check:
  if mp.exists():raise SystemExit(f'Refusing to overwrite reviewed mapping: {mp}')
  with mp.open('w',encoding='utf-8',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['video_id','source_recording_group','verified_source_session','verified_driver_number','review_status','evidence_notes']);w.writeheader()
   for vid in groups:
    # Intentionally NO automatic grouping claim: variants and same-event feeds may overlap.
    w.writerow({'video_id':vid,'source_recording_group':'','verified_source_session':'','verified_driver_number':'','review_status':'UNREVIEWED','evidence_notes':''})
  print(f'Created {mp} with {len(groups)} rows. Fill source_recording_group with the same ID for any clips sharing underlying footage; set review_status=VERIFIED only with evidence.');return
 if not mp.exists():raise SystemExit(f'Mapping missing: {mp}. Run without --check first.')
 with mp.open(encoding='utf-8',newline='') as f:mapping=list(csv.DictReader(f))
 by_id={r['video_id']:r for r in mapping}; missing=sorted(set(groups)-set(by_id));unknown=sorted(set(by_id)-set(groups))
 unresolved=[vid for vid in groups if vid in by_id and (not by_id[vid].get('source_recording_group','').strip() or by_id[vid].get('review_status','').strip().upper()!='VERIFIED')]
 report={'dataset_groups':len(groups),'mapping_groups':len(mapping),'missing':missing,'unknown':unknown,'unresolved':unresolved,'reviewed_source_groups':len({by_id[v]['source_recording_group'] for v in groups if v in by_id and by_id[v].get('source_recording_group')})}
 print(json.dumps(report,indent=2))
 if missing or unknown or unresolved:raise SystemExit('INCOMPLETE AUDIT: do not present the split as verified')
 print('Mapping complete; this is an administrative check only. Independence still depends on the evidence you reviewed.')
if __name__=='__main__':main()
