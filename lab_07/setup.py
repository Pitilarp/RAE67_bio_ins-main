from setuptools import setup
setup(name='lamp_week07',version='0.1.0',packages=['lamp_week07'],
      data_files=[('share/ament_index/resource_index/packages',['resource/lamp_week07']),('share/lamp_week07',['package.xml','interface_contract.json'])],
      install_requires=['setuptools'],zip_safe=True,maintainer='Bio-Inspired Robotics teaching team',maintainer_email='teaching@example.invalid',
      description='Week07 seven-topic teaching adapter; proposed course model',license='UNLICENSED - educational course materials',
      entry_points={'console_scripts':['synthetic_inputs=lamp_week07.ros_nodes:input_main','interaction=lamp_week07.ros_nodes:interaction_main','output_collector=lamp_week07.ros_nodes:collector_main']})
