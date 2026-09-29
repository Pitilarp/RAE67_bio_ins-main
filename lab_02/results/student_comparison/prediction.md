# Prediction before experiment

1. C1 will react fastest to the distance crossing because it compares the raw sensor distance directly against a single threshold.
2. C1 will likely show more false triggers and extra switching because noise can cause repeated threshold crossings.
3. C2 will respond more slowly because the filter smooths the signal and the hysteresis band prevents rapid switching near the threshold.
4. C2 should have fewer false triggers and lower switching count, even though the transition may be delayed.
5. C3 should be smooth and track the target distance, but it may saturate near the command limits when the error is large.
