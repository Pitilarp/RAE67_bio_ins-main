# ใบงาน Lab 05 — Prediction, timing, evidence

ฉบับพิมพ์: [Word](Lab05_Student_Worksheet_TH.docx) / [PDF](Lab05_Student_Worksheet_TH.pdf)

ชื่อ/รหัส________________ กลุ่ม________ วันที่________

**ขอบเขต:** main runner เป็น proposed course model ใช้ scheduled stimulus และ kinematic body; contact demo ใช้ synthetic signals ไม่ใช่ ALCS terrain experiment ของ paper

## 1. ก่อนรัน: hypothesis และ architecture (10 นาที)

1. วาด S→controller→R_used→φ/stride→CPG→decoder→body ของ Lab แล้ววงจุดที่ยังไม่มี independent sensory feedback
2. เขียน hypothesis1 ข้อสำหรับ B1 เทียบ B2 พร้อมตัวชี้วัดและทิศทางที่คาด เช่น TV, latency/recovery, segmentfrequency หลีกเลี่ยงคำว่า “ดีขึ้น” โดยไม่มี metric
3. B3 ตัดอะไรออกจาก B2? สิ่งใดที่ยังคงมี memory?
4. ตาราง provenance: source equation1 รายการ, proposedcourseequation1 รายการ, expectedmeasurement1 รายการ และ metric ที่วัดไม่ได้ 1 รายการ

## 2. รัน comparison และตรวจเวลา (15 นาที)

รัน comparison ตาม README เปิด report เลือก B2 เลื่อน timeline ไป 10.00/10.05s แล้วเปิด B2_states.csv/B2_intervals.csv เพื่อยืนยัน

| command/input time | state end time | H_start | H_end | R_used | φที่ใช้ | stride_half ที่ใช้ |
|---|---|---|---|---|---|---|
| 10.00 | | | | | | |
| 10.05 | | | | | | |
| 20.00 | | | | | | |

อธิบายจาก CSV ว่าเหตุใด B1 command latency กับ state latency จึงต่างกัน: __________________

ตรวจ warmup/initialstates ใน config: ทุก condition เริ่ม CPG เหมือนกันหรือไม่? หลักฐาน__________________

## 3. เปรียบเทียบผลและข้อจำกัด (15 นาที)

เติมจาก metrics และ segment_metrics พร้อมหน่วย ห้ามคัดลอกผล source paper มาใส่เป็นผล run นี้

| condition | TV φ(rad) | maxΔφ/step(rad) | TV stride(m) | cmd latency(s) | cmd recovery(s) | on frequency(Hz) | on distance(m) |
|---|---|---|---|---|---|---|---|
| B0 | | | | | | | |
| B1 | | | | | | | |
| B2 | | | | | | | |
| B3 | | | | | | | |

1. ผลข้อใดสนับสนุน hypothesis และผลข้อใดไม่สนับสนุน? __________________
2. การลด TV ยืนยันว่าหุ่นยนต์ไม่ล้มหรือใช้พลังงานน้อยลงหรือไม่? ขาดข้อมูลอะไร? __________________
3. Bounds เหมือนกันทำให้ commandamplitude เท่ากันหรือไม่? ใช้ peak/trace ประกอบ __________________
4. ทำไมไม่ใช้ frequency เฉลี่ย 30s แทน pre/on/off? __________________

## 4. เปลี่ยนหนึ่งปัจจัยและตรวจ fault (20 นาที)

เลือก phi-only หรือ stride-only ตั้ง prediction ก่อนรัน ตรวจ parameter ที่คงที่จาก intervalCSV แล้วเปรียบเทียบ B1/B2 กับ bothmapping

สิ่งที่เปลี่ยน________ สิ่งที่คงที่________ metric หลัก________ prediction________

ผลและข้อจำกัด causalclaim: __________________

รัน faultprofile เปิด input15.00 แล้วบันทึก:

| field | B2 value |
|---|---|
| fault at command15.00 | |
| H_used / R_used | |
| φ / stride ที่ใช้ | |
| H state15.05 | |
| H state15.10 | |

อธิบายว่า fallback ทำก่อนหรือหลัง command และเหตุใด policy นี้ยังไม่รับรอง hardware safety: __________________

## 5. Contact mini-lab (20 นาที)

เปิด contactreport เลือก cases ด้านล่าง เปรียบเทียบ SI, SIF, absoluteerror และ validity

| case | SI ของแต่ละขาโดยทั่วไป | SIF | absoluteerror | สิ่งที่อนุมานไม่ได้ |
|---|---|---|---|---|
| matched | | | | |
| gain-offset | | | | |
| mixed-delay | | | | |
| all-inverted | | | | |
| constant | | | | |

1. ทำไม gain-offset ให้ correlation สูงแม้ error ไม่เป็น 0? __________________
2. เมื่อทุกขา inverted ทำไม SIF จึงยังเป็น 0? release ที่ SIF0 มีค่าเท่าไร? __________________
3. constant ควรเป็น SI0 หรือ N/A? __________________
4. fault หนึ่ง sample มีผลต่อ rollingwindows กี่ rows ไม่นับ startup49rows? ตรวจ CSV__________________
5. pairedPearson ของ demo มีสถานะ source/proposed ใด? ต่อ Cg/MI แล้วหรือยัง? __________________

## 6. ส่งงานและ exit ticket (10 นาที)

ส่ง prediction ก่อนรัน, config/manifest/rawCSV ของ comparison+one-factorrun+fault, contactmetrics และ CSV หนึ่ง case ที่อภิปราย, ตารางพร้อมหน่วยและกราฟ 2 รูป พร้อมรายงาน 2–3 หน้า บอกคำสั่งและ Pythonversion เพื่อรันซ้ำ

Exit: เขียนหนึ่ง claim ที่ข้อมูลรองรับ และหนึ่ง claim ที่ยังรองรับไม่ได้ พร้อมชื่อ metric/ข้อมูลที่ต้องเพิ่ม

**Rubric20 คะแนน:** architecture/provenance4; timing/fault4; reproducibility/data3; quantitativecomparison/one-factor5; interpretation/contact/N/A4 คะแนนมาจากเหตุผลกับหลักฐาน ไม่ได้ให้เต็มเพราะ runner รันผ่านหรือเพราะผล “ดีขึ้น” ตามคาด

**Workshop 25 นาทีในคาบ Week05:** ทำข้อ 1 แบบย่อ 5 นาที, ข้อ 2 10 นาที, ข้อ 3 10 นาที ส่วน one-factor/fault/contact เป็น extended lab หรือการบ้าน ใช้เวลารวม 90 นาทีตามใบงาน ไม่รวมเวลาติดตั้ง Python
