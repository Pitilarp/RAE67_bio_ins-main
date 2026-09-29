# รายงาน Lab 03: SO(2) CPG และการเดินของหุ่นยนต์หกขา

## 1. วัตถุประสงค์
การทดลองนี้ศึกษาผลของ recurrent gain `alpha` และ phase increment `phi` ต่อจังหวะของ SO(2) CPG การสลับขาแบบ alternating tripod และตัวชี้วัดการเดินใน kinematic simulation

## 2. วิธีการทดลอง
ใช้ค่า `dt = 0.05 s`, ระยะเวลาทดลอง 30 s, warmup 10 s, stride half 0.055 m และ lift height 0.030 m โดยเปรียบเทียบ 3 เงื่อนไข:

- `baseline`: alpha = 1.10, phi = 0.20 rad
- `fast`: alpha = 1.10, phi = 0.40 rad
- `high_gain`: alpha = 1.30, phi = 0.20 rad

การทดลองใช้ kinematic model ซึ่งวัด timing, foot placement และการเคลื่อนที่ของลำตัว แต่ไม่ได้จำลองแรงสัมผัสหรือ dynamics ของหุ่นยนต์จริง

## 3. ความสอดคล้องกับสไลด์ Week 03
การ implement ใน Lab 3 สอดคล้องกับแนวคิดหลักของสไลด์ CPG ดังนี้:

- ใช้ recurrent gain `alpha` และ phase increment `phi` ในการหมุนสถานะของ oscillator แบบ SO(2)
- คำนวณ `o1(t+1)` และ `o2(t+1)` จากสถานะเดิมพร้อมกัน ไม่ใช้ค่าที่อัปเดตแล้วของ `o1` ไปคำนวณ `o2` ในรอบเดียวกัน
- แปลง output ของ oscillator เป็น alternating tripod โดย Tripod A คือ `LF, RM, LH` และ Tripod B คือ `RF, LM, RH`
- ใช้ `phi` และ stride เป็นพารามิเตอร์ของ gait และจำกัดค่าด้วย bounds ก่อนส่งต่อไปยัง Week 4
- แยก slow modulation ออกจาก CPG และ actuator โดยใช้ bounded mapping แทนการสั่งมอเตอร์โดยตรง

## 4. Prediction
คาดว่าเมื่อเพิ่ม `phi` จาก 0.20 เป็น 0.40 rad ความถี่ของ CPG และความเร็วการเดินจะเพิ่มขึ้น เพราะ phase เปลี่ยนมากขึ้นในแต่ละ timestep เมื่อเพิ่ม `alpha` จาก 1.10 เป็น 1.30 คาดว่าแอมพลิจูดและ foot clearance จะเพิ่มขึ้น ส่วนขาใน Tripod A และ Tripod B ควรมี phase ตรงข้ามกัน 180 องศา

## 5. ผลการตรวจสมการ SO(2)
กำหนด `o1 = 0.10`, `o2 = -0.20`, `alpha = 1.10` และ `phi = 0.20 rad`

- `a1(t+1) = 0.064100071`
- `a2(t+1) = -0.237468274`
- `o1(t+1) = tanh(a1) = 0.064012423`
- `o2(t+1) = tanh(a2) = -0.233103007`

การคำนวณใช้ค่า `o1(t)` และ `o2(t)` เดิมพร้อมกัน จึงเป็น simultaneous update ตามสมการ SO(2)

## 6. ผล gait comparison

| Condition | Speed (m/s) | Frequency (Hz) | Duty factor | Min support | Clearance (mm) |
|---|---:|---:|---:|---:|---:|
| baseline | 0.077756 | 0.625000 | 0.494176 | 3 | 17.095 |
| fast | 0.155511 | 1.267123 | 0.500832 | 3 | 17.113 |
| high_gain | 0.094457 | 0.544218 | 0.494176 | 3 | 24.637 |

### การอภิปรายผล
การเพิ่ม `phi` เป็น 0.40 rad ในเงื่อนไข `fast` ทำให้ความถี่เพิ่มจาก 0.625 เป็น 1.267 Hz และความเร็วเพิ่มจาก 0.077756 เป็น 0.155511 m/s หรือประมาณสองเท่า ขณะที่ clearance แทบไม่เปลี่ยน เพราะค่า `alpha` และ lift height คงเดิม

การเพิ่ม `alpha` ในเงื่อนไข `high_gain` ทำให้ clearance เพิ่มจาก 17.095 เป็น 24.637 mm และความเร็วเพิ่มเป็น 0.094457 m/s แต่ความถี่ลดลงเหลือ 0.544218 Hz ในการวัดชุดนี้ ดังนั้น alpha ไม่ได้เพิ่มความถี่ในทิศทางเดียวกับ phi โดยตรง แต่มีผลต่อขนาด output และความสูงของการยกเท้า

ค่า minimum support legs เท่ากับ 3 ในทุก condition แสดงว่า decoder รักษารูปแบบ alternating tripod ได้ตามที่ออกแบบไว้ ไม่พบช่วงที่มีขารองรับน้อยกว่า 3 ขาในแบบจำลองนี้

## 7. ผล Week 4 handoff

| ช่วงเวลา | m(t) | phi command | stride command (m) | Speed (m/s) | Frequency (Hz) |
|---|---:|---:|---:|---:|---:|
| 0–10 s | 0.0 | 0.20 | 0.055 | 0.077632 | 0.625000 |
| 10–20 s | 1.0 | 0.40 | 0.065 | 0.183294 | 1.263158 |
| 20–30 s | 0.0 | 0.20 | 0.055 | 0.077387 | 0.625000 |

เมื่อ `m(t)` เพิ่มเป็น 1 ค่า phi และ stride เพิ่มขึ้นตาม bounded mapping ทำให้ความเร็วและความถี่เพิ่มขึ้น เมื่อ `m(t)` กลับเป็น 0 ทั้งสอง command กลับสู่ baseline และ metric ก็กลับมาใกล้ค่าเดิม แสดงว่า interface มีพฤติกรรมย้อนกลับได้ตาม mapping

Bounds มีความสำคัญเพื่อไม่ให้ command ออกนอกช่วงที่ออกแบบและเพื่อจำกัดพฤติกรรมของ gait ให้อยู่ในช่วงที่ตรวจสอบได้ ใน Week 4 ค่า `m(t)` จะถูกแทนด้วย hormone concentration ที่ผ่าน production, decay และ receptor dynamics หาก hormone เปลี่ยนช้ากว่า CPG ค่า phi และ stride จะค่อย ๆ เปลี่ยน ทำให้เกิด transient ก่อนเข้าสู่ gait ใหม่

## 8. ข้อจำกัด
แบบจำลองนี้เป็น kinematic teaching model จึงยังไม่สามารถยืนยัน dynamic stability, contact force, friction, motor torque, energy consumption หรือความสามารถในการติดตามคำสั่งของ actuator ได้ ผลลัพธ์จึงควรใช้ยืนยัน logic ของ timing และ foot placement เท่านั้น ไม่ควรอ้างเป็นผลการเดินของหุ่นยนต์จริง

## 9. สรุป
การทดลองยืนยันว่า `phi` เป็นตัวแปรสำคัญต่อ phase progression, ความถี่ และความเร็วของ gait ขณะที่ `alpha` มีผลต่อ amplitude และ foot clearance มากกว่า ทุก condition รักษา minimum support ที่ 3 ขาได้ จึงสอดคล้องกับการออกแบบ alternating tripod CPG การใช้ bounded modulation ทำให้ Week 4 สามารถเชื่อม slow biological signal เข้ากับพารามิเตอร์ของ gait ได้โดยไม่ส่งคำสั่งมอเตอร์โดยตรง

## 10. ไฟล์ผลลัพธ์
- Worksheet: [../worksheet.md](../worksheet.md)
- Grader: [my_grade.json](my_grade.json)
- Summary: [gait_comparison/conditions_summary.csv](gait_comparison/conditions_summary.csv)
- Baseline graph: [gait_comparison/baseline.svg](gait_comparison/baseline.svg)
- Fast graph: [gait_comparison/fast.svg](gait_comparison/fast.svg)
- High gain graph: [gait_comparison/high_gain.svg](gait_comparison/high_gain.svg)
- Week 4 CSV: [week4_bridge/week4_bridge.csv](week4_bridge/week4_bridge.csv)
- Week 4 contract: [week4_bridge/handoff_contract.json](week4_bridge/handoff_contract.json)
