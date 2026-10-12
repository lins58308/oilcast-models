package tw.oilcast.core;

import java.net.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Public GitHub model reads: no authentication, cookies, upload or remote executable code. */
public final class ModelHttp {
    private static final ScheduledExecutorService WATCH=Executors.newScheduledThreadPool(1,r->{Thread t=new Thread(r,"model-deadline");t.setDaemon(true);return t;});
    private static final ExecutorService CLOSE=Executors.newCachedThreadPool(r->{Thread t=new Thread(r,"model-close");t.setDaemon(true);return t;});
    private static final ConcurrentMap<Thread,HttpURLConnection> ACTIVE=new ConcurrentHashMap<>();
    private ModelHttp(){}
    public static void cancel(Thread owner){HttpURLConnection connection=ACTIVE.get(owner);if(connection!=null)CLOSE.execute(connection::disconnect);}
    public static URL checked(String link)throws Exception{
        URL url=new URL(link);String host=url.getHost().toLowerCase(Locale.ROOT);
        if(!url.getProtocol().equals("https")||url.getUserInfo()!=null||url.getPort()!=-1&&url.getPort()!=443||!Arrays.asList("github.com","raw.githubusercontent.com","release-assets.githubusercontent.com","objects.githubusercontent.com").contains(host))throw new IOException("模型轉址不在允許來源");return url;
    }
    public static byte[] read(String link,int limit,ProgressListener progress)throws Exception{
        URL url=checked(link);Thread caller=Thread.currentThread();long deadline=System.nanoTime()+35_000_000_000L;
        for(int redirects=0;redirects<=4;redirects++){
            if(caller.isInterrupted())throw new InterruptedIOException("已停止模型更新");
            if(System.nanoTime()>deadline)throw new SocketTimeoutException("模型下載逾時");
            HttpURLConnection c=(HttpURLConnection)url.openConnection();c.setConnectTimeout(15000);c.setReadTimeout(20000);c.setInstanceFollowRedirects(false);c.setUseCaches(false);c.setRequestProperty("User-Agent","OilcastTaiwan/3.3.5 (public model reader)");
            ACTIVE.put(caller,c);AtomicBoolean closed=new AtomicBoolean();ScheduledFuture<?> watch=WATCH.scheduleAtFixedRate(()->{if((caller.isInterrupted()||System.nanoTime()>deadline)&&closed.compareAndSet(false,true))CLOSE.execute(c::disconnect);},100,100,TimeUnit.MILLISECONDS);
            try{
                int status=c.getResponseCode();
                if(Arrays.asList(301,302,303,307,308).contains(status)){String next=c.getHeaderField("Location");if(next==null)throw new IOException("模型轉址缺少網址");url=checked(new URL(url,next).toString());continue;}
                if(status!=200)throw new IOException(status==404?"雲端模型尚未發布":"模型服務 HTTP "+status);
                int expected=c.getContentLength();if(expected>limit)throw new IOException("模型檔超過大小限制");
                ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buffer=new byte[16384];int n;
                try(InputStream in=c.getInputStream()){while((n=in.read(buffer))!=-1){if(caller.isInterrupted())throw new InterruptedIOException("已停止模型更新");if(System.nanoTime()>deadline)throw new SocketTimeoutException("模型下載逾時");if(out.size()+n>limit)throw new IOException("模型檔超過大小限制");out.write(buffer,0,n);if(progress!=null){progress.update("cloud",out.size(),expected>0?expected:limit,-1,-1);progress.detail("已下載 "+(out.size()/1024)+" KB，正在檢查雲端模型");}}}
                return out.toByteArray();
            }finally{watch.cancel(false);ACTIVE.remove(caller,c);c.disconnect();}
        }
        throw new IOException("模型轉址次數過多");
    }
}
