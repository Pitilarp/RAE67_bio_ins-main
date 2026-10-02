# Prediction before experiment

1. C1 will react fastest to the distance crossing because it compares the raw sensor distance directly against a single threshold.
2. C1 will likely show more false triggers and extra switching because noise can cause repeated threshold crossings.
3. C2 will respond more slowly because the filter smooths the signal and the hysteresis band prevents rapid switching near the threshold.
4. C2 should have fewer false triggers and lower switching count, even though the transition may be delayed.
5. C3 should be smooth and track the target distance, but it may saturate near the command limits when the error is large.

## คำถามก่อนทดลอง

1. เมื่อ noise เพิ่มขึ้น C1 จะมี switching count เปลี่ยนอย่างไร?
   คำตอบ: เดาว่า switching count น่าจะเพิ่มขึ้น เพราะระยะที่มี noise อาจแกว่งข้าม threshold ไปมา
2. C2 ลด false trigger โดยแลกกับ latency หรือ recovery time อย่างไร?
   คำตอบ: คิดว่า C2 น่าจะลด false trigger ได้ แต่ตอบสนองช้าลงเพราะมีการกรองสัญญาณและใช้ hysteresis
3. เมื่อเพิ่ม sensor delay เส้น command จะเลื่อนจาก physical event เท่าใด?
   คำตอบ: คาดว่า command จะช้าตาม delay ที่เพิ่ม เช่น delay 100 ms ก็อาจช้าประมาณ 0.1 วินาที แต่อาจต่างไปนิดหน่อยตามการกรองสัญญาณ
