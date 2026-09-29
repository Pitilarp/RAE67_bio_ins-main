# RAE67 bio ins

ชุดแล็บสำหรับรายวิชา Bio Inspired Robotics จัดแต่ละแล็บไว้ในโฟลเดอร์ `lab_xx` เพื่อเพิ่มแล็บถัดไปได้โดยไม่ปะปนกัน

| แล็บ | เนื้อหา | เอกสารเริ่มต้น |
|---|---|---|
| [Lab 02](lab_02/README.md) | Robust Reactive Lamp: sensor uncertainty และ sensorimotor control | [คู่มือนักศึกษา](lab_02/Lab02_Student_Manual_TH.docx) |
| [Lab 03](lab_03/README.md) | SO(2) CPG และการเดินแบบ alternating tripod ของหุ่นยนต์หกขา | [คู่มือนักศึกษา](lab_03/Lab03_Student_Manual_TH.docx) |

## เริ่ม Lab 02

```powershell
cd lab_02
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

เปิด [คำอธิบายแล็บ](lab_02/README.md) สำหรับขั้นตอนทดลองและไฟล์ที่ต้องส่ง ค่า controller ใน repo เป็น proposed course model สำหรับ simulator ไม่ใช่ค่าที่รับรองสำหรับหุ่นยนต์จริง

## เริ่ม Lab 03

```powershell
cd lab_03
python cpg_walk_sim.py --condition baseline --duration 2 --output-dir results\smoke_test
```

เปิด [คำอธิบาย Lab 03](lab_03/README.md) แล้วดาวน์โหลด [คู่มือนักศึกษา](lab_03/Lab03_Student_Manual_TH.docx) ก่อนเริ่มทำ TODO ใน `student_cpg.py`
