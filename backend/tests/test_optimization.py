from datetime import datetime,timedelta,timezone
import json
from sqlalchemy import select,func
from test_pr06 import client_db,role
from app.models import VideoSnapshot,AlgorithmConfig,Score
from app.scoring.initialize_configs import read_initial_rules

def test_extras_transaction_and_recalculation(client_db):
 c,engine,factory=client_db
 with factory() as s:
  rules=read_initial_rules()
  for k,v in rules.items():s.add(AlgorithmConfig(config_key=k,config_value=json.dumps(v)))
  s.add(AlgorithmConfig(config_key='up_standards_UP',config_value=json.dumps({k:vs for k,vs in {'play':[1,2,3,4,5],'interact':[.01,.02,.03,.04,.05],'jump_3s':[.1,.2,.3,.4,.5],'progress':[.1,.2,.3,.4,.5],'convert':[.001,.002,.003,.004,.005]}.items()})))
  v=s.get(VideoSnapshot,1);v.publish_date=(datetime.now(timezone.utc)-timedelta(days=20)).date();v.raw_payload={'fields':{'播放量':3,'互动率':.03,'3s跳出率':.3,'平均播放进度':.3,'播转粉率':.003,'排行':['全站']}}
  s.commit()
 role('member');assert c.put('/api/admin/videos/1/extras',json={'difficulty':'S'}).status_code==403
 role('admin')
 body={'difficulty':'S','efficiency':'按时','traffic_ratio':.4}
 response=c.put('/api/admin/videos/1/extras',json=body);assert response.status_code==200,response.text
 score=response.json()['total_score']
 with factory() as s:
  assert s.get(VideoSnapshot,1).raw_payload['fields']['制作难度']=='S'
  assert float(s.scalar(select(Score.score).where(Score.video_snapshot_id==1)))==float(score)
 assert c.put('/api/admin/videos/1/extras',json=body).status_code==200
 with factory() as s:assert s.scalar(select(func.count()).select_from(Score).where(Score.video_snapshot_id==1))==1
 assert c.put('/api/admin/videos/1/extras',json={**body,'traffic_ratio':2}).status_code==422
 with factory() as s:
  cfg=s.scalar(select(AlgorithmConfig).where(AlgorithmConfig.config_key=='up_standards_UP'));s.delete(cfg);s.commit()
 assert c.put('/api/admin/videos/1/extras',json={**body,'difficulty':'A'}).status_code==409
 with factory() as s:assert s.get(VideoSnapshot,1).raw_payload['fields']['制作难度']=='S'

def test_multiselect_age_sort_and_exports(client_db):
 c,_,_=client_db;role('admin')
 assert c.get('/api/scores/filters').json()['directors']==['编导甲']
 assert c.get('/api/member/scores',params={'is_published_15_days':True}).json()['total']==0
 data=c.get('/api/admin/scores',params=[('up_names','UP'),('directors','编导甲'),('sort_by','total_score'),('sort_order','asc')]).json()
 scores=[x['total_score'] for x in data['items']];assert scores==sorted(scores)
 for format in ['csv','xlsx']:
  response=c.get('/api/admin/scores/export',params={'format':format,'up_names':'不存在'})
  assert response.status_code==200
  if format=='csv':assert '播放得分' in response.text
  else:assert response.content.startswith(b'PK')
 role('member');assert c.get('/api/admin/scores/export').status_code==403
