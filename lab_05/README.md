# Lab 05 — Hormone → SO(2) CPG → Kinematic Walking

เชื่อมแบบจำลอง Week03–04 ให้รันได้จริง แล้วทดสอบว่า hormone path ทำให้ command, CPG และการเคลื่อนที่ใน kinematic model เปลี่ยนอย่างไร เทียบ fixed/direct path และ binding ablation

**ทุกตัวเลข robot/controller/timing ใน Lab นี้เป็น proposed course model** อ้างอิง architecture และโจทย์จาก [Ngamkajornwiwat et al. (2020), IEEE Access Article 9088155](https://ieeexplore.ieee.org/abstract/document/9088155) แต่ไม่ได้ reproduce MNLC, hormone-to-MI recurrence, terrain dynamics หรือผล robot ใน paper อ่าน [SOURCES.md](SOURCES.md) ก่อนตีความผล

## เริ่มบนเครื่องใหม่

ดาวน์โหลดจาก [GitHub รายวิชา `lab_05`](https://github.com/potiwat/RAE67_bio_ins/tree/main/lab_05) ใช้ Python 3.10 ขึ้นไป ไม่ต้องติดตั้ง package เพิ่ม

```sh
git clone https://github.com/potiwat/RAE67_bio_ins.git
cd RAE67_bio_ins/lab_05
python3 --version
python3 lab05.py --condition all --profile step --mapping both --output-dir results/comparison
python3 contact_demo.py --output-dir results/contact
```

Windows ถ้าไม่พบ `python3` ให้ใช้ `py -3` แทนทุกคำสั่ง เปิด `results/comparison/report.html` และ `results/contact/report.html` ด้วย browser ปกติ เปิดได้ offline ไม่ต้องมี server

หากมี checkout เดิม ให้เก็บงานของตนเองแล้วรัน `git pull --ff-only` ที่ root ของ `RAE67_bio_ins` ก่อนเข้า `lab_05`

อ่าน [ใบงาน Word](Lab05_Student_Worksheet_TH.docx) หรือ [ใบงาน PDF](Lab05_Student_Worksheet_TH.pdf) แล้วเขียน prediction ก่อนเปิดผล comparison

runner ปฏิเสธ directory ที่ไม่ว่างเพื่อเก็บ raw results เดิม เมื่อต้องการรันซ้ำให้ตั้งชื่อใหม่ เช่น `results/comparison_02` ไม่มีคำสั่ง overwrite อัตโนมัติ

นี่เป็น **working scaffold สำหรับ prediction/analysis/experimental design** ไม่ใช่ข้อสอบเติม TODO นักศึกษาไม่ต้องเขียน MNLC ใหม่ ทุกขั้นตอนคำนวณเปิดอ่านได้ใน `course_model.py`; runner ไม่โหลดหรือ execute code จากไฟล์นักศึกษา

## Protocol ที่ต้องประกาศก่อนรัน

dt=.05 s, α=1.10, lift=.03 m, duration=30 s, initial oscillator (.10,0). Warmup CPG 10 s ด้วย φ=.20 เหมือนกันทุก condition จากนั้น reset H/R, body origin, foot anchors และ log origin โดยคง oscillator ที่ผ่าน warmup ไว้

S=0 ช่วง [0,10), S=1 ช่วง [10,20), S=0 ช่วง [20,30); controller เดียวกันแต่ละ condition ใช้ stimulus schedule เดียวกัน ไม่มี random noise การรันซ้ำจึงตรวจ reproducibility ได้แต่ไม่ใช่ independent trials

| Condition | การสร้าง R_used | k_prod | k_clear | k_bind |
|---|---|---:|---:|---:|
| B0 fixed | 0 | — | — | — |
| B1 direct | S_k ณต้น interval | — | — | — |
| B2 hormone | H(t_k), R=H | .8 | .6 | .2 |
| B3 binding ablation | H(t_k), R=H | .8 | .6 | 0 |

k_prod มีหน่วย normalized H/s, k_clear เป็น s⁻¹ และ k_bind เป็น normalized H/s ต่อ R ที่ไม่มีหน่วย B3 ทดสอบ binding term ภายใต้ model นี้ ไม่ใช่ตัด prior MI_H หรือ hormone memory ของ paper

```text
P = k_prod S_k
C = k_clear H(t_k)
B = k_bind R(t_k), R(t_k)=H(t_k)
H_raw = H(t_k) + dt(P−C−B)
H(t_(k+1)) = clamp(H_raw,0,1)
phi_cmd = clamp(.20+.20 R_used,.10,.45) [rad]
stride_half_cmd = clamp(.055+.010 R_used,.040,.070) [m]
```

Bounds เดียวกันไม่ได้ทำให้ response amplitude เท่ากัน ค่า command ใน protocol นี้อยู่ภายใน bounds อยู่แล้ว ดังนั้น command clamp count อาจเป็นศูนย์ และ H=0 ตามปกติไม่ถือเป็น lower-clamp event

## เวลา: input, command และ state คนละ field

`B*_states.csv` มี **601 states** เวลา 0 ถึง 30 s ส่วน `B*_intervals.csv` มี **600 intervals** เวลา command 0 ถึง 29.95 s

1. อ่าน S_k ที่ input_time=t_k; ถ้า invalid ใช้ fault fallback ก่อน command
2. B2/B3 ใช้ R จาก state t_k; B1 เป็น direct algebraic path จึงใช้ S_k ทันที
3. ใช้ φ/stride command ณ command_time=t_k ในช่วง [t_k,t_(k+1))
4. อัปเดต CPG สองนิวรอนพร้อมกันจาก old outputs → decode → advance kinematic body
5. อัปเดต hormone จาก S_k และ old H → บันทึก state ที่ t_(k+1)

ตัวอย่างตรวจ timing ของ B2: state_time=10.00 มี H/R=0, command_time=10.00 ใช้ φ=.20, stride=.055; input10.00 ทำให้ state10.05 มี H=.04 จากนั้น command10.05 ใช้ φ=.208 และ stride=.0554 นี่คือ convention ของ numerical scheduling ไม่ใช่ hardware latency

B1 command เริ่มทันทีที่ 10.00 แต่ post-update R ใน states เริ่ม 10.05 จึงต้องแยก command latency จาก state latency

Contact ของ main runner ใช้ sign(o₂) จาก decoder ไม่ใช่ measurement อิสระ การนับ 3 support legs ยังไม่ยืนยัน static/dynamic stability โดยไม่มี CoM/support polygon/body dynamics ภาพ contact diagram ใน report แสดง decoder state เท่านั้น

## หนึ่งปัจจัยและ extreme-input runs

ตั้ง hypothesis ว่าเปลี่ยน parameter ใดก่อนดูผล แล้วรัน:

```sh
python3 lab05.py --mapping phi-only --output-dir results/phi_only
python3 lab05.py --mapping stride-only --output-dir results/stride_only
python3 lab05.py --condition B2 --profile zero --output-dir results/zero
python3 lab05.py --condition B2 --profile one --output-dir results/one
python3 lab05.py --condition B2 --profile spike --output-dir results/spike
python3 lab05.py --condition all --profile fault --output-dir results/fault
```

phi-only คง stride_half=.055; stride-only คง φ=.20 ไม่เปลี่ยน gains/bounds ใน contract ตัว runner หยุดเมื่อ contract ต่างจาก Week03–04 ถ้าจะเปลี่ยน model ต้องออกแบบ protocol ใหม่และระบุ provenance แยก

zero=0 ตลอด, one=1 ตลอด, spike=1 เพียงหนึ่ง sample=.05 s ที่ input10.00, fault=step profile แต่ S=NaN หนึ่ง sample ที่ input15.00

**Fault policy:** ทุก condition ส่ง R_used=0, φ=.20, stride=.055 ใน interval[15.00,15.05) ก่อน CPG update; B2/B3 reset H/R เป็น 0; post state15.05 เป็น 0 แล้วสะสมใหม่จาก interval15.05 จึง H15.10=.04 ไม่ freeze ตัวกรองและไม่รอ command ถัดไป Policy นี้เป็น software fallback ใน model ไม่รับรอง hardware safety

## Metrics และ N/A

| Field | นิยามที่ใช้ |
|---|---|
| distance_m / mean_speed_m_s | body_x(end)−body_x(start), หาร elapsed time; kinematic model เท่านั้น |
| phi_total_variation_rad | Σ abs(φ_next−φ_previous) รวม initial baseline → command0; หน่วย rad |
| stride_total_variation_m | แบบเดียวกัน หน่วย m; ไม่เติม command หลังจบ trial |
| phi_max_step_rad / stride_max_step_m | max abs(command_next−command_previous) รวม initial baseline; เปลี่ยนสูงสุดต่อ step ไม่ใช่ TV หรือ body acceleration |
| command_latency_s | command_time แรกหลัง 10 ที่ R_used≥.1 ลบ 10; B1=0 ตาม direct convention |
| state_latency_s | state_time แรกหลัง 10 ที่ R≥.1 ลบ 10; log B1 มี sampling offset=.05 s |
| command_rise_10_90_s | ช่วง crossing10%→90% ของ peak R_used ใน command-window[10,20) |
| command_recovery_s | command_time แรกตั้งแต่ 20 ที่ R_used≤10% ของ peak ก่อนปิด ลบ 20 |
| auc_h_left_normalized_s | ΣH(t_k)dt, k=0..599; ไม่รวม endpoint30 เพิ่มอีก dt |
| h_upper/lower_clamp_fraction | updates raw>1/raw<0 หารจำนวน updates; B0/B1 ไม่มี H→N/A |
| frequency_hz ใน segments | 1/mean period ระหว่าง rising crossings ของ o₁ ใน [start,end); ≥2 crossings |
| complete_period_count | จำนวน periods ระหว่าง crossings ที่อยู่ใน segment ทั้งคู่ |
| fault_count / command clamp counts | actual events ไม่ใช่จำนวนที่ state อยู่พอดีขอบเขต |

แบ่ง pre[0,10), on[10,20), off[20,30) สำหรับ frequency และ command averages; distance ใช้ positions ที่ boundary start/end เพื่อให้ segment distances รวมกันได้ Timing ใช้ resolution=.05 s; frequency ใช้ linear interpolation ระหว่างสอง **simulated** states เพื่อประมาณ crossing ไม่ใช่การเติมข้อมูล sensor ที่ขาด ห้ามเรียกช่วง on/off ว่า steady state โดยไม่ตรวจ transient

Timing ใช้เฉพาะ B1/B2/B3 กับ step profile; B0 หรือ profile อื่นเป็น N/A ถ้าไม่พบ crossing ก่อนจบ trial ก็ N/A พร้อมเหตุผล JSON ใช้ null, CSV ช่องว่าง, report แสดง N/A ห้ามแทนด้วย 0

TV วัดผลรวมการเปลี่ยนตลอด trial จึงอาจใกล้กันมากระหว่าง direct step กับ hormone ที่ค่อย ๆ ขึ้นลงด้วย amplitude ใกล้กัน ใช้ max-step และ time trace ร่วมกันเพื่ออภิปรายความค่อยเป็นค่อยไป อย่าสรุปว่า TV ต้องลดมากเพราะมี hormone

Paper Stability/Harmony/Displacement เป็น N/A เพราะไม่มี measurement/dynamics/normalization ที่ตรงนิยาม ไม่เรียก TV ว่า Harmony, supportcount ว่า Stability หรือ distance ว่า Displacement

## Predicted–actual contact mini-lab

`contact_demo.py` สร้าง expected กับ synthetic actual 6 ขา เป็น continuous sine proxy1Hz ไม่ใช่ binary force/contact sensor และไม่ส่ง feedback เข้า main runner

| Case | perturbation | คำถามที่ทดสอบ |
|---|---|---|
| matched | actual=expected | validwindow ควรเป็นอย่างไร |
| gain-offset | actual=.2+.5expected | correlation ตรวจ amplitude/offset ได้หรือไม่ |
| mixed-delay | 3 ขาตรง, 3 ขา delay.25s | temporalcorrelation ต่างจาก populationSD อย่างไร |
| all-inverted | actual=1−expected ทุกขา | ทุกขาผิดเหมือนกันแต่ SIF เกิดอะไร |
| constant | expected=actual=.5 | variance0 ไม่ใช่ SI0 |
| fault | LF actual=NaN sample15.00 | fault กระทบหลาย rollingwindows แค่ไหน |

ใช้ paired-product Pearson ที่ติดป้าย **proposed course definition** ไม่ได้แก้ Eq.(3) ของ paper โดยปริยาย Window50samples รวม current: sample0..49 ครอบ 0..2.45s; firstvalid sample2.45 ไม่ใช่ 2.50 โดยอัตโนมัติ ถ้า window ไม่ครบ, variance0, nonfinite หรือ out-of-range ให้ SI unavailable; หากขาใด unavailable ให้ SIF/release unavailable ไม่แทน SI ด้วย 0

SIF=populationSD ของ 6SI; release=1/(1+exp(−SIF)) ตาม Eq.(1) CI1 แต่ไม่รัน C_g/HR/MI_H ต่อ อ่าน time traces และ validityflags ใน CSV ร่วมกับค่าเฉลี่ย

## ไฟล์ผลและการส่งงาน

แต่ละ run เก็บ raw states/intervals, config, initial states, full/segment metrics, report, contract, source snapshots และ manifest SHA-256 นักศึกษาสามารถเปิด source snapshots กับ config เพื่อรันซ้ำบนเครื่องใหม่ได้

ส่งตาม [worksheet.md](worksheet.md): prediction, selected raw/config/manifest files, metric table, กราฟและรายงาน 2–3 หน้า ทุก claim ต้องระบุ model และช่วงเวลา พร้อมหนึ่งข้อค้นพบที่เป็น negative/null result ได้

เวลาขยาย lab แนะนำ 90 นาที นอกเหนือจาก numerical/paper-reading activities ของคาบ Week05; ใน workshop25 นาทีให้ใช้เฉพาะ comparison+timing ไม่มีข้อบังคับรันทุก extension ในคาบ
