import tw.oilcast.core.*;
import org.json.*;
import java.time.*;
import java.nio.file.*;

public final class VerifyOutput {
    public static void main(String[] args)throws Exception{
        Path root=Path.of(args[0]),output=Path.of(args[1]);
        JSONObject envelope=new JSONObject(Files.readString(output.resolve("envelope.json")));
        CloudModelPackage.validate(Files.readAllBytes(output.resolve("model.json")),envelope,CloudModelPackage.publicKey(Files.readString(root.resolve("model-public.txt"))),"oilcast-model-v1",Instant.now(),false);
        System.out.println("Production model verified with the App's pinned public key");
    }
}
