"""ROS2 Jazzy adapter (requires rclpy/std_msgs); verified on Ubuntu 24.04 WSL2.

Three independent executables: synthetic inputs, interaction/output publisher,
and command collector. No motor/ESP32 driver. Seven /lamp application topics;
standard ROS infrastructure topics may also appear.
"""
import csv
import json
import math
from pathlib import Path
import platform
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from std_msgs.msg import Bool, Float32, String, Float32MultiArray, MultiArrayDimension, ColorRGBA
from .bridge import Engine, load_policy
from .course_model import Config, Frame, protocol

QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                 reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE)

class TraceNode(Node):
    def __init__(self,name):
        super().__init__(name)
        self.declare_parameter('trace_file',name+'_trace.csv')
        path=Path(self.get_parameter('trace_file').value)
        path.parent.mkdir(parents=True,exist_ok=True)
        self.trace_handle=path.open('x',encoding='utf-8',newline='')
        self.trace_writer=csv.DictWriter(self.trace_handle,fieldnames=['node','host','clock','phase','topic','local_sequence','monotonic_ns','duration_ns','payload','source_latency_s'])
        self.trace_writer.writeheader()
        self.trace_counts={}

    def record(self,phase,topic,payload,duration=None):
        key=phase+topic; self.trace_counts[key]=self.trace_counts.get(key,0)+1
        self.trace_writer.writerow({'node':self.get_name(),'host':platform.node(),'clock':'perf_counter_ns same-host monotonic; no wire timestamp',
            'phase':phase,'topic':topic,'local_sequence':self.trace_counts[key], 'monotonic_ns':time.perf_counter_ns(),
            'duration_ns':duration,'payload':json.dumps(payload),'source_latency_s':''})
        self.trace_handle.flush()

    def destroy_node(self):
        self.trace_handle.close()
        return super().destroy_node()

class SyntheticInputs(TraceNode):
    def __init__(self):
        super().__init__('week07_inputs')
        self.declare_parameter('seed',41)
        self.frames=protocol(Config(),self.get_parameter('seed').value)
        self.sequence=0
        self.pubs={c:self.create_publisher(Float32 if c=='distance' else Bool,'/lamp/input/'+c,QOS) for c in ('button','touch','distance')}
        self.timer=self.create_timer(.02,self.publish_frame)

    def publish_frame(self):
        if self.sequence>=len(self.frames):
            self.timer.cancel(); self.get_logger().info('22s source protocol complete; stop nodes and inspect sidecar traces'); return
        frame=self.frames[self.sequence]; self.sequence+=1
        for channel,pub in self.pubs.items():
            value=getattr(frame,'distance_m' if channel=='distance' else channel)
            msg=Float32() if channel=='distance' else Bool(); msg.data=float(value) if channel=='distance' else bool(value)
            self.record('publish','/lamp/input/'+channel,{'data':value if math.isfinite(value) else 'NaN','virtual_sample_s':frame.time_s,
                        'virtual_acquisition_s':getattr(frame,channel+'_sample_s'),'input_id':getattr(frame,channel+'_input_id')})
            pub.publish(msg)

class Interaction(TraceNode):
    def __init__(self):
        super().__init__('week07_interaction')
        self.declare_parameter('policy_file',str(Path(__file__).with_name('student_policy.py')))
        self.engine=Engine(load_policy(self.get_parameter('policy_file').value))
        self.origin=time.perf_counter()
        self.receipts={c:{'value':0. if c!='distance' else 1.2,'time':-1.} for c in ('button','touch','distance')}
        self.subs=[self.create_subscription(Float32 if c=='distance' else Bool,'/lamp/input/'+c,lambda msg,channel=c:self.receive(channel,msg),QOS) for c in self.receipts]
        self.pubs={c:self.create_publisher(typ,'/lamp/'+c,QOS) for c,typ in (('interaction',String),('emotion',String),('servo_command',Float32MultiArray),('rgb_command',ColorRGBA))}
        self.timer=self.create_timer(.02,self.tick)

    def receive(self,channel,msg):
        self.receipts[channel]={'value':float(msg.data),'time':time.perf_counter()-self.origin}
        self.record('receive','/lamp/input/'+channel,{'data':msg.data if isinstance(msg.data,bool) or math.isfinite(msg.data) else 'NaN','timestamp_scope':'local receipt only; source acquisition unavailable'})

    def tick(self):
        started=time.perf_counter_ns(); t=time.perf_counter()-self.origin
        b,u,d=(self.receipts[c] for c in ('button','touch','distance'))
        # Wire messages lack Header. These timestamps deliberately use receipt,
        # never masquerade as source acquisition or cross-node latency.
        frame=Frame(t,b['value'],u['value'],d['value'],b['time'],u['time'],d['time'],
                    max(0.,b['time']),max(0.,u['time']),max(0.,d['time']))
        row=self.engine.step(frame)
        interaction=String(); interaction.data=row['interaction']
        emotion=String(); emotion.data=row['emotion']
        servo=Float32MultiArray(); servo.data=[row[k] for k in ('tilt_rad','extend_rad','nod_rad')]
        dimension=MultiArrayDimension(); dimension.label='tilt_extend_nod_rad'; dimension.size=3; dimension.stride=3
        servo.layout.dim=[dimension]; servo.layout.data_offset=0
        rgb=ColorRGBA(); rgb.r=row['rgb_r']; rgb.g=row['rgb_g']; rgb.b=row['rgb_b']; rgb.a=1.
        duration=time.perf_counter_ns()-started
        for name,msg,payload in (('interaction',interaction,interaction.data),('emotion',emotion,emotion.data),('servo_command',servo,list(servo.data)),('rgb_command',rgb,[rgb.r,rgb.g,rgb.b,rgb.a])):
            self.record('publish','/lamp/'+name,{'data':payload,'fault_channels':row['fault_channels'],'receipt_freshness_only':True},duration)
            self.pubs[name].publish(msg)

class OutputCollector(TraceNode):
    def __init__(self):
        super().__init__('week07_output_collector')
        self.subs=[self.create_subscription(typ,'/lamp/'+name,lambda msg,topic='/lamp/'+name:self.receive(topic,msg),QOS)
                   for name,typ in (('interaction',String),('emotion',String),('servo_command',Float32MultiArray),('rgb_command',ColorRGBA))]

    def receive(self,topic,msg):
        payload=[msg.r,msg.g,msg.b,msg.a] if isinstance(msg,ColorRGBA) else list(msg.data) if isinstance(msg,Float32MultiArray) else msg.data
        self.record('receive',topic,{'data':payload,'scope':'received command; actuator not measured'})

def spin(cls,args=None):
    rclpy.init(args=args); node=cls()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

def input_main(args=None): spin(SyntheticInputs,args)
def interaction_main(args=None): spin(Interaction,args)
def collector_main(args=None): spin(OutputCollector,args)
