# Lab 03 SO(2) CPG และการเดินของหุ่นยนต์หกขา

เอกสารชุดนี้ใช้สมการ SO(2) CPG จาก `lec5.pptx` สไลด์ 18 สร้างจังหวะเดินแบบ alternating tripod ในแบบจำลองเชิงจลนศาสตร์ นักศึกษาต้องคำนวณวงจร เขียนตัวถอดรหัสขา เปรียบเทียบเงื่อนไขด้วยข้อมูล และส่งสัญญาณควบคุมที่มี bounds ไปเป็นจุดเริ่มของ Week 4

> ค่า `α`, `φ`, stride, lift และ bounds ในชุดนี้เป็น **proposed course model** สำหรับการสอน ไม่ใช่ค่าที่รับรองสำหรับหุ่นยนต์จริง

## ดาวน์โหลดชุดทดลอง

- GitHub: https://github.com/potiwat/RAE67_bio_ins/tree/main/lab_03
- หากใช้ Git: `git clone https://github.com/potiwat/RAE67_bio_ins.git`
- หลังดาวน์โหลด ให้เข้าโฟลเดอร์ `RAE67_bio_ins\lab_03`

## 1 Research question

การเปลี่ยน recurrent gain `α` และ phase increment `φ` ส่งผลต่อจังหวะ CPG การสลับ tripod และตัวชี้วัดการเดินใน kinematic simulation อย่างไร

คำถามส่งต่อ Week 4 คือ สถานะที่เปลี่ยนช้ากว่า CPG จะปรับ `φ` และ stride ภายใต้ bounds ได้อย่างไร โดยไม่ส่งคำสั่งมอเตอร์โดยตรง

## 2 Learning outcomes

เมื่อจบ Lab นักศึกษาสามารถ:

1. implement สมการ SO(2) แบบ simultaneous update
2. แปลง `o₁`, `o₂` เป็นคำสั่งขาหกขาแบบ alternating tripod
3. เปลี่ยนตัวแปรทีละตัวและวัด speed, frequency, duty factor, support และ clearance
4. แยกค่าที่ตั้ง ค่าที่วัด และข้อจำกัดของ kinematic model
5. สร้าง bounded modulation interface ที่ Week 4 สามารถป้อน hormone concentration เข้ามาแทน manual input ได้

## 3 ไฟล์สำคัญ

- `hexapod_cpg_sim.html` — visual simulator สำหรับสำรวจค่าพารามิเตอร์แบบสด
- `run_visual_sim.bat` — เปิด visual simulator บน Windows
- `cpg_walk_sim.py` — reference batch experiment และตัวสร้าง CSV JSON SVG
- `student_cpg.py` — ไฟล์นักศึกษาที่มี TODO 1–3
- `grade_submission.py` — ตรวจสมการ decoder และ bounded mapping เชิงพฤติกรรม
- `week4_bridge.py` — manual slow modulation protocol สำหรับส่งต่อ Week 4
- `worksheet.md` — ใบงาน prediction การบันทึกผล และคำถาม handoff
- `Lab03_Student_Manual_TH.docx` — คู่มือแจกนักศึกษา

## 4 เตรียมสภาพแวดล้อม

ต้องใช้ Python 3.10 ขึ้นไป การจำลองใช้ Python standard library จึงไม่ต้องติดตั้ง package เพิ่ม

```powershell
git clone https://github.com/potiwat/RAE67_bio_ins.git
cd RAE67_bio_ins\lab_03
python --version
python cpg_walk_sim.py --condition baseline --duration 2 --output-dir results\smoke_test
```

หาก Windows ไม่รู้จัก `python` ให้ลองใช้ `py` แทน เพื่อให้ภาษาไทยในผล JSON แสดงถูกต้องใน PowerShell ใช้ `$env:PYTHONUTF8=1`

## 5 สมการและลำดับอัปเดต

```text
a₁(t+1) = α[cos(φ)o₁(t) + sin(φ)o₂(t)]
a₂(t+1) = α[−sin(φ)o₁(t) + cos(φ)o₂(t)]
o₁(t+1) = tanh(a₁(t+1))
o₂(t+1) = tanh(a₂(t+1))
```

ต้องเก็บ `o₁(t)` และ `o₂(t)` ก่อนคำนวณค่ารอบใหม่ทั้งคู่ ห้ามนำ `o₁(t+1)` ไปใช้คำนวณ `o₂(t+1)` ในรอบเดียวกัน

## 6 งานก่อนทดลอง

กรอก prediction ใน `worksheet.md` ก่อนรันโปรแกรม:

1. เมื่อเพิ่ม `φ` ความถี่ที่วัดได้จะเปลี่ยนอย่างไร
2. เมื่อเพิ่ม `α` แอมพลิจูดและ clearance จะเปลี่ยนอย่างไร
3. ขาสอง tripod ควรต่างเฟสกันเท่าใด
4. metric ใดที่ kinematic simulator ยังวัดไม่ได้

ห้ามแก้ prediction หลังเห็นผลโดยไม่บันทึกเหตุผล

## 7 ขั้นทดลอง A Visual exploration

ดับเบิลคลิก `run_visual_sim.bat` หรือเปิด `hexapod_cpg_sim.html` ด้วยเว็บเบราว์เซอร์

1. กด `Baseline` แล้วสังเกตกราฟ `o₁`, `o₂`
2. ตรวจว่า Tripod A คือ `LF, RM, LH` และ Tripod B คือ `RF, LM, RH`
3. ตรวจว่ามีขารองรับ 3 ขาในแต่ละช่วง
4. กด `Fast` แล้วเปรียบเทียบ frequency และ speed
5. กด `High gain` แล้วสังเกต amplitude และ clearance
6. ทดลองปรับทีละ slider และบันทึกสิ่งที่เปลี่ยน

ปุ่ม `Download CSV` ดาวน์โหลดข้อมูลตั้งแต่การ reset ครั้งล่าสุด แต่ผลหลักที่ใช้ส่งควรมาจาก batch experiment เพื่อให้ทำซ้ำได้

## 8 ขั้นทดลอง B เติมโค้ดนักศึกษา

เปิด `student_cpg.py` แล้วเติม:

- TODO 1 `so2_step` — สมการ SO(2) และ simultaneous update
- TODO 2 `decode_tripod` — `x_rel`, `lift`, `contact` ของขาทั้งหก
- TODO 3 `bounded_modulation` — mapping จาก `m` ไปยัง `φ` และ stride พร้อม clamp

ตรวจไฟล์ของตนเอง:

```powershell
python grade_submission.py --student-file student_cpg.py `
  --out results\my_grade.json
```

ไฟล์เริ่มต้นจะ FAIL ตามที่ตั้งใจจนกว่า TODO ครบ รายงาน PASS ต้องได้ 5 จาก 5 checks

## 9 ขั้นทดลอง C Gait comparison

```powershell
python cpg_walk_sim.py --condition all --output-dir results\gait_comparison
```

| Condition | α | φ rad | ตัวแปรที่เปลี่ยน |
|---|---:|---:|---|
| baseline | 1.10 | 0.20 | จุดอ้างอิง |
| fast | 1.10 | 0.40 | `φ` เท่านั้น |
| high_gain | 1.30 | 0.20 | `α` เท่านั้น |

คง `dt=0.05 s`, duration 30 s, warmup 10 s, initial condition, stride และ lift height เท่ากัน

ผลลัพธ์ประกอบด้วย `conditions_summary.csv` และไฟล์ CSV SVG JSON ของแต่ละ condition

## 10 วิธีอ่าน metric

- `distance_m` — การเปลี่ยนตำแหน่งลำตัวในแบบจำลอง
- `mean_speed_m_s` — distance หารด้วยเวลาทดลอง
- `oscillation_frequency_hz` — ความถี่จาก rising zero crossings หลัง warmup
- `duty_factor_LF` — สัดส่วนเวลาที่ขา LF อยู่ใน stance
- `minimum_support_legs` — จำนวนขารองรับต่ำสุด
- `maximum_foot_clearance_m` — ความสูงยกเท้าสูงสุดจาก decoder

สรุปผลด้วย condition, metric, หน่วย และตัวเลขเปรียบเทียบ หลีกเลี่ยงคำว่า “ดีกว่า” หากยังไม่กำหนดเกณฑ์

## 11 ขั้นทดลอง D ส่งต่อ Week 4

```powershell
python week4_bridge.py --output-dir results\week4_bridge
```

| เวลา | manual `m(t)` | ความหมาย |
|---|---:|---|
| 0–10 s | 0 | baseline |
| 10–20 s | 1 | เพิ่ม `φ` และ stride ผ่าน bounded mapping |
| 20–30 s | 0 | กลับ baseline |

```text
φ_cmd      = clamp(0.20 + 0.20m, 0.10, 0.45)
stride_cmd = clamp(0.055 + 0.010m, 0.040, 0.070)
```

`m(t)` เป็น manual input สำหรับ Week 3 ยังไม่ใช่ hormone ใน Week 4 นักศึกษาจะเรียน `H_c`, production, decay และ receptor แล้วใช้ค่าที่ได้มาแทน `m(t)` โดยรักษา target mapping และ bounds เดิมไว้เพื่อเปรียบเทียบอย่างเป็นธรรม

ผลลัพธ์คือ `week4_bridge.csv` และ `handoff_contract.json` ซึ่งบันทึก baseline, gain, bounds, fixed parameters และ segment metrics

## 12 คำถามวิเคราะห์

1. `fast` ต่างจาก `baseline` ใน frequency และ speed เท่าใด
2. `high_gain` เปลี่ยน clearance และ frequency ไปในทิศทางเดียวกันหรือไม่
3. support legs ต่ำกว่า 3 หรือไม่ และกฎใดเป็นสาเหตุ
4. เมื่อ `m` กลับจาก 1 เป็น 0 output กลับ baseline ทันทีหรือมี transient
5. เพราะเหตุใด Week 4 จึงควรส่ง hormone ผ่าน receptor และ bounded mapping แทนการสั่งมอเตอร์โดยตรง
6. ถ้าต้องพิสูจน์ dynamic stability ต้องเพิ่ม model และ metric ใด

## 13 ขอบเขตของหลักฐาน

แบบจำลองนี้ตรวจตรรกะของ timing, phase, foot placement และ metric pipeline ผลยังไม่ยืนยัน dynamic stability, contact force, friction, motor torque, energy, actuator tracking หรือสมรรถนะของหุ่นยนต์จริง

## 14 ผลส่งมอบ

แต่ละกลุ่มส่ง:

1. `worksheet.md` ที่กรอก prediction และผลวัด
2. `student_cpg.py` ที่เติม TODO ครบ
3. `results/my_grade.json`
4. raw CSV และ summary ของ gait comparison
5. `week4_bridge.csv` และ `handoff_contract.json`
6. กราฟตัวแทนอย่างน้อยสองเงื่อนไข
7. รายงาน 1–2 หน้า แยกค่าที่ตั้ง ค่าที่วัด กลไก และข้อจำกัด

## 15 เกณฑ์ประเมิน

| เกณฑ์ | คะแนน |
|---|---:|
| สมการ SO(2) และ simultaneous update | 20 |
| alternating tripod decoder | 20 |
| controlled experiment และความครบถ้วนของข้อมูล | 20 |
| metric การเปรียบเทียบและการตีความ | 20 |
| bounded Week 4 handoff | 10 |
| ข้อจำกัดและความซื่อสัตย์ของข้อสรุป | 10 |

ผลของ `grade_submission.py` ครอบคลุมเฉพาะ implementation คะแนนส่วนอื่นประเมินจาก prediction, raw data, กราฟ และคำอธิบาย

## 16 ข้อผิดพลาดที่พบบ่อย

- ใช้เครื่องหมายของ `w₂₁` ผิด
- อัปเดต `o₁` ก่อนแล้วนำค่าใหม่ไปคำนวณ `o₂`
- เริ่มที่ `o₁=o₂=0` ทำให้วงจรอยู่ที่จุดสมดุลศูนย์
- เปลี่ยน `α` และ `φ` พร้อมกันแล้วสรุปสาเหตุไม่ได้
- เรียก `φ` ว่าความถี่โดยไม่วัด output
- สลับรายชื่อขาใน Tripod A และ B
- ไม่มี clamp ก่อนส่ง parameter command
- อ้างผล simulation เป็นผลหุ่นยนต์จริง
