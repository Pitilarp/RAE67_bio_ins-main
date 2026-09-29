# สรุปสไลด์ Week 03: SO(2) CPG

## แนวคิดหลัก
CPG หรือ Central Pattern Generator ใช้ oscillator เพื่อสร้างจังหวะซ้ำ ๆ ให้กับการเคลื่อนไหว โดยไม่ต้องกำหนดคำสั่งของขาแต่ละขาแยกกันทุก timestep

## สมการ SO(2)
สถานะ oscillator มีสององค์ประกอบคือ `o1` และ `o2` การอัปเดตหนึ่งรอบใช้ recurrent gain `alpha` และ phase increment `phi`:

```text
a1(t+1) = alpha [cos(phi)o1(t) + sin(phi)o2(t)]
a2(t+1) = alpha [-sin(phi)o1(t) + cos(phi)o2(t)]
o1(t+1) = tanh(a1(t+1))
o2(t+1) = tanh(a2(t+1))
```

จุดสำคัญคือเป็น simultaneous update ต้องเก็บค่า `o1(t)` และ `o2(t)` เดิมไว้ใช้คำนวณทั้งสองสมการ

## ความหมายของพารามิเตอร์
- `alpha`: recurrent gain มีผลต่อขนาด output และ amplitude
- `phi`: phase increment มีผลต่อความเร็วการหมุนของ oscillator และความถี่ที่วัดได้
- `tanh`: จำกัด output ให้อยู่ในช่วงประมาณ `[-1, 1]`

## Alternating tripod
หุ่นยนต์หกขาแบ่งเป็นสองกลุ่ม:

- Tripod A: `LF, RM, LH`
- Tripod B: `RF, LM, RH`

สองกลุ่มใช้ phase sign ตรงข้ามกัน จึงมีช่วงหนึ่งที่กลุ่มหนึ่งอยู่ใน stance ขณะที่อีกกลุ่มอยู่ใน swing ทำให้มีขารองรับ 3 ขาในแบบจำลองนี้

## การแปลงเป็นคำสั่งขา
สำหรับขาแต่ละขาใช้ sign ของ tripod เพื่อคำนวณ:

```text
x_rel = stride_half * sign * o1
lift = lift_height * max(0, sign * o2)
contact = sign * o2 <= 0
```

## การทดลอง
- เพิ่ม `phi`: คาดว่าความถี่และความเร็วจะเพิ่มขึ้น
- เพิ่ม `alpha`: คาดว่า amplitude และ foot clearance จะเพิ่มขึ้น
- ตรวจ minimum support legs เพื่อดูว่ารูปแบบ tripod ยังรักษาขารองรับ 3 ขาได้หรือไม่

## การส่งต่อ Week 4
slow input `m(t)` ถูก map ไปเป็น `phi` และ stride ด้วย bounds:

```text
phi = clamp(0.20 + 0.20m, 0.10, 0.45)
stride = clamp(0.055 + 0.010m, 0.040, 0.070)
```

ใน Week 4 สามารถแทน `m(t)` ด้วย hormone concentration ที่ผ่าน production, decay และ receptor dynamics โดยยังคง bounds เพื่อควบคุมขอบเขตของ gait

## ข้อจำกัด
ผลจาก kinematic simulation ยืนยันได้เฉพาะ timing, phase, foot placement และ metric pipeline ยังไม่ยืนยัน dynamic stability, friction, contact force, motor torque, energy หรือ actuator tracking
