# Lab07 — Seven-topic ROS2 bridge and experimental design

ชุดนี้ฝึกเชื่อม policy กับ interface ของ Week07 และออกแบบการทดลองที่เก็บหลักฐานได้ นักศึกษาเติม starter ที่รวมอยู่ใน Lab07 ได้เอง หรือใช้ policy ของกลุ่มที่ทำเสร็จจาก Lab06 มีสองทางทดลอง: offline ใช้ Python standard library และ ROS 2 ใช้เครื่อง Ubuntu 24.04 + ROS 2 Jazzy ที่เตรียมไว้แล้ว ตัวเลข, poses และ thresholds เป็น **proposed course model** ที่ยังต้องสอบเทียบเมื่อใช้กับหุ่นยนต์จริง

Offline เป็นบทบาทที่เรียกใน process เดียว ใช้เวลาเสมือน ไม่ใช่ ROS/DDS network benchmark ส่วน ROS source มีสาม executable ที่ตั้งใจให้รันเป็นคนละ process ยังไม่มี motor driver, ESP32 firmware หรือ micro-ROS Agent ในชุดนี้

## เริ่มจาก ZIP บนเครื่องสะอาด

แตก `Week07_Student_Package.zip` แล้วเปิด terminal ใน `Week07_Student_Package/lab07` ไม่ต้องลง Python packages สำหรับ offline ใช้ Python3.10+ (Windows เปลี่ยน `python3` เป็น `py -3` ได้)

```bash
python3 offline_lab.py --condition all --repeats 3 --output-dir results/starter_run
python3 check_submission.py --contract group
python3 check_proposal.py proposal.json
```

คำสั่งแรกทำงานได้ แต่ policy starter ใน `lamp_week07/student_policy.py` ยังมี TODO ดังนั้น checker สองคำสั่งหลังควร FAIL ให้เติม transition ของกลุ่มในไฟล์นี้ แล้วรัน checker จนผ่านก่อนทดลองใหม่:

```bash
python3 check_submission.py --contract group
python3 offline_lab.py --condition all --repeats 3 --output-dir results/completed_starter
```

หากมีไฟล์ `student_policy.py` ที่กลุ่มทำเสร็จจาก Lab06 ให้นำมาวางเป็น `completed_policy.py` แล้วใช้ชื่อไฟล์นั้นอย่างชัดเจน:

```bash
python3 check_submission.py --policy-file completed_policy.py --contract group
python3 offline_lab.py --policy-file completed_policy.py --condition all --repeats 3 --output-dir results/completed_run
```

ใช้ directory ใหม่ทุกครั้ง runner ปฏิเสธ directory ที่ไม่ว่างเพื่อรักษาหลักฐาน รันเฉพาะ policy ของกลุ่มที่เชื่อถือได้; checker แยก process/ล้าง inherited environment/timeout5s แต่ไม่ใช่ OS sandbox

## เริ่มจาก GitHub หลังเผยแพร่ Lab07

เมื่อผู้สอนเผยแพร่โฟลเดอร์ `lab_07` แล้ว ใช้คำสั่งต่อไปนี้แทนการแตก ZIP:

```bash
git clone https://github.com/potiwat/RAE67_bio_ins.git
cd RAE67_bio_ins/lab_07
python3 check_submission.py --contract group
python3 offline_lab.py --condition all --repeats 3 --output-dir results/starter_run
```

คำสั่ง checker ของ starter ควร FAIL จนกว่าเติม TODO ครบ เช่นเดียวกับทาง ZIP ทุกคำสั่งที่เหลือในคู่มือนี้เริ่มจากโฟลเดอร์ที่มี `offline_lab.py` ไม่ต้องมี Lab06 ติดตั้งอยู่ก่อน ผลทดลองและ logs เก็บในเครื่องของกลุ่มตาม `.gitignore`; ส่งหลักฐานงานตามช่องทางที่ผู้สอนกำหนด

## Interface ที่คงเจ็ด application topics

| Topic | Message type | หน่วย/ความหมาย |
|---|---|---|
| `/lamp/input/button` | `std_msgs/msg/Bool` | true/false |
| `/lamp/input/touch` | `std_msgs/msg/Bool` | true/false |
| `/lamp/input/distance` | `std_msgs/msg/Float32` | m |
| `/lamp/interaction` | `std_msgs/msg/String` | event: fault/near/clear/touch/button/approach/timeout/idle หรือ empty เมื่อไม่มี event ใน tick |
| `/lamp/emotion` | `std_msgs/msg/String` | normal/interested/happy/afraid/sleepy |
| `/lamp/servo_command` | `std_msgs/msg/Float32MultiArray` | rad; order `[tilt, extend, nod]` |
| `/lamp/rgb_command` | `std_msgs/msg/ColorRGBA` | r/g/b = Lab06 integer/255; alpha=1 |

`extend` คือชื่อ semantic joint ของโคม คำสั่งนี้ยังเป็น **rad** ไม่ใช่ linear extension หน่วย m ต้องมี linkage/actuator calibration ก่อนแปลงไป hardware ไม่มีการแปลง degree โดยเงียบ Float32MultiArray deprecated ตั้งแต่ Foxy แต่คงชนิดนี้ตาม interface รายวิชา หากเปลี่ยนเป็น custom message ต้องออก contract version ใหม่

ROS topics ระบบเช่น `/rosout` และ `/parameter_events` อาจปรากฏด้วย; ข้อกำหนดเจ็ดหมายถึงเจ็ด `/lamp/...` topics เท่านั้น ทั้ง publisher/subscriber ในชุดใช้ **RELIABLE, KEEP_LAST depth10, VOLATILE** คู่ QoS ต้อง compatible; reliable subscriber รับ best-effort publisher ไม่ได้โดยอัตโนมัติ reliable ไม่ได้ทำให้ค่าที่ส่งเก่าเป็นค่าปัจจุบัน

## Offline experiment

- C0: ideal modeled transport; delay0/drop0
- C1: profile ที่มี delay choices0/.02/.04/.06/.10/.14/.18s, random drop probability.08 และ burst drop12.50–12.70s
- แต่ละ condition มีสาม repeats seeds41/42/43; คู่ seed ใช้ source stimuli เหมือนกัน Policy, guarded debounce/hysteresis, bounds/slew, duration22s, dt.02s และ scheduler.04s เหมือนกัน
- C1 เปลี่ยน jitter และ drop พร้อมกัน จึงศึกษาผลของ **profile** และแยกเหตุเชิงสาเหตุของแต่ละส่วนไม่ได้ มันไม่ใช่การจำลอง guarantee ของ reliable DDS ใช้การทดลองแยก delay-only/drop-only หากต้องการแยกผล
- Messages ที่มาถึง out of order ไม่ยอมย้อนข้อมูล latest ใช้ sequence ใน offline sidecar เท่านั้น ไม่ใส่ sequence ลง Bool/Float32 บน wire
- offline freshness ใช้ acquisition sample time ที่รู้จาก fixture; ROS adapter ใช้ receipt freshness เท่านั้น สองอย่างนี้ไม่เท่ากัน

ไฟล์ต่อ trial: `input_trace.csv` (ทุก publish, planned delay/drop, receipt, accepted/out-of-order/censored), `command_trace.csv` (applied commands), `events.csv`, `metrics.json`, `config.json` ทั้ง directory มี `summary.json`, `report.html`, `source_snapshot/` และ `manifest.json` SHA256 เก็บ raw traces ก่อนวิเคราะห์ และไม่แก้ผลย้อนหลัง

| Metric | นิยาม/denominator |
|---|---|
| published/received/dropped | Message counts รวม3input topics; censoredหลัง22sแยกจากdrop |
| accepted/out-of-order | Received = accepted + discarded out-of-order |
| transport age | receipt time − publish time; สรุปเฉพาะ messages ที่ received |
| fault ticks | invalid OR stale channels /1101ticks; มี invalid/stale probes เหมือนกันทั้งC0/C1 |
| state transitions | เปลี่ยน emotion ระหว่าง consecutive ticks |
| both latency | max(first applied movement, first applied RGB) − original source time, รวม candidates input_id+kindเดียวกัน |
| missing both | first movementหรือRGBไม่พบ; JSONnull, CSVblank, reportN/A; ห้ามแทน0 |

Lab07 ค้นหา onset ภายใน trial 22 s: ถ้า motion หรือ RGB ไม่ครบจึงเป็น missing และ `both_latency_s`/`pass_1s_both` เป็น null หากพบทั้งคู่แต่ latency เกิน 1 s ให้เก็บค่าตัวเลขและรายงาน `pass_1s_both=False` เป็น deadline fail แยกจาก missing กลุ่มต้องประกาศทั้ง deadline และ observation window ก่อนรัน

ทุก trial เก็บสิบ source inputs รวม conflict และ fault ที่ไม่จำเป็นต้องสร้าง expression ใหม่ `primary_*` ใช้ baseline expected subset เจ็ด IDs: button_01,touch_01,approach_01,clear_01,near_01,clear_02,button_02 หากกลุ่มเปลี่ยน positive mapping ให้ **ประกาศ expected input IDs ก่อนรัน** แล้วคำนวณ pass/miss จาก `source_outcomes` ด้วยชุดเดียวกันทั้งC0/C1 ห้ามรายงาน primary7 เป็นผล policy ของกลุ่มโดยไม่ตรวจสมมติฐานนี้ ไม่เลือก denominator ตามผลที่ออก

Replay schedule และ inputs ที่เก็บไว้หนึ่ง trial:

```bash
python3 offline_lab.py --policy-file completed_policy.py --condition C1 --repeats 1 --replay results/completed_run/C1_r02/input_trace.csv --output-dir results/replay_check
```

Replay อ่าน seed จาก adjacent `config.json`; ข้อมูล value/sample/source/IDs และ delay/drop จาก CSV ถ้า policy/code/config เปลี่ยนผลอาจเปลี่ยน เปรียบเทียบ command/events และ SHA อย่าอ้างว่ารันซ้ำตรงกันจนตรวจ

## Mini-project AHM–SO(2) CPG offline simulation

`ahm_cpg_project.py` is a separate proposed-course-model experiment for the Mini Project; it does not change the seven-topic ROS bridge and does not model ROS/DDS or physical hardware. It connects the Lab04-style bounded Euler AHM state to the Lab03 SO(2) recurrence, then compares:

- C0: fixed `phi=0.20 rad/update`
- C1: `phi=clamp(0.20 + 0.20*R, 0.10, 0.45) rad/update`

Both conditions use `alpha=1.10`, the same initial oscillator state and paired source stimulus, `dt=0.05 s`, a 10 s warm-up, a 10 s stimulus and a 30 s analysis window. The simulation includes an explicitly proposed first-order semantic actuator response (`tau=0.15 s`, slew bound `0.8 rad/s`); it is not a measured motor model. Metrics are applied-command nod frequency during stimulation and command tracking RMSE over the analysis window. Physical angle/onset remains N/A.

Run into a new output directory:

```bash
python3 ahm_cpg_project.py --output-dir results/project_ahm_cpg
```

Outputs include each paired trial's `trace.csv`, `config.json`, and `metrics.json`, plus `summary.json`, `report.html`, and a SHA256 `manifest.json`. These three deterministic source traces are software replications, not independent human or hardware trials. The 10-minute participant protocol and real robot tests remain separate work requiring the approved platform and environment.

Generated v2 outcome (`results/project_ahm_cpg_v2/summary.json`, 3 paired software runs/condition): C0 mean nod frequency `0.625 Hz`, tracking RMSE `0.01458 rad`; C1 `1.218 Hz`, `0.01804 rad`. Within this proposed model, C1 increased frequency by `0.593 Hz` while RMSE increased by `0.00346 rad`; these values are not physical measurements or statistical evidence from independent participants.

## ROS2 track บนเครื่องที่เตรียมไว้

Environment นี้ติดตั้ง Ubuntu24.04 + ROS2 Jazzy บน WSL2 แล้ว; `lamp_week07` build ผ่านด้วย colcon และรัน synthetic smoke test 22 s ได้ครบทั้ง 7 application topics พร้อม QoS/rosbag inspection. หากทำซ้ำบนเครื่องอื่น ให้เตรียม Ubuntu24.04, ROS2Jazzy, rclpy/std_msgs/colcon ตาม [official installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html); ไม่ต้องติดตั้ง ROS บน Windows เพื่อทำ offline

หลักฐาน run นี้อยู่ใน `results/ros2_wsl/run03/`: `inputs.csv`, `interaction.csv`, `collector.csv`, topic/QoS snapshots, sample RGB message, bag recorder log และ `bag/run01_0.mcap` (22.16 s, 6,911 messages). Runtime discovery ยืนยัน publisher/subscriber และ RELIABLE/VOLATILE; CLI รายงาน history depth เป็น UNKNOWN แม้ node กำหนด KEEP_LAST depth 10 ใน source. Trace พบ input publish 1,101/channel แต่ interaction receive 1,081/channel; output publish ประมาณ 1,426/topic และ collector receive 1,373/topic. เนื่องจาก standard wire messages ไม่มี source sequence ID จึงระบุไม่ได้ว่าความต่างเกิดตรงจุดใด และห้ามเรียกเป็น measured packet-loss rate. ใช้ synthetic inputs กับ semantic command เท่านั้น—ไม่มี hardware, physical onset หรือ human trial.

วาง lab directory ทั้งชุดเป็น `ros2_ws/src/lamp_week07` (ไม่รวม results/instructor/tests เมื่อแจกนักศึกษา) แล้วเปิด terminal ที่ `ros2_ws`:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select lamp_week07
source install/setup.bash
```

นำ policy ของกลุ่มที่ผ่าน checker แล้วไปไว้ที่ราก workspace เป็น `completed_policy.py` ถ้าเติม starter ของ Lab07 ให้คัดลอก `lamp_week07/student_policy.py` เป็นไฟล์นี้ เปิดสาม terminals โดยแต่ละ terminal อยู่ที่ `ros2_ws` และ source `/opt/ros/jazzy/setup.bash` กับ `install/setup.bash`; เริ่ม collector และ interaction ก่อน inputs:

```bash
ros2 run lamp_week07 output_collector --ros-args -p trace_file:=logs/run01/collector.csv
```

```bash
ros2 run lamp_week07 interaction --ros-args -p policy_file:="$(pwd)/completed_policy.py" -p trace_file:=logs/run01/interaction.csv
```

```bash
ros2 run lamp_week07 synthetic_inputs --ros-args -p seed:=41 -p trace_file:=logs/run01/inputs.csv
```

Trace path ใช้ exclusive-create: เปลี่ยน run01 เป็นชื่อใหม่เมื่อทดลองใหม่ Inputs จบ22s virtual stimulus แต่ receipt timer และ wall clock จริงอาจไม่ตรง22s; หลัง messageจบให้ Ctrl+C แต่ละ terminal รวม collector/interaction ซึ่งรันต่อและจะเห็น timeout/stale fault

Reset ทั้งสาม processes ทุก trial และบันทึก startup offset; อย่าเปรียบเทียบ run ที่ initialstate/เวลาเริ่มต่างกันโดยไม่ควบคุมค่า การบันทึก synthetic acquisition time อยู่ใน input sidecar เท่านั้น จึง **offline stale-sample probeไม่ส่งผ่าน Boolบนwire**; ทดสอบ ROS receipt-stale โดยหยุด publisher และดู neutral fallback. ROS callbackอาจ jitter/ค้างจนมีหลายqueuedjobsพร้อมกัน; slew.8rad/sใน modelอิง nominaldt.02 จึงไม่ใช่ measuredphysicalslew guarantee ต้องใช้ driver watchdog/realelapsedtime limiter และสอบเทียบก่อนขับ servoจริง

```bash
ros2 topic list
ros2 topic info /lamp/servo_command --verbose
ros2 topic echo /lamp/rgb_command
ros2 bag record -o bags/run01 --topics /lamp/input/button /lamp/input/touch /lamp/input/distance /lamp/interaction /lamp/emotion /lamp/servo_command /lamp/rgb_command
```

เริ่ม bag ก่อน inputs ใน terminal เพิ่ม (ยังคงเจ็ด application topics) rosbag เก็บ message/receipt/playback แต่ไม่ได้เพิ่ม Header ที่ไม่มีอยู่ ดู [official bag QoS guide](https://docs.ros.org/en/jazzy/How-To-Guides/Overriding-QoS-Policies-For-Recording-And-Playback.html)

## Clock และ measurement boundary

Bool/String/Float32/ColorRGBA ใน interface ไม่มี Header ROS logs บันทึก `perf_counter_ns`, node/host/topic/local_sequence/phase/payload ใน sidecar ส่วน `duration_ns` ใน interaction output วัดเฉพาะ engine step และการสร้าง messages ก่อน log/publish ไม่ใช่เวลารวมของ callback, logging, publishing หรือ network ค่า phase=publish เป็น log ของความพยายามส่งก่อนเรียก publisher ต้องตรวจ reception เพิ่ม local_sequence ของ publish/receive ไม่รับประกันว่าเป็น ID เดียวกันเมื่อมี drop จึง **source_latency_s เว้นว่าง (N/A)** ไม่หักเวลาข้าม nodes จาก ordinal/payload ที่ซ้ำกันโดยเดา

เวลาที่วัดใน node บอก processing boundary ที่ระบุ ส่วน collector receipt บอก command arrival ทั้งสองยังไม่ใช่ physical motion/RGB onset ต้องมี input identity ใน log wrapper, clock correlation/synchronization + error bound และวัด actuator จริงก่อนอ้าง source→physical latency ต่างเครื่องห้ามลบ monotonic timestamps โดยไม่มี clock mapping ROS receiver ไม่รู้ acquisition time จาก Bool/Float32 จึงตรวจได้เพียง receipt freshness; sensor ที่ส่งค่าเก่าซ้ำต่อเนื่องยังดู fresh ต้องออกแบบ hardware acquisition watchdog/sequence/log boundary เพิ่มก่อนทดสอบจริง

## งานส่ง Week07

1. วาด graph พร้อม3rolesและ micro-ROS/ESP32/Agent extension ที่กลุ่มจะสร้าง ระบุ node/topic/unit/QoS และ boundary ที่มี/ไม่มี timestamps
2. รัน policy ของกลุ่มที่เติมจาก Lab07 starter หรือทำเสร็จจาก Lab06 ผ่าน bridge; แนบ topic contract, traces/config และผลสอง conditions × สาม repeats โดยเก็บ misses
3. กรอก `proposal.json` และทำ proposal2–3หน้า: biological inspiration/source, AHM≥1, Dr. Poramate SO(2) CPG, AHM–CPGหรือAHM–emotion integration, baseline,≥2conditions,≥2metrics,conditionละ≥3repeats, **simulation AND real robot**, scenarioเล่นกับคน600s พร้อมcontrols/calibration/safety/timeline
4. Offline22sช่วยเตรียม protocol ไม่แทน human scenario10นาที ไม่แทน AHM/CPG implementation และไม่แทน robot verification

## แหล่งอ้างอิงและที่มา

`lamp_week07/course_model.py` และ incomplete student policy/transition checker ต่อจาก Lab06 ของรายวิชา; ไม่รวม completed instructor policy ใน student package ROS source/units ใช้ [std_msgs](https://github.com/ros2/common_interfaces/tree/jazzy/std_msgs) และ [QoS documentation](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html) ข้อกำหนดรายวิชามาจาก Week07 เดิมของผู้สอน ตัว numerical mapping/transportstress ของ lab นี้คือ proposed course model
