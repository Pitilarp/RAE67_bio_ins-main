# ใบงาน Lab04 (รายงาน 1–2 หน้า)

ชื่อ/รหัส __________________ กลุ่ม ______ วันที่ ______ code version/hash ______

## A. ก่อนรัน (10 นาที)

Block diagram ของ proposed course model:
```text
S ──> P=k_prod·S ──┐
H_old ──> C=k_clear·H_old ─┼─> H_raw=H_old+dt(P−C−B) ─> clamp ─> H_new ─> R_new
H_old ──> receptor ─> R_old ─> B=k_bind·R_old ─┘                         │
                                                                           └─> bounded mapping ─> phi, stride
invalid S ────────────────────────────────────────────────────────────────> fault=1, reset H/R=0
```
ความเชื่อมโยง: S ควบคุม production P; clearance C อ่าน H_old ส่วน binding B อ่าน R_old ที่คำนวณจาก H_old. P−C−B เปลี่ยน H หนึ่งครั้งต่อ time step จึงเก็บประวัติผ่าน state H; receptor อ่าน H_new หลัง update แล้ว mapping แปลง R_new เป็น phi/stride. Invalid stimulus ใช้ fault/reset path แทนการคำนวณอัตราปกติ.

| Comparison | prediction ก่อนรัน | เหตุผลจาก term ในสมการ | ผลจริงหลังรัน |
|---|---|---|---|
| C2 vs C1 | H เพิ่มเร็วกว่าและ AUC สูงกว่า; peak อาจใกล้หรือเท่ากันเมื่อชนขอบ 1; คาดว่า recovery อาจนานขึ้นจาก H ที่สูงกว่า | ตอน S=1, `P=k_prod S` เพิ่มจาก 0.8S เป็น 1.2S ทำให้ `H_raw=H_old+dt(P−C−B)` เพิ่มเร็วขึ้น; เมื่อ S=0 ค่า P เป็นศูนย์และ C,B เท่ากันตามสถานะ แต่ H เริ่มต้นอาจสูงกว่า | peak_H 1.0000 เทียบ 0.9997; AUC_H 10.6724 เทียบ 9.9996; latency 0.10 เทียบ 0.15 s; rise 1.05 เทียบ 2.70 s; recovery เท่ากัน 2.85 s; upper clamp 0.2900 เทียบ 0 |
| C3 vs C1 | H สะสมมากกว่าและลดลงช้ากว่า; คาดว่า AUC และ recovery สูงขึ้น; peak อาจถูกขอบบนจำกัด | `k_clear` ลดจาก 0.6 เป็น 0.25 จึงลด `C=k_clear H_old`; `P` และ `B` เท่าเดิมเมื่อเทียบที่สถานะเดียวกัน ทำให้ผลสุทธิ `P−C−B` สูงขึ้นทั้งตอนกระตุ้นและตอนปิด stimulus | peak_H 1.0000 เทียบ 0.9997; AUC_H 11.3891 เทียบ 9.9996; recovery 5.10 เทียบ 2.85 s (ช้ากว่า 2.25 s); rise 1.45 เทียบ 2.70 s; upper clamp 0.2733 เทียบ 0 |
| C4 vs C1 | ตัด binding แล้วคาดว่า H เพิ่มเร็วขึ้นและ AUC สูงขึ้น; ตอนปิด stimulus คาดว่าฟื้นช้าลงเพราะเหลือ clearance อย่างเดียว | `k_bind=0` ทำให้ `B=k_bind R_old=0` แทนที่จะหักออกจาก `H_raw`; ผลต่างนี้มีทั้งตอน S เปิดและปิด ส่วน `P` และ `C` ยังเหมือนเดิมเมื่อเทียบที่สถานะเดียวกัน | peak_H 1.0000 เทียบ 0.9997; AUC_H 10.7547 เทียบ 9.9996; rise 1.70 เทียบ 2.70 s; recovery 3.80 เทียบ 2.85 s (ช้ากว่า 0.95 s); upper clamp 0.2583 เทียบ 0 |
| C0 vs C1 | C0 ตอบสนองตรงตาม S ไม่มีสถานะ H และไม่มีการสะสม/ฟื้นตัวแบบฮอร์โมน; C1 มี latency และ recovery จาก dynamics ของ H | C0 กำหนด `R=S` โดยตรงและไม่มี `P,C,B,H`; C1 คำนวณ `H_raw` จากสถานะเก่าแล้วใช้ `R_new=receptor(H_new)` จึงมี memory/lag | C0 ไม่มี H (peak_H/AUC_H = N/A); peak_R ทั้งคู่ 1.0000; latency ที่ sampling 0.05 s คือ 0.05 s ใน C0 และ 0.15 s ใน C1; recovery 0.05 เทียบ 2.85 s |

หมายเหตุ: คำทำนายในคอลัมน์นี้เรียบเรียงจากสมการของแบบจำลองหลังจากมีผลรันแล้ว จึงเป็นการสร้าง prediction เชิงทฤษฎีย้อนหลัง ไม่ใช่หลักฐานว่าได้บันทึกไว้ก่อนรัน

เขียนว่า prediction ใดอาจเปลี่ยนเพราะ H มี upper bound=1: คำทำนายว่า C2, C3 หรือ C4 ต้องมี peak_H สูงกว่า C1 อาจไม่เกิด เพราะเมื่อ H แตะ 1 จะถูก clamp; ผลจริง peak ของ C1–C4 ใกล้/เท่ากันที่ประมาณ 1 แต่ AUC, rise, recovery และ clamp fraction ยังต่างกัน __________________

## B. เติม code และคำนวณมือ (20 นาที)

**Source equation (สมการอ้างอิงจากเอกสารการสอน):**
`Hc(t)=beta Hc(t−1)+Hg(t)−Hr(t)`, `Hg(t)=alpha f(S(t))`,
`Hr(t)=sum(gamma_i Receptor_i(t))`.

**Proposed course model ที่ implement ใน Lab04 (ไม่ใช่ค่าฮาร์ดแวร์):**
`R_old=clamp((H_old−H_min)/(H_max−H_min),0,1)`;
`P=k_prod S`, `C=k_clear H_old`, `B=k_bind R_old`;
`H_raw=H_old+dt(P−C−B)`, `H_new=clamp(H_raw,0,1)`,
`R_new=receptor(H_new)`.
จากนั้น `phi=clamp(0.20+0.20R_new,0.10,0.45)` rad และ
`stride_half=clamp(0.055+0.010R_new,0.040,0.070)` m.

ทดสอบ receptor: เมื่อ `H=.2`, `H_min=.1`, `H_max=.5`,
`R=clamp((.2−.1)/(.5−.1),0,1)=.25`.

สำหรับ C1 (`dt=.05`, `k_prod=.8`, `k_clear=.6`, `k_bind=.2`):
รอบแรก `H_old=0`, `S=1`, `R_old=0` จึง `P=.8`, `C=0`, `B=0`,
`H_raw=.04`, `H_new=.04`, `R_new=.04`, `phi=.208` rad,
`stride_half=.0554` m.
รอบสอง `H_old=.04`, `R_old=.04` จึง `P=.8`, `C=.024`, `B=.008`,
`H_raw=.04+.05(.8−.024−.008)=.0784`, `H_new=.0784`,
`R_new=.0784`, `phi=.21568` rad, `stride_half=.055784` m.

| input_time_s | time_s | P | C | B | H_raw | H | R | phi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|10.00|10.05|0.8000|0.0000|0.0000|0.0400|0.0400|0.0400|0.20800|
|10.05|10.10|0.8000|0.0240|0.0080|0.0784|0.0784|0.0784|0.21568|

แถว CSV ใช้เวลา `input_time_s` เป็นต้นช่วงที่นำ stimulus ไปคำนวณ และ `time_s` เป็นเวลาสถานะหลัง update: input 10.00–10.05 ให้ state เวลา 10.05; input 10.05–10.10 ให้ state เวลา 10.10.

รัน `check_submission.py`: ผ่านทั้ง 13 cases (normalization/clamp, invalid range, update จาก old state, no binding และ fault NaN/Inf/out-of-range) ไม่มี case ที่ไม่ผ่านให้แก้.

## C. Controlled comparison (20 นาที)

รัน C0–C4 ใช้ dt,duration,H0,stimulus,mapping เดียวกัน เปิด report.html และกรอกค่าจาก metrics.json ไม่อ่านค่าด้วยสายตาอย่างเดียว

| Condition | peak_H | AUC_H | latency s | rise s | recovery s | upper clamp fraction | phi TV rad |
|---|---:|---:|---:|---:|---:|---:|---:|
|C0|N/A|N/A|0.05|0.00|0.05|N/A|0.40000|
|C1|0.99972|9.99964|0.15|2.70|2.85|0.00000|0.39983|
|C2|1.00000|10.67241|0.10|1.05|2.85|0.29000|0.39994|
|C3|1.00000|11.38914|0.15|1.45|5.10|0.27333|0.39789|
|C4|1.00000|10.75472|0.15|1.70|3.80|0.25833|0.39955|

C3 ฟื้นช้ากว่า C1 `5.10−2.85=2.25 s`. C2 และ C3 peak_H เท่ากันที่ 1.0 เพราะ upper clamp; AUC (10.67241 เทียบ 11.38914), rise (1.05 เทียบ 1.45 s), recovery และ clamp fraction แยกระบบได้. C0 ไม่มี state H (`peak_H` และ `AUC_H` เป็น N/A/null) เพราะเป็น direct mapping `R=S`. ค่า TV ที่ต่ำกว่าเพียงอย่างเดียวพิสูจน์คุณภาพ gait ไม่ได้ เพราะยังไม่มี CPG/body-motion, gait stability หรือพลังงานในการจำลองนี้.

## D. Extreme tests และ handoff (10 นาที)

| Profile (C1) | ผลจาก metrics/CSV | ตรวจสอบ |
|---|---|---|
| zero | peak_H=0, AUC_H=0, fault_count=0 | H คง baseline |
| one | peak_H=1.00000, upper clamp fraction=0, fault_count=0 | stimulus คงที่; H เข้าใกล้ 1 โดยไม่เกิน bound |
| spike | peak_H=.04000 | S=1 ที่ input_time_s=10.00 เพียงหนึ่ง update (0.05 s) |
| fault | fault_count=1; แถว input_time_s=15.00, time_s=15.05 มี H=R=0, raw=P=C=B=0, phi=.20, stride=.055; แถวถัดไป time_s=15.10 กลับ H=.04 | fault flag และ reset ถูกต้อง; dynamics เริ่มสะสมใหม่ |

การแยกขอบเขต: software bounds เป็น clamp ของตัวแปรจำลองในซอฟต์แวร์เท่านั้น; ไม่ได้รับรอง actuator limits ทางกายภาพหรือ emergency stop ซึ่งเป็นระบบฮาร์ดแวร์/ความปลอดภัยแยกกันและต้องทดสอบอย่างเหมาะสม.

ตรวจ handoff contract ที่แนบมากับ Lab (`handoff_contract.json`): runner ยอมรับ contract นี้และ comparison สร้างผลสำเร็จ. ที่ `R=0` ได้ `phi=.20 rad`, `stride_half=.055 m`; ที่ `R=1` ได้ `phi=.40 rad`, `stride_half=.065 m` ซึ่งอยู่ใน mapping bounds. ไม่มีไฟล์ contract Week03 ต้นฉบับแยกต่างหากในชุดผลนี้ จึงยืนยันได้เฉพาะ contract ที่แนบมา ไม่ได้อ้างว่าได้ทดสอบไฟล์ Week03 อื่น. Lab04 ยังไม่ได้ทดสอบการเชื่อม CPG, gait/body motion, เสถียรภาพ, พลังงาน หรือความปลอดภัยฮาร์ดแวร์; ต้องทำ integrated gait test ใน Week05.

## E. สรุปส่งงาน (10 นาที)

**สรุป (1) กลไกและ provenance.** ใน proposed course model stimulus S กำหนด production `P=k_prod S`; clearance `C=k_clear H_old` และ binding `B=k_bind R_old` ใช้สถานะเก่า. ผลสุทธิเปลี่ยน H หนึ่งครั้งต่อ dt=.05 s แล้ว receptor อ่าน H ใหม่ก่อน mapping เป็น phi/stride. ตัวอย่าง C1 หลังเปิด stimulus ที่ input_time_s=10.00 และ 10.05 ได้ H=.0400 และ .0784 ตามลำดับ. สมการต้นทางจากเอกสารการสอนถูกแยกจาก Euler model ที่ Lab เสนอ; พารามิเตอร์และ bounds เป็นค่าของแบบจำลองรายวิชา ไม่ใช่ข้อมูลฮาร์ดแวร์.

**สรุป (2) prediction และผล.** การเพิ่ม production ใน C2 ทำให้ latency ลดจาก .15 s (C1) เป็น .10 s และ AUC เพิ่มจาก 9.99964 เป็น 10.67241; ลด clearance ใน C3 ทำให้ AUC เพิ่มเป็น 11.38914 และ recovery ยาวจาก 2.85 เป็น 5.10 s หรือช้ากว่า 2.25 s. การปิด binding ใน C4 ให้ AUC 10.75472 และ recovery 3.80 s. Peak_H ของ C1–C4 อยู่ประมาณ 1 เพราะ upper clamp จำกัด peak จึงใช้ AUC, rise, recovery และ clamp fraction ประกอบ; C0 ไม่มี H และมี latency/recovery ที่ความละเอียด log 0.05 s. คำทำนายในตาราง A เป็นการคาดการณ์จากสมการที่เรียบเรียงย้อนหลังหลังได้ผล ไม่ใช่การบันทึกก่อนรัน.

**สรุป (3) ข้อจำกัดและงานต่อ.** ผลเป็น deterministic subsystem simulation 30 s ไม่ได้พิสูจน์ gait, stability, energy efficiency, actuator safety หรือ emergency-stop behavior. งาน Week05 ควรต่อ output phi/stride เข้ากับ CPG และ plant/body model ภายใต้ protocol ที่ควบคุมเหมือนกัน เก็บ time-series/metrics การเคลื่อนที่และเสถียรภาพ พร้อมทดสอบ fault handling แยกจากการทดสอบฮาร์ดแวร์จริง.

คำสั่งที่ใช้ (รันจาก `lab_04`; ใช้ `py -3` บน Windows ที่ตั้งค่า Python Launcher แล้ว):
```powershell
py -3 check_submission.py --student-file student_hormone.py
py -3 lab04.py --controller-source student --condition all --profile step --output-dir results\comparison
py -3 lab04.py --controller-source student --condition C1 --profile zero --output-dir results\zero
py -3 lab04.py --controller-source student --condition C1 --profile one --output-dir results\one
py -3 lab04.py --controller-source student --condition C1 --profile spike --output-dir results\spike
py -3 lab04.py --controller-source student --condition C1 --profile fault --output-dir results\fault
```
ผลและ config อยู่ใต้ `results/`; comparison ใช้ `dt=.05 s`, duration `30 s`, H0=0 และ stimulus step 10–20 s. SHA-256 ใน `results/comparison/config.json`: student controller `cf09e2e39cd358fcbe2c8ebdcd2aca57706ca7d8d7b38e79777c1a540bf5cf7f`; runner `4acf68979cde5f086e41f82cc5137ab7bac49026184032a2e7ac4943c1abacb4`.

Checklist: ☑ code ☑ comparison CSV 5 files ☑ extreme CSV 4 files ☑ config ☑ plots ☑ metrics ☑ report ☑ คำสั่งรันซ้ำได้. ข้อมูลชื่อ/รหัส/กลุ่ม/วันที่ของผู้ส่งยังเว้นไว้ให้กรอกเอง.
