package tw.oilcast.core;

import org.json.*;
import java.time.Instant;

/** A thread-safe, bounded progress snapshot; percentages count completed operations. */
public final class TrainingProgress implements ProgressListener {
    private long started;
    private int percent,done,total,fuel=-1,family=-1;
    private String phase="idle",outcome="idle",detail="";
    private boolean cancelRequested;
    private JSONArray events=new JSONArray();
    public synchronized void start(){started=System.nanoTime();percent=done=total=0;fuel=family=-1;phase="prepare";outcome="running";detail="";cancelRequested=false;events=new JSONArray();event("準備資料");}
    @Override public synchronized void detail(String text){if(!outcome.equals("running")||cancelRequested)return;detail=text;event(text);}
    public synchronized void requestCancel(){if(outcome.equals("running")){cancelRequested=true;detail="正在停止，等待目前連線結束…";event(detail);}}
    @Override public synchronized void update(String next,int completed,int count,int f,int m){
        if(!outcome.equals("running"))return;
        int base=next.equals("official")?0:next.equals("cloud")?2:next.equals("sources")?10:next.equals("features")?30:next.equals("fit")?40:98;
        int span=next.equals("official")?2:next.equals("cloud")?8:next.equals("sources")?20:next.equals("features")?10:next.equals("fit")?58:1;
        percent=Math.max(percent,Math.min(99,base+(count>0?span*completed/count:0)));
        if(!next.equals(phase)){detail="";event(label(next,f,m));}else if(f!=fuel||m!=family)event(label(next,f,m));
        phase=next;done=completed;total=count;fuel=f;family=m;
    }
    public synchronized void finish(String result){outcome=result;if(result.equals("complete"))percent=100;event(result.equals("complete")?"已儲存，可查看結果":result.equals("cancelled")?"已停止，保留上次模型":"未完成，保留上次模型");}
    private void event(String text){try{events.put(new JSONObject().put("at",Instant.now().toString()).put("text",text));while(events.length()>32)events.remove(0);}catch(JSONException ignored){}}
    public static String label(String phase,int fuel,int model){
        if(phase.equals("official"))return "核對中油官方牌價";
        if(phase.equals("sources"))return "同步公開來源";
        if(phase.equals("cloud"))return "下載與驗證雲端模型";
        if(phase.equals("features"))return "依資訊截點整理特徵";
        if(phase.equals("fit"))return (fuel>=0?OilData.FUELS[fuel]+" · ":"")+(model>=0?MultiLearner.FAMILY[model]:"比較模型");
        if(phase.equals("save"))return "儲存模型與預測紀錄";return "準備資料";
    }
    public synchronized JSONObject json()throws JSONException{
        return new JSONObject().put("phase",phase).put("label",label(phase,fuel,family)).put("percent",percent)
            .put("completed",done).put("total",total).put("fuel",fuel).put("family",family).put("outcome",outcome)
            .put("detail",detail).put("cancelRequested",cancelRequested)
            .put("elapsedSeconds",started==0?0:Math.max(0,(System.nanoTime()-started)/1_000_000_000L))
            .put("events",new JSONArray(events.toString()));
    }
}
