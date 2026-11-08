# Lab 06 — Lamp Emotion and Interaction

โปรแกรม offline สำหรับออกแบบและตรวจ emotion state machine ของโคมไฟหุ่นยนต์ ใช้ Python 3.10 ขึ้นไปและ standard library ไม่มี package เพิ่ม **ตัวเลข sensor/controller/movement/RGB และ mapping ทุกค่าเป็น proposed course model** Joint เป็นแกนเชิงความหมาย `tilt`, `extend`, `nod` หน่วย rad ไม่มี linkage, torque, collision หรือการรับรอง hardware safety

## เริ่มจาก GitHub

```sh
git clone https://github.com/potiwat/RAE67_bio_ins.git
cd RAE67_bio_ins/lab_06
python3 --version
python3 lab06.py --policy student --condition all --repeats 3 --output-dir results/starter
python3 check_submission.py --contract group
```

อ่าน [ใบงาน Word](Week06_Student_Worksheet_TH.docx) และ [worksheet.md](worksheet.md) เพื่อเขียน prediction และ transition table ก่อนเติม TODO ใน `student_policy.py` Starter รันได้ แต่ checker ควร FAIL จนกว่างานครบ หากมี checkout เดิมให้เก็บงานของตนเองแล้ว `git pull --ff-only` ที่ root ก่อนเข้า `lab_06`

คำสั่ง GitHub ทั้งหมดเริ่มจาก `lab_06` ซึ่งมี `lab06.py`; ขั้นตอน `cd lab06` ในใบงาน Word ใช้เฉพาะโครงสร้าง ZIP ด้านล่าง บน Windows ใช้ `py -3` แทน `python3` ได้ หลังเติม policy ให้ตรวจด้วย contract ที่กลุ่มเลือก แล้วรันด้วยชื่อ output ใหม่ตามคู่มือนี้

## เริ่มจาก ZIP บนเครื่องใหม่

แตก ZIP `Week06_Student_Package.zip` แล้วเปิด terminal ภายใน folder `Week06_Student_Package` จากนั้นรัน:

```sh
python3 --version
cd lab06
python3 lab06.py --policy student --condition all --repeats 3 --output-dir results/starter
python3 check_submission.py
```

บน Windows หากไม่มี `python3` ให้ใช้ `py -3` แทน เปิด `results/starter/report.html` ด้วย browser ปกติได้ offline ตัว starter แสดง normal/interested/afraid และยังไม่ครบ happy/sleepy/timeout: checker จึง **ต้องรายงาน FAIL ก่อนทำ TODO** ไม่ใช่ installation error

อ่าน [worksheet.md](worksheet.md) แล้วเติม `transition(current_state: str, event: str) -> str | None` ใน [student_policy.py](student_policy.py) จาก prediction และ transition table 5 × 8 ของตนเอง ห้ามแก้ sensor/output safety เพื่อให้ผ่าน checker เมื่อแก้แล้วรัน:

```sh
python3 check_submission.py
python3 lab06.py --policy student --condition all --repeats 3 --output-dir results/completed
```

ใช้ชื่อ output ใหม่ทุกครั้ง runner ปฏิเสธ directory ที่ไม่ว่างเพื่อเก็บ raw results เดิม การรัน policy เป็นการ execute Python ของตนเอง; checker ใช้ process แยก จำกัด 5 s และล้าง inherited environment แต่ไม่ใช่ OS sandbox สำหรับตรวจ code จากบุคคลอื่นควรใช้ restricted account หรือ disposable offline VM

## Protocol และ baseline

| ค่า | proposed course model |
|---|---|
| dt / duration / scheduler delay | .02 s / 22 s / .04 s |
| debounce C1 | button/touch ต้องคงค่า .06 s; source onset ก่อน debounce |
| near C1 | enter ≤.20 m; exit ≥.28 m |
| approach C1 | enter ≤.80 m; exit ≥.95 m |
| C0 | ไม่มี debounce/hysteresis; near .20 m และ approach .80 m |
| stale / invalid | sample age >.12 s, future/nonfinite timestamp, button/touch ไม่ใช่0/1, distance นอก0..4 m หรือ nonfinite → fault |
| active timeout / normal inactivity | interested/happy 2 s → normal; normal ไม่มี interaction6 s → sleepy |
| output bound / slew | tilt ±.35, extend ±.25, nod ±.30 rad; ≤.8 rad/s ทุกแกน |
| repeated inputs | seeds41,42,43; C0/C1 ใช้ input CSV เดียวกันในแต่ละคู่ |

Default protocol: button1 s มี bounce; touch3 s; approach5 s มี noise±.035 m; clear6.4 s; near7 s พร้อม touch; clear9 s; invalid distance11 s; stale touch12 s; button18 s ระหว่างช่วงว่างเข้าสู่ sleepy ตาม timeout ของ model ผลจาก seed มีความต่างได้จริง แต่เป็น synthetic replications ไม่ใช่ physical trials อิสระ

C0 และ C1 ใช้ policy, pose/RGB, bounds, slew, stale/invalid fallback, scheduler และ seed เหมือนกัน จึงเปรียบเทียบผลของ debounce/hysteresis ภายใต้ noise ที่กำหนดได้ เลือก priority `fault > near > clear > touch > button > approach > timeout > idle`; บันทึก lower-priority candidates เป็น `discarded_priority` ไม่มีการ silently drop ถ้าระยะยัง near ให้ afraid จน clear/fault และเมื่อข้อมูล invalid ให้ neutral normal ก่อน activity ถัดไป

**Transition contract สำหรับ baseline TODO/checker:** fault จากทุก state → normal; near จากทุก state → afraid; clear จากทุก state → normal หลังตรวจสาม event นี้ ให้ afraid hold ทุก event อื่น; สำหรับ state อื่น touch → happy, button/approach → interested; timeout เฉพาะ interested/happy → normal; idle เฉพาะ normal → sleepy ส่วน combination ที่เหลือให้ return None ใช้ baseline เมื่อต้องการเทียบผลกับ protocol เดิม

เมื่อออกแบบ mapping ของกลุ่มเอง ใช้ `python3 check_submission.py --contract group`: คง fault/near/clear, afraid guard, timeout/idle recovery เดิม แต่เลือก interested หรือ happy สำหรับ positive button/touch/approach ได้ และทุก5stateต้อง reachable จากnormal รัน C0/C1 ด้วย policy ของกลุ่มเดียวกัน โดยประกาศ mappingก่อนรัน อย่านำค่าของ baseline reference มาใช้เป็นผล group policy

Priority ใช้กับ events ที่ recognized ใน tick เดียวกัน หาก debounce/noise ทำให้ touch กับ near recognized คนละเวลา จะมี state ชั่วคราวได้ ให้ตรวจ source/recognized/applied timestamps การเป็น afraid ป้องกัน touch หลัง near เข้าสถานะแล้ว แต่ไม่ได้ทำนาย near ก่อน measurement ผ่าน threshold

| State | tilt/extend/nod [rad] | RGB |
|---|---|---|
| normal | 0, 0, 0 | 60,90,140 |
| interested | .22,.18,.06 | 255,180,0 |
| happy | .10,.10,.18 sin(2π elapsed) | 40,220,80 |
| afraid | −.22,−.22,−.16 | 230,30,30 |
| sleepy | 0,−.15,−.20 | 50,40,100 |

elapsed เป็นเวลาจาก state entry หน่วย s และ nod1 Hz เป็น expression ของ model เท่านั้น นี่คือ adaptation ตามกฎและ internal state คงที่ **ไม่มีการเรียนรู้หรืออัปเดต parameter แบบ persistent** ถ้าทำ extension ให้บันทึก parameter/version ก่อน–หลัง และเรียกว่า parameter adaptation ตามวิธี update ที่ทำจริง ไม่ถือว่า learning เพียงเพราะ FSM เปลี่ยน state

## เวลาและ N/A

1. `source_time_s`: onset ที่อยู่ใน synthetic interaction หรือ sensor threshold record ก่อน debounce
2. `recognized_time_s`: event ผ่าน filter
3. `decision_time_s` / `queued_time_s`: FSM ตัดสินใจและส่ง command เข้า queue
4. `scheduled_application_s` / `actual_application_s`: scheduler ถึงเวลาจริงที่ apply command
5. `first_motion_s` / `first_rgb_s`: tick แรกที่ **output ที่ apply แล้วเปลี่ยนจริง** จาก previous output; motion epsilon1e−9 rad

`motion_latency_s=first_motion_s−source_time_s`, RGB เช่นเดียวกัน; `both_latency_s=max(first_motion_s,first_rgb_s)−source_time_s` เมื่อพบทั้งคู่ มิฉะนั้น JSON=null, CSV blank, report=N/A FSM timestamp ไม่ใช่ response onset สถานะเดิมไม่มี expression ใหม่จึง `no_state_change`; ignored combinations=`policy_held`; commands ถูก epoch ใหม่แทนก่อน apply=`preempted_before_apply`; รอไม่ทันจบ=`censored_end` ไม่มีการแทน missing ด้วย0

มี latency บางกรณีเป็น N/A อย่างมีเหตุผล เช่น fault ตอน output neutral อยู่แล้ว หรือ touch ขณะ afraid ทุก input ยังอยู่ใน source-outcome denominator รายงานจำนวน both onset และ ≤1s observed แยกจาก all source count อ่านสถานะก่อนสรุป อย่าใช้ success เฉพาะ measured samples แทน success ของทุก interaction

Primary denominator ที่ประกาศก่อนรันมี7 input: button_01, touch_01, approach_01, clear_01, near_01, clear_02, button_02 โดยต้องการ expression/recovery ใหม่ ขัดแย้ง touch_conflict และ faultที่alreadyneutral2inputยังอยู่ในall10 แต่ไม่เป็นprimaryexpected รายงาน primary_expected_count, primary_pass_1s_both_count และ primary_missing_both_count แยกกัน

Source-level latency ใน metrics รวม earliest motion/RGB onset จากทุก candidate ที่มี original input_id และ event kind เดียวกัน ทำให้ sourceที่ candidateแรกถูกpreempt แต่ candidateต่อมาapplyได้ไม่ถูกเรียกว่า missing ทั้งหมด onsetของสองmodalityอาจมาจากคนละcandidateได้ นี่เป็น **interaction-level** measurement ส่วน event-level latency/status ทุกตัวคงอยู่ใน events CSV และ candidate_status_counts/first_candidate_status ของ JSON อย่าสับสนสองระดับนี้

**simulated ≤1 s ยืนยันเฉพาะ software model** ไม่ใช่ physical movement/LED onset บนหุ่นยนต์จริง งาน hardware ต้องวัด input และ onset ด้วย clock/camera/photodiode ที่สอบเทียบ แยก motion, RGB และ both พร้อม resolution และ uncertainty

## Raw artifacts และ replay

| File | เนื้อหา |
|---|---|
| `inputs_rNN.csv` | synthetic raw sensor + measurement timestamp + original source timestamp/ID |
| `source_inputs_rNN.csv` | ทุก external input ที่คาดหวัง รวม conflicting และ fault inputs |
| `raw_C0_rNN.csv`, `raw_C1_rNN.csv` | sensor, state, queue/epoch, actual applied joint/RGB และ scheduler timestamp |
| `events_C*_rNN.csv` | candidate/decision/queue/applied/onset/latency/status/reason |
| `config.json`, `metrics.json`, `metrics.csv` | fixed contract และผล measured; JSON root `runs` มีหนึ่ง record ต่อ condition/repeat |
| `trace_C*_rNN.svg`, `report.html` | กราฟ offline และทุก source outcome |
| `source_snapshot`, `manifest.json` | source ที่ใช้และ SHA-256 ของ artifacts เพื่อ reproducibility |

```sh
python3 lab06.py --policy student --condition C1 --repeats 1 --replay results/completed/inputs_r01.csv --output-dir results/replay
```

replay ใช้ dt/config เดิมและrawinputที่บันทึกไว้ ไม่สุ่มใหม่ seedในreplaymetricsเป็นN/Aเพื่อไม่อ้างว่าdefaultseedเป็นseedของไฟล์ต้นฉบับ; configเก็บSHA-256ของinputเพื่อระบุไฟล์แน่นอน เทียบ `raw_C1_r01.csv` และ `events_C1_r01.csv` byte-for-byte ได้ ถ้า policy ไม่เปลี่ยน เมื่อรัน reference สำหรับผู้สอน ไฟล์คำตอบไม่อยู่ใน student ZIP และไม่มีความจำเป็นต่อ student commands

ส่ง transition diagram/table, prediction ก่อนรัน, student_policy.py, config/raw/events/metrics ที่เลือก, latency table ที่แยก missing status และข้ออภิปราย C0/C1 อย่างน้อย3 paired seeds พร้อมหนึ่งข้อจำกัดหรือ negative result

## Expected set ของ positive mapping ของกลุ่ม

ค่า primary_* ใน metrics.json ใช้ baseline 7 input IDs เสมอ ส่วน --contract group ตรวจ transition ของกลุ่ม แต่ไม่ได้เปลี่ยน metric subset อัตโนมัติ หาก mapping ทำให้บาง input ตั้งใจคง state ให้ประกาศ expected input IDs ก่อนรัน แล้วนับ pass_1s_both และ missing จากแต่ละ source_outcomes ตามชุดนั้นเอง ใช้ชุดเดียวกัน C0/C1 และเก็บ all 10 sources พร้อม status ห้ามเลือก subset หลังดูผล
