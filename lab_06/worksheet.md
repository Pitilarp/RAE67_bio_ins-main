# ใบงาน Lab06 — Student

**แบบจำลองทั้งหมดใน runner เป็น proposed course model** โปรแกรมเป็น simulation ไม่ใช่ข้อมูลจาก robot และไม่มี learning

1. เขียน prediction ก่อนรัน: bounce/noise จะกระทบ C0 กับ C1 อย่างไร และ input ใดควรไม่มี onset ใหม่
2. วาด FSM ที่มี normal/interested/happy/afraid/sleepy พร้อม entry/exit guard timeout/recovery
3. ทำตาราง5 state ×8 event (fault, near, clear, touch, button, approach, timeout, idle) โดยเขียน next state หรือ hold ในแต่ละช่อง ตรวจ priority และเหตุการณ์พร้อมกันจาก README
4. เติม TODO ใน student_policy.py แล้วรัน checker จนผ่าน บันทึกหนึ่ง failed case ที่ช่วยแก้ logic

   เลือก `python3 check_submission.py` สำหรับ baseline หรือ `python3 check_submission.py --contract group` สำหรับ mapping ของกลุ่ม: positive button/touch/approach เลือก interested/happy ได้ แต่คง safety/recovery และทุกstateต้องreachable ตรวจ README ก่อนเลือก contract
5. รัน C0/C1 ด้วย3 paired seeds เก็บ all source inputs, both onset count, no-onset count และเหตุผล ไม่คัดเฉพาะ successes
6. ตรวจหนึ่ง event ตั้งแต่ source → debounce/filter → decision → queue → actual apply → motion/RGB onset เทียบ latency จาก CSV กับค่าที่คำนวณเอง
7. ตรวจ near+touch conflict, stale/invalid fallback, quiet-to-sleepy และ recovery button อธิบาย discarded/held/no state change/censored ต่างกันอย่างไร
8. เทียบ raw/event CSV ของ replay และต้นฉบับ หากต่าง ให้หา policy/config/source version ที่เปลี่ยน
9. รายงาน1–2หน้า: prediction, protocol, FSM/table,กราฟ,latency table,ผล C0/C1, negative result และ hardware limitation ห้ามเรียก simulated command onset ว่า physical latency

## ตารางบันทึกของนักศึกษา

| Condition/seed | All external inputs | Both onset | ≤1s both observed | No both onset/status | Max observed latency [s] | State transitions |
|---|---:|---:|---:|---|---:|---:|
| C0/41 | | | | | | |
| C1/41 | | | | | | |
| C0/42 | | | | | | |
| C1/42 | | | | | | |
| C0/43 | | | | | | |
| C1/43 | | | | | | |

| Input ID | Source s | Recognized s | Decision s | Actual apply s | Motion onset s | RGB onset s | Both latency s | Status/reason |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| | | | | | | | | |
| | | | | | | | | |

ก่อนส่งตรวจ: ทุก state/movement/input ครบ; bounds/slewไม่ถูกปิด; latencyใช้ออนเซ็ตจริงของmodel; missingไม่แทน0; ระบุ3seedsเป็นsynthetic replications; ส่งpolicy/config/raw/events/metrics; student filesไม่มีเฉลยหรือข้อมูลผู้สอน

Expected set ของ group: ประกาศ input IDs ก่อนรัน ใช้ชุดเดียวกัน C0/C1 แล้วนับ pass/misses จาก source_outcomes ใน metrics.json ตามชุดนั้น ค่า primary_* ที่ runner สร้างใช้ baseline 7 IDs เสมอ; รายงาน all 10 sources พร้อมเหตุผลไว้ครบ ห้ามปรับ subset หลังเห็นผล
