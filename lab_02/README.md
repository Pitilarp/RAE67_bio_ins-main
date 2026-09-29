# Lab 02 — Robust Reactive Lamp

เอกสารสำหรับแจกนักศึกษา: [คู่มือ Lab 02 ฉบับ Word](Lab02_Student_Manual_TH.docx)

แล็บนี้ใช้ simulator เปรียบเทียบ controller สี่แบบภายใต้ input trajectory เดียวกัน แล้ววัดผลด้วยข้อมูลจาก repeated trials ก่อนนำแนวคิดไปเชื่อมกับหุ่นยนต์จริง

> ค่า threshold, gain, noise, delay และ command limit ในโฟลเดอร์นี้เป็น **proposed course model** สำหรับการเรียนการสอน ไม่ใช่ค่าความปลอดภัยหรือค่าที่รับรองสำหรับฮาร์ดแวร์จริง

## 1. Research question

รูปแบบ controller และระดับ sensor uncertainty ส่งผลต่อความเร็ว ความถูกต้อง และความเสถียรของการตอบสนองอย่างไร

## 2. ไฟล์สำคัญ

- `lab02.py` — simulator, controller C0–C3, protocol และ metric reference
- `student_controller.py` — โครงเริ่มต้นที่ให้นักศึกษาเติม TODO 1–4; simulator เรียกใช้ได้ด้วย `--controller-source student`
- `grade_submission.py` — ตรวจพฤติกรรมโค้ดนักศึกษาแยกตามฟังก์ชันและทดลองครบ C0–C3
- `plot_trial.py` — สร้างกราฟระยะ, state และ command จาก CSV หนึ่ง trial
- `tests/` — ตรวจ reference, การเชื่อม student controller และกรณี TODO ยังไม่เสร็จ
- `requirements.txt` — dependency สำหรับสร้างกราฟ

## 3. เตรียมสภาพแวดล้อม

ใช้ Python 3.10 ขึ้นไป จากโฟลเดอร์นี้:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

การจำลองและสร้าง CSV ใช้ Python standard library ส่วน `matplotlib` ใช้เฉพาะตอนสร้างกราฟ

## 4. งานก่อนทดลอง

ให้นักศึกษาเขียน prediction ลงในใบงานก่อนรันโปรแกรม:

1. เมื่อ noise เพิ่มขึ้น C1 จะมี switching count เปลี่ยนอย่างไร
2. C2 จะลด false trigger โดยแลกกับ latency หรือ recovery time อย่างไร
3. เมื่อเพิ่ม sensor delay เส้น command จะเลื่อนจาก physical event เท่าใด

ห้ามแก้ prediction หลังเห็นผลโดยไม่บันทึกเหตุผลและเวลาแก้

## 5. ทำความเข้าใจ input scenario

ทุก trial ยาว 20 วินาทีและใช้ trajectory เดียวกัน:

| เวลา | ระยะจริงจำลอง |
|---|---|
| 0–4 s | 0.60 m |
| 4–8 s | เคลื่อนเข้าใกล้จนถึง 0.25 m |
| 8–12 s | ค้างใกล้พร้อม disturbance ขนาดเล็ก |
| 12–16 s | เคลื่อนออกจนถึง 0.60 m |
| 16–20 s | 0.60 m |

โปรแกรมเพิ่ม Gaussian noise และ delay เฉพาะเส้นทาง sensor ส่วน `true_distance_m` ยังคงเป็น ground truth สำหรับวิเคราะห์ผล

## 6. Controller ที่ต้องเปรียบเทียบ

| Condition | หลักการ | ค่า input ที่ใช้ |
|---|---|---|
| C0 | Open-loop sequence ตามเวลา | ไม่ใช้ sensor |
| C1 | Single threshold ที่ `T = 0.35 m` | raw distance |
| C2 | Low-pass filter และ hysteresis | filtered distance |
| C3 | Proportional response และ clamp | filtered distance |

ให้เปิด `student_controller.py` และเติม TODO 1–4 ก่อนอ่านส่วน implementation ใน `lab02.py` โดยเมธอดแต่ละตัวต้องคืนค่าที่คำนวณได้ ตัวเชื่อมใน `lab02.py` จะจัดการ state, filter history และการส่ง command ให้ simulator

มีสองโหมดที่ใช้ input, seed และ metric ชุดเดียวกัน:

- `--controller-source reference` (ค่าเริ่มต้น) ใช้ตัวอย่างใน `lab02.py`
- `--controller-source student` ใช้ `StudentController` ในไฟล์ที่ระบุด้วย `--student-file` (ค่าเริ่มต้นคือ `student_controller.py` ในโฟลเดอร์นี้)

ไฟล์เริ่มต้นยังมี TODO จึงรันโหมด student ไม่ผ่านจนกว่านักศึกษาจะเติมฟังก์ชันครบ

## 7. ขั้นทดลอง A — เปรียบเทียบ C0–C3

ค่าเริ่มต้นใช้ `sigma = 0.01 m`, delay `0 ms` และ 5 trials ต่อ condition รวม 20 trials:

```powershell
python lab02.py --protocol controller-comparison --out results\comparison
```

เมื่อเติม TODO แล้ว ให้รันโค้ดนักศึกษาในโฟลเดอร์ผลแยกจาก reference:

```powershell
python lab02.py --controller-source student --protocol controller-comparison `
  --student-file student_controller.py --out results\student_comparison
```

`run_config.json` จะบันทึก `controller_source`, ที่อยู่ไฟล์นักศึกษา และ SHA-256 ของไฟล์เพื่อระบุว่า CSV ชุดนั้นสร้างจาก submission ใด

ไฟล์ที่ได้:

```text
results/comparison/
├── run_config.json
├── summary_trials.csv
├── summary_aggregate.csv
└── trials/
    ├── C0_*.csv
    ├── C1_*.csv
    ├── C2_*.csv
    └── C3_*.csv
```

ตรวจ `run_config.json` ก่อนวิเคราะห์เพื่อยืนยัน parameter, seed และจำนวน trial

## 8. ขั้นทดลอง B — Noise และ delay

หลังจากขั้น A ให้เลือก controller หนึ่งแบบ โดยค่าเริ่มต้นแนะนำ C2 เพราะต้องการศึกษาผลของ filter และ hysteresis

### ชุดย่อในคาบ

ห้า combinations และ 3 trials ต่อ combination รวม 15 trials:

```powershell
python lab02.py --protocol robustness-short --condition C2 --out results\c2_short
```

### ชุดเต็มหลังเรียน

noise `0.00, 0.01, 0.03 m` คูณ delay `0, 100, 300 ms` และ 5 trials รวม 45 trials:

```powershell
python lab02.py --protocol robustness-full --condition C2 --out results\c2_full
```

หากต้องการทดลองซ้ำในโฟลเดอร์เดิม ต้องระบุ `--overwrite` อย่างชัดเจน โปรแกรมจะไม่เขียนทับผลเดิมโดยอัตโนมัติ

## 9. สร้างกราฟหนึ่ง trial

เลือกไฟล์ CSV จาก `trials`:

```powershell
python plot_trial.py results\comparison\trials\C2_n0.01_d000_r01.csv `
  --out results\comparison\C2_trial1.png
```

กราฟต้องอ่านร่วมกันสองส่วน:

- ระยะจริง, raw distance, filtered distance และ threshold
- state, command และตำแหน่ง event

ชี้บนกราฟว่า stimulus ข้าม criterion เวลาใด และ controller เริ่มตอบสนองเวลาใด

## 10. Metric ที่โปรแกรมคำนวณ

- `latency_enter_s` และ `latency_exit_s` — เวลาจาก physical crossing ถึง state ถูกต้องครั้งแรก
- `recovery_time_s` — เวลาจาก physical threshold crossing จนเริ่มช่วงที่ state ถูกต้องต่อเนื่องอย่างน้อย 0.5 s โดยรายงานค่าที่มากกว่าระหว่าง enter และ exit
- `false_trigger_rate_per_min` — การเข้าสู่ NEAR ขณะที่ ground truth ยังเป็น FAR ต่อ valid observation minute
- `switching_count` — จำนวนการเปลี่ยน FAR กับ NEAR ทั้งหมด
- `extra_switches` — switching count ที่เกิน expected transitions สองครั้ง
- `mean_abs_command_change` — ค่าเฉลี่ย `|u[k] - u[k-1]|`
- `invalid_sample_count` — จำนวน sample ที่ missing, non-finite หรือ out of range

ต้องอ่านหลาย metric ร่วมกัน ตัวอย่างเช่น command ที่ไม่เคลื่อนเลยอาจมี smoothness ดี แต่ไม่ตอบสนองต่อ stimulus

## 11. คำถามวิเคราะห์ผล

1. C1 กับ C2 ต่างกันใน `extra_switches` และ latency เท่าใด
2. เมื่อ noise เพิ่มจาก 0.01 เป็น 0.03 m ค่าใดเปลี่ยนชัดที่สุด
3. delay 300 ms เพิ่ม response latency ใกล้ 300 ms หรือไม่ เพราะเหตุใด
4. C3 ชน command limit ช่วงใด และ smoothness สัมพันธ์กับ tracking error อย่างไร
5. มี invalid samples หรือไม่ และกลุ่มจัดการ trial เหล่านั้นอย่างไร

ข้อสรุปต้องระบุ condition, metric และตัวเลขเปรียบเทียบ หลีกเลี่ยงข้อความว่า controller หนึ่ง “ดีกว่า” โดยไม่ระบุเกณฑ์

## 12. เชื่อมต่อกับหุ่นยนต์จริง

เปลี่ยนเฉพาะสามจุดใน experiment loop:

1. `true_distance_m()` เปลี่ยนเป็น reference measurement หรือเว้นว่างหากไม่มี ground truth
2. sensor simulator เปลี่ยนเป็น `read_distance_m()` ที่คืนค่าและ sensor timestamp
3. normalized command เปลี่ยนเป็นคำสั่ง actuator หลังตรวจหน่วย, mechanical limit และทิศทางเครื่องหมาย

ก่อนจ่ายกำลังให้ actuator:

- ตรวจ datasheet, min/max range และ field of view ของ sensor
- ตรวจ joint limit, velocity limit และ command unit
- ทดสอบ `safe_command()` และ emergency stop
- เริ่มด้วย command limit ต่ำกว่าค่าทดลองจริง
- ยึดหุ่นยนต์และกันพื้นที่เคลื่อนที่

ห้ามใช้ parameter จาก simulator กับหุ่นยนต์โดยตรงโดยไม่ทำขั้นตอนเหล่านี้

## 13. ผลส่งมอบ

แต่ละกลุ่มส่ง:

1. Prediction ก่อนทดลอง
2. Block diagram ของ sensorimotor loop พร้อมทิศทางข้อมูลและ feedback
3. `student_controller.py` ที่เติม TODO และ source code อื่นที่แก้
4. ผลตรวจ `grade_submission.py`, `run_config.json` ของโหมด student, raw CSV ทุก trial และ `summary_aggregate.csv`
5. กราฟตัวแทนอย่างน้อย C1 และ C2 พร้อมเวลา physical crossing และ first correct response
6. รายงาน 1–2 หน้า พร้อมข้อจำกัดของการทดลอง

## 14. ตรวจงานนักศึกษา

จากโฟลเดอร์ `lab_02` ผู้สอนใช้คำสั่งต่อไปนี้กับไฟล์ที่แต่ละกลุ่มส่ง โดยแยกชื่อรายงานและโฟลเดอร์ผลต่อกลุ่ม:

```powershell
python grade_submission.py --student-file path\to\student_controller.py `
  --out results\group01_grade.json
python lab02.py --controller-source student `
  --student-file path\to\student_controller.py `
  --protocol controller-comparison --out results\group01_trials
```

รายงานตรวจการโหลดไฟล์, filter, threshold, hysteresis, proportional/clamp, invalid sample และการรันเต็ม C0–C3 หากยังมี TODO จะรายงาน FAIL และคืน exit code 1 ผลตรวจนี้เป็นเพียงหลักฐานด้าน controller ไม่ใช่คะแนน 20 คะแนนอัตโนมัติ ผู้สอนยังต้องตรวจ block diagram, ความซื่อสัตย์ของข้อมูล, การวิเคราะห์ และการตีความ

การนำไฟล์ Python ที่นักศึกษาส่งมารันคือการรันโค้ดของผู้ส่ง ควรตรวจใน VM หรือสภาพแวดล้อมแยกที่ไม่มี token, credential หรือข้อมูลส่วนตัว และอย่ารันด้วยสิทธิ์สูง
