# Lab 04 — Artificial Hormone Mechanism

เป้าหมาย: อธิบายว่า stimulus เปลี่ยนอัตราการสร้าง H อย่างไร เขียน dynamics ที่อัปเดตถูกลำดับ และใช้ข้อมูลเปรียบเทียบการตอบสนองตรง C0 กับ hormone C1–C4 ก่อนส่ง receptor output ไปยัง mapping ของ Week 03

ทุกอัตรา เวลา bounds และ mapping ใน Lab นี้เป็น **proposed course model** ไม่ใช่ค่าของฮาร์ดแวร์หรือผลทดลองจากบทความ ไม่มีการจำลอง gait ใน Lab04

## เตรียมเครื่องและเปิดงาน

ใช้ Python 3.10 ขึ้นไป ไม่ต้องติดตั้ง package เพิ่ม เริ่มจาก clone repository แล้วเปิด terminal ในโฟลเดอร์ `lab_04`:

```sh
git clone https://github.com/potiwat/RAE67_bio_ins.git
cd RAE67_bio_ins/lab_04
python3 --version
```

หาก clone ไว้แล้ว ให้ใช้ `git pull --ff-only` จาก repository root แล้วเข้า `lab_04` บน Windows ถ้าไม่พบ `python3` ให้ใช้ `py -3` แทนทุกคำสั่ง Python

ดาวน์โหลด [ใบงาน Word ภาษาไทย](Lab04_Student_Worksheet_TH.docx) เพื่อกรอกหรือพิมพ์ ใช้ร่วมกับ [คำถามใบงาน](worksheet.md) และคู่มือนี้ ชุดสาธารณะมีเฉพาะไฟล์นักศึกษา ไม่รวม reference controller เฉลย หรือผลทดลองของผู้สอน

1. เปิดใบงาน Word หรือ `worksheet.md` และเขียน prediction ก่อนรัน
2. เติม TODO ใน `student_hormone.py` ตามสมการด้านล่าง
3. ตรวจสอง time step แรกหลัง stimulus เปิด
4. รัน comparison และเปิด `results/comparison/report.html` ใน browser

```sh
python3 check_submission.py --student-file student_hormone.py
python3 lab04.py --controller-source student --condition all --profile step --output-dir results/comparison
python3 lab04.py --controller-source student --condition C1 --profile zero --output-dir results/zero
python3 lab04.py --controller-source student --condition C1 --profile one --output-dir results/one
python3 lab04.py --controller-source student --condition C1 --profile spike --output-dir results/spike
python3 lab04.py --controller-source student --condition C1 --profile fault --output-dir results/fault
```

คำสั่งแรกต้องรายงานผ่านทุก case เมื่อทำ TODO ครบ หากยังไม่ครบจะมี `NotImplementedError` โดยตั้งใจ การผ่าน checker เป็นเพียงหลักฐานด้าน code ไม่ใช่คะแนนเต็มของรายงาน

เมื่อรันซ้ำให้เลือก output directory ใหม่ เพื่อรักษาข้อมูลเดิม runner จะหยุดถ้า directory ไม่ว่าง ใช้ `--overwrite` เฉพาะเมื่อตั้งใจแทนที่ผลชุดนั้น

## โครงสร้างของเหตุและผล

Sensor stimulus S กระตุ้น production P ส่วน clearance C และ binding B ใช้สถานะเก่าร่วมกัน ผลสุทธิ P−C−B ทำให้ H เปลี่ยน จากนั้น receptor อ่าน H ใหม่ และ bounded mapping สร้าง phi/stride

สมการจากเอกสารการสอนที่อ้าง Homchanthanakul et al. (2019):

```text
Hc(t) = beta Hc(t−1) + Hg(t) − Hr(t)
Hg(t) = alpha f(S(t))
Hr(t) = sum(gamma_i Receptor_i(t))
```

Lab เลือกแบบจำลอง Euler แยกอัตราอย่างชัดเจน ไม่แทน beta ด้วย k_clear โดยตรง:

```text
R_old = clamp((H_old − H_min)/(H_max − H_min), 0, 1)
P = k_prod S                 [normalized H / s]
C = k_clear H_old            [normalized H / s]
B = k_bind R_old             [normalized H / s]
H_raw = H_old + dt (P − C − B)
H_new = clamp(H_raw, 0, 1)
R_new = receptor(H_new)
phi = clamp(0.20 + 0.20 R_new, 0.10, 0.45) [rad]
stride_half = clamp(0.055 + 0.010 R_new, 0.040, 0.070) [m]
```

`receptor` ต้อง reject H/range ที่ nonfinite และ H_max≤H_min ด้วย ValueError ใน `step` นั้น H เริ่มที่ 0 และมี bounds จึง finite เสมอ ตรวจ stimulus ก่อนคำนวณ: NaN, infinity หรือ S นอก [0,1] ให้ reset H/R เป็น 0 ตั้ง p/c/b/raw=0 และ fault=1 นี่คือ software fallback ของ Lab ไม่ใช่การรับรอง hardware safety

## Protocol และเวลาใน CSV

dt=0.05 s, duration=30 s, H0=0 ทุก condition ใช้ stimulus เดียวกัน: S=0 ช่วง [0,10), S=1 ช่วง [10,20), S=0 ช่วง [20,30) การรันเป็น deterministic ไม่ต้องใช้ random seed

| Condition | k_prod | k_clear | k_bind | สิ่งที่เปลี่ยนจาก C1 |
|---|---:|---:|---:|---|
| C0 | — | — | — | direct R=S ไม่มี hormone state |
| C1 | 0.8 | 0.6 | 0.2 | baseline |
| C2 | 1.2 | 0.6 | 0.2 | production เพิ่ม |
| C3 | 0.8 | 0.25 | 0.2 | clearance ลด |
| C4 | 0.8 | 0.6 | 0 | ตัด binding |

CSV มี **601 state rows** แต่มี **600 updates** แถวแรกเป็น initial state เวลา 0 แถวต่อมา time_s เป็นเวลา *หลัง* update ส่วน input_time_s เป็นเวลาต้นช่วงที่ใช้ stimulus และ p/c/b ในแถวนั้น เช่น input_time_s=10.00 ให้ state ที่ time_s=10.05

สอง update แรกหลังเปิด stimulus ของ C1 ให้ H=0.0400 และ 0.0784 (แถวเวลา 10.05 และ 10.10) ไม่ใช่สองแถวแรกของไฟล์ ซึ่งยังเป็นช่วง S=0 เวลาปิด stimulus คือ 20.00 state ที่ 20.00 ยังเป็นผลจาก on interval สุดท้าย ส่วน off update แรกจบที่ 20.05

H/raw/p/c/b ของ C0 เป็นช่องว่างใน CSV และ null ใน JSON เพราะไม่มี hormone state ไม่ใช่ค่า 0 ที่ใช้เปรียบเทียบ peak_H ได้

## นิยาม metric ที่ใช้จริง

| Metric | นิยามและหน่วย |
|---|---|
| peak_h, peak_r | ค่าสูงสุดตลอด 30 s; C0 peak_h=N/A |
| auc_h_left | ΣH(t_k)dt สำหรับ k=0..599 ช่วง [0,30), normalized H·s; ไม่รวม endpoint เพิ่มอีก dt |
| latency_s | เวลาที่ R≥0.1 ครั้งแรกหลังเปิด ลบ 10 s; sampling resolution 0.05 s |
| rise_10_90_s | เวลาข้าม 90% ลบเวลาข้าม 10% ของ peak_R ใน state-window [10,20]; เป็นสัดส่วนของ peak ไม่ใช่ค่าคงที่ 0.9 |
| recovery_s | หลัง 20 s เวลาข้าม R≤10% ของ peak_R ก่อนปิด; N/A ถ้า trial จบก่อน crossing |
| upper/lower_clamp_fraction | จำนวน updates ที่ raw>1 หรือ raw<0 หาร 600; H=0 ตามปกติไม่ใช่ clamp event |
| phi_total_variation_rad | Σ abs(phi[k+1]−phi[k]) หน่วย rad |
| stride_total_variation_m | นิยามเดียวกัน หน่วย m |
| fault_count | จำนวน input faults; fault profile ใส่ NaN 1 sample ที่ input_time_s=15 |

Timing metrics ใช้เฉพาะ step profile เท่านั้น profile อื่นเป็น N/A พร้อมเหตุผล อย่าแทน N/A ด้วยศูนย์ การตอบสนองตรง C0 ใน continuous time มี latency=0 แต่ log post-update ใน Lab จะวัดได้ 0.05 s ให้รายงานความละเอียดนี้

C2/C3/C4 อาจมี peak_H=1 เท่ากันเพราะ clamp จึงต้องดู AUC, recovery และ clamp fraction ร่วมกัน ห้ามสรุปว่า production เพิ่มแล้ว peak ที่ bounded ต้องเพิ่มเสมอ

## Extreme inputs

zero: ไม่มีเหตุการณ์ H ต้องคง baseline; one: S=1 ตลอด 30 s; spike: S=1 เพียง **หนึ่ง sample = 0.05 s** ที่ 10.00; fault: baseline step แต่แทน S ด้วย NaN หนึ่ง sample ที่ 15.00 แล้วกลับ stimulus ปกติ

ตรวจ fault row เวลา 15.05: fault=1, H=R=0, phi=.20, stride=.055 แถวถัดไปควรเริ่มสะสมอีกครั้ง input fault กับ saturation เป็นคนละเหตุการณ์

## Week 03 handoff

`handoff_contract.json` บรรจุ mapping และค่าคงที่ตรงกับ Week03: alpha=1.10, dt=.05, lift=.03 ตัว runner ตรวจ contract และหยุดถ้ามีการเปลี่ยนค่า สามารถใช้ contract ที่สร้างจาก Lab03 โดยส่ง `--contract path/to/handoff_contract.json`

Lab04 ส่งออก phi_rad และ stride_half_m ที่พร้อมใช้เชื่อมต่อ แต่ยังไม่รัน CPG หรือวัด body motion การทดสอบ integrated gait อยู่ Week05

## งานส่งและ rubric (20 คะแนน)

ส่ง student_hormone.py, raw CSV ของ comparison และ extreme cases, config.json, metric table, กราฟ และรายงาน 1–2 หน้า ให้ผู้ตรวจรันซ้ำได้จากคำสั่งที่ระบุ

คะแนน: architecture 3, model/provenance 4, implementation 4, experimental integrity 3, quantitative analysis 4, interpretation/safety 2 ดูคำถามใน worksheet ประกอบ

อ้างอิง: เอกสาร Week04 ของรายวิชา และ [Homchanthanakul et al. (2019), DOI](https://doi.org/10.1109/IROS40897.2019.8968580) สมการ Euler และตัวเลขใน Lab เป็น proposed course model
