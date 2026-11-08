# Source และขอบเขตของ Lab 05

บทความหลัก: Ngamkajornwiwat, P., Homchanthanakul, J., Teerakittikul, P., & Manoonpong, P. (2020). *Bio-Inspired Adaptive Locomotion Control System for Online Adaptation of a Walking Robot on Complex Terrains*. IEEE Access, 8, 91587–91602. DOI: [10.1109/ACCESS.2020.2992794](https://doi.org/10.1109/ACCESS.2020.2992794).

- [IEEE Xplore Article 9088155](https://ieeexplore.ieee.org/abstract/document/9088155)
- [Full text จาก SDU](https://findresearcher.sdu.dk/ws/files/170343970/Bio_inspired.pdf) — ใช้ตรวจเนื้อหา, CC BY 4.0
- SHA-256 ของ PDF ที่ใช้ทบทวนเนื้อหา: `F051F039E82E5836344CDDE1EB62570A070F9C2F1D4691D29D27C763C2D7D5BB`

| สิ่งที่ใช้ | ที่มา | สถานะในโปรแกรม |
|---|---|---|
| ALCS = MNLC + AHM, efference copy, expected–actual contact | paper Fig. 2–6 | อ้างอิงแนวคิด; ไม่ได้สร้าง MNLC ครบชุด |
| การคำนวณ SI ใน Eq. (3) ตามที่พิมพ์ | paper Section II-C | **ไม่ implement ตามพิมพ์**; ผลคูณของ centered normalized sums แยกกันมีข้อสงสัย ยังไม่ยืนยัน author code/erratum |
| paired-product Pearson SI = Σ(x−x̄)(y−ȳ)/sqrt(Σ(x−x̄)² Σ(y−ȳ)²) | **proposed course definition** | `contact_demo.py`; ค่า [-1,1], ไม่เรียกว่า reproduction ของ Eq. (3) |
| 50 paired samples ต่อ window | paper ระบุ 50 steps; indexing ใน Eq. (3) ยังต้องตรวจ | lab เลือกแน่ชัด last 50 samples รวม current; dt=.05 s เป็นค่ารายวิชา |
| SIF เป็น population SD ของ SI ระหว่าง 6 ขา | paper Eq. (2) | demo ใช้ centered equivalent form เพื่อลด cancellation; ต้อง valid ครบ 6 ขา |
| release = CI/(1+exp(−SIF)), CI=1 | paper Eq. (1) | คำนวณเฉพาะเมื่อ SIF valid; ไม่ต่อ C_g/HR/MI_H |
| synthetic sine/contact-proxy, delay, gain, offset, faults | **proposed course inputs** | ไม่มี physical sensor/terrain feedback; ไม่เชื่อมกลับเข้า main runner |
| SO(2) α/φ recurrence, alternating tripod decoder | Week03, Lab03, legacy lec5.pptx slide18 | working scaffold; ไม่ใช่ MNLC postprocessing/PSN/VRN/18 motor neurons |
| production–clearance–binding Euler, H/R clamp [0,1] | Week04 **proposed course model** | B2 ใช้ C1, B3 ใช้ C4; H ไม่ใช่ C_g, R ไม่ใช่ HR |
| affine φ/stride mapping, bounds, schedule, fault policy | Lab03/04 **proposed course model** | คง handoff contract; ไม่ใช่ MI_H=HR×prior MI_H |
| stance-anchor body model | Lab03 kinematic teaching model | มี x position แต่ไม่มี mass, force, friction, slip, CoM หรือ terrain |
| command TV, latency/recovery, segment frequency/distance | **proposed course metrics** | ค่า simulator; frequency มี timing interpolation ระหว่าง simulated states |
| Stability, Harmony, Displacement ตาม paper | paper Eqs. (8)–(14) | N/A; ไม่มี measurement/dynamics/normalization ที่รองรับ |

แบบจำลองหลักใช้ stimulus schedule เดียวกันทุก controller จึงทดสอบการตอบสนองของ controller และผลใน kinematic model ได้ แต่ไม่ใช่การปรับตัวจากผลการกระทำที่มีต่อ terrain แบบ closed loop

SIF=0 เกิดได้ทั้งทุก SI=1, ทุก SI=0 และทุก SI=−1 สำหรับ Pearson ที่เลือกใน demo; release ที่ SIF=0 ยังเท่ากับ .5 การเพิ่ม absolute error จึงไม่จำเป็นต้องเพิ่ม SIF/release

สมการ C_g/HR/MI_H ตามพิมพ์มีประเด็นเรื่อง scale, neutral point และ convergence ซึ่งสอนผ่าน numerical audit แยกต่างหาก ไม่ใช้ runner นี้เป็นหลักฐานว่าแก้ประเด็นดังกล่าวแล้ว และไม่อ้างผลเทียบ rough-terrain success rate ของ paper จากผล kinematic lab

ทุกไฟล์ผลทดลองบันทึก source snapshot, config, raw CSV และ SHA-256 manifest นักศึกษาต้องแยก source equations, proposed model และผลที่วัดได้จริงในรายงาน
