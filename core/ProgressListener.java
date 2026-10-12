package tw.oilcast.core;

/** Counts completed work, never elapsed-time estimates. Implementations must be fast. */
public interface ProgressListener {
    void update(String phase, int completed, int total, int fuel, int family);
    default void detail(String text) {}
    ProgressListener NONE = (phase, completed, total, fuel, family) -> {};
}
