# Surveillance_Morphwalker


## A Transformable Wheel–Leg Hybrid Robot for Disaster Rescue and Surveillance

<p align="center">
  <b>One Robot. Two Locomotion Modes. Built for Mixed Terrain.</b>
</p>

---

## 📌 Overview

**Surveillance MorphWalker** is a compact transformable wheel–leg hybrid robot designed for **disaster rescue, surveillance, inspection, and hazardous-environment exploration**.

The robot combines the speed and efficiency of wheeled locomotion with the terrain adaptability of legged locomotion. It can transform between **wheel mode** and **leg mode** using a servo-actuated four-bar linkage mechanism, allowing it to adapt to different terrain conditions.

An onboard **Raspberry Pi 4** provides real-time vision processing and surveillance, while a distributed **ESP32-based control architecture** manages locomotion and mechanical transformation.

The system is designed as an affordable and locally maintainable robotic platform using commercially available components and 3D-printed structural parts.

---

## 🎯 Problem Statement

Disaster environments such as earthquakes, floods, landslides, and building collapses contain unstable and unpredictable terrain.

Conventional robotic platforms have important limitations:

* **Wheeled robots** are fast and efficient but struggle with rubble, steps, and uneven terrain.
* **Legged robots** can negotiate difficult terrain but are comparatively slow and complex.
* **Human rescuers** may be exposed to unstable structures, toxic environments, and other hazards during initial reconnaissance.
* Existing surveillance robots may provide visual information but lack adaptive locomotion and physical interaction capabilities.

Therefore, there is a need for a robotic platform that can:

* Traverse mixed and unpredictable terrain.
* Provide continuous visual surveillance.
* Adapt its locomotion according to terrain conditions.
* Reduce human exposure to hazardous environments.
* Remain affordable, repairable, and locally maintainable.

---

## 💡 Proposed Solution

MorphWalker addresses these challenges by combining two locomotion modes in a single robotic platform.

### 🛞 Wheel Mode

Used for:

* Flat terrain
* Semi-flat terrain
* Faster movement
* Efficient traversal

### 🦿 Leg Mode

Used for:

* Rubble
* Steps
* Uneven terrain
* Obstacles
* Rough surfaces

The robot uses a **servo-driven four-bar linkage mechanism** to transform the wheel structure into a leg configuration.

```text
              MORPHWALKER
                   │
          ┌────────┴────────┐
          │                 │
          ▼                 ▼
     WHEEL MODE         LEG MODE
          │                 │
     Fast movement     Obstacle traversal
     Flat terrain      Uneven terrain
          │                 │
          └────────┬────────┘
                   │
            Adaptive Mobility
```

---

## ⚙️ Key Features

* Transformable wheel–leg locomotion
* Servo-driven four-bar linkage mechanism
* Raspberry Pi 4 onboard processing
* Real-time camera surveillance
* OpenCV-based vision processing
* Object and obstacle detection
* Distributed ESP32 control architecture
* Wireless human-supervised operation
* Real-time video streaming
* 3D-printed mechanical components
* Modular design
* Low-cost and locally maintainable architecture

---

## 🏗️ System Architecture

The robot follows a hierarchical distributed architecture.

```text
                  ┌───────────────────┐
                  │      CAMERA       │
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │   RASPBERRY PI 4  │
                  │                   │
                  │ Vision Processing  │
                  │ Object Detection  │
                  │ Decision Making    │
                  │ Video Streaming    │
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │    MASTER ESP32   │
                  │                   │
                  │ Motion Coordinator│
                  └─────────┬─────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Slave    │  │ Slave    │  │ Slave    │
        │ ESP32    │  │ ESP32    │  │ ESP32    │
        └────┬─────┘  └────┬─────┘  └────┬─────┘
             │             │             │
             └─────────────┼─────────────┘
                           │
                           ▼
                    Wheel Modules
```

### Raspberry Pi

The Raspberry Pi acts as the high-level processing unit.

Responsibilities include:

* Camera processing
* Object detection
* Video streaming
* High-level decision making
* Robot state monitoring
* Communication with the ESP32 control system

### Master ESP32

The Master ESP32 coordinates the low-level robotic system.

Responsibilities include:

* Receiving commands
* Coordinating locomotion
* Synchronizing wheel transformation
* Communicating with slave controllers

### Slave ESP32 Controllers

The slave controllers manage individual wheel modules.

Responsibilities include:

* DC motor control
* Servo control
* Wheel transformation
* Local actuator control

---

## 🔄 Wheel-to-Leg Transformation

Each wheel incorporates a **four-bar linkage mechanism** driven by a servo motor.

The transformation process changes the wheel from a compact circular configuration into an expanded leg-like configuration.

```text
WHEEL MODE
     ↓
Servo Actuation
     ↓
Linkage Expansion
     ↓
LEG MODE
```

When the terrain is suitable for wheeled traversal, the robot remains in wheel mode.

When an obstacle or uneven terrain is detected, the transformation mechanism can be activated to improve terrain adaptability.

---

## 👁️ Vision System

A camera connected to the Raspberry Pi provides real-time environmental information.

The vision pipeline uses **OpenCV** for image processing.

### Vision Pipeline

```text
Camera
   ↓
Frame Acquisition
   ↓
Image Preprocessing
   ↓
Edge / Contour Detection
   ↓
Obstacle Identification
   ↓
Terrain Assessment
   ↓
Movement / Transformation Decision
```

The system can perform:

* Real-time camera streaming
* Object detection
* Obstacle detection
* Terrain analysis
* Environmental monitoring

The project documentation reports an average vision-processing performance of approximately **18 FPS** during testing.

---

## 🧭 Autonomous Navigation

The navigation methodology uses environmental information to determine appropriate robot behavior.

### Basic decision logic

```text
              Environment
                   │
                   ▼
             Camera Input
                   │
                   ▼
           Terrain Assessment
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
   Clear Path   Small       Large
                Obstacle    Obstacle
        │          │          │
        ▼          ▼          ▼
   Move Forward  Slow/     Transform
                 Re-route   to Leg Mode
```

The intended behavior is:

* Clear path → continue movement in wheel mode.
* Small obstacle → slow down or re-route.
* Large obstacle → activate wheel-to-leg transformation.
* Uneven terrain → prioritize leg mode for stability.

---

## 🎮 Control Modes

MorphWalker is designed around human-supervised robotic operation.

### Autonomous Mode

The robot uses environmental information for:

* Navigation
* Obstacle detection
* Locomotion decisions
* Transformation decisions

### Remote Control Mode

The operator controls the robot wirelessly.

### Surveillance Mode

The robot provides continuous visual monitoring while stationary or moving slowly.

---

## 🔧 Hardware Components

| Component                     | Purpose                        |
| ----------------------------- | ------------------------------ |
| Raspberry Pi 4 Model B        | Central processing and control |
| ESP32 Master                  | Motion coordination            |
| ESP32 Slave Controllers       | Wheel-module control           |
| MG995 Servo Motors            | Wheel-leg transformation       |
| DC Gear Motors                | Locomotion                     |
| IBT-2 Motor Driver            | Motor control                  |
| USB Camera                    | Visual surveillance            |
| FlySky Transmitter            | Wireless control               |
| Li-Po Battery                 | Power supply                   |
| Buck Converter                | Voltage regulation             |
| PLA Filament                  | 3D-printed components          |
| Bearings / Shafts / Fasteners | Mechanical assembly            |

---

## 💻 Software Stack

| Software / Technology    | Purpose                        |
| ------------------------ | ------------------------------ |
| Python                   | Control and vision programming |
| C++ / Embedded C         | ESP32 control                  |
| OpenCV                   | Computer vision                |
| YOLO                     | Object detection               |
| Raspberry Pi OS / Ubuntu | Computing platform             |
| Arduino IDE              | ESP32 development              |
| Fusion 360 / SolidWorks  | CAD design                     |
| Git                      | Version control                |
| GitHub                   | Project repository             |

---

## 📊 Prototype Specifications

| Parameter                       | Specification |
| ------------------------------- | ------------: |
| Transformation time             |  ~2–3 seconds |
| Average transformation time     |  ~2.7 seconds |
| Vision processing               |       ~18 FPS |
| Weight                          |        3–5 kg |
| Typical mixed-operation runtime |   ~28 minutes |
| Continuous wheeled operation    |   ~35 minutes |
| Continuous legged operation     |   ~22 minutes |
| Structure                       |    3D-printed |
| Primary material                |           PLA |

---

## 🧪 Experimental Results

The prototype was evaluated for transformation, vision processing, autonomous navigation, and power performance.

### Mechanical Transformation

* Average transformation time: **2.7 ± 0.3 seconds**
* Minimum transformation time: **2.2 seconds**
* Maximum transformation time: **3.4 seconds**
* Test cycles: **20**

### Vision Processing

* Average processing rate: **18 FPS**
* Processing latency: approximately **65 ± 8 ms**

### Obstacle Detection

| Obstacle Type     | Detection Accuracy |
| ----------------- | -----------------: |
| Vertical Walls    |                98% |
| Steps & Curbs     |                96% |
| Small Objects     |                92% |
| Irregular Terrain |                89% |

### Autonomous Navigation

| Test Section    | Success Rate |
| --------------- | -----------: |
| Flat Surface    |         100% |
| Incline         |         100% |
| Obstacle Field  |          90% |
| Rough Terrain   |          80% |
| Combined Course |          85% |

---

## 🔋 Power Performance

Using the tested 12 V, 3300 mAh Li-Po battery:

| Operating Condition     | Runtime |
| ----------------------- | ------: |
| Continuous wheel mode   | ~35 min |
| Continuous leg mode     | ~22 min |
| Typical mixed operation | ~28 min |
| Intermittent operation  | 45+ min |

---

## 🧩 Project Development Phases

### Phase 1 — Design

* Requirement definition
* Mechanical design
* CAD modelling
* Component selection
* Software architecture

### Phase 2 — Fabrication

* 3D printing
* Mechanical assembly
* Electronics integration
* Wiring
* Initial testing

### Phase 3 — Integration

* ESP32 control
* Raspberry Pi integration
* Camera integration
* Vision processing
* Locomotion integration
* Transformation testing

### Phase 4 — Autonomous Operation

* Environmental perception
* Obstacle detection
* Decision making
* Adaptive locomotion
* Autonomous transformation

### Phase 5 — Future Development

* Advanced perception
* Sensor fusion
* SLAM
* Environmental sensing
* Multi-robot coordination

---

## 🚀 Future Scope

The platform can be extended with:

* LiDAR-based SLAM
* Thermal cameras
* Gas and chemical sensors
* Depth cameras
* IMU integration
* Advanced terrain classification
* Improved autonomous navigation
* Multi-robot coordination
* Waterproofing
* Ruggedized mechanical components
* Energy optimization
* Autonomous mission planning

---

## 🌍 Applications

MorphWalker can be adapted for:

### Disaster Response

* Earthquake reconnaissance
* Building-collapse inspection
* Landslide response
* Flood-zone inspection

### Industrial Inspection

* Hazardous-area inspection
* Gas/chemical environments
* Confined-space inspection
* Infrastructure monitoring

### Surveillance

* Remote surveillance
* Perimeter monitoring
* Continuous visual inspection

### Environmental Exploration

* Difficult terrain exploration
* Remote environmental monitoring
* Hazardous-zone reconnaissance

---

## ⚠️ Current Limitations

The current prototype has several limitations:

* Limited battery endurance
* Prototype-scale mechanical construction
* Limited field testing
* Vision performance can be affected by low-light or smoky environments
* Full autonomous navigation requires further development
* Self-righting capability is not currently implemented
* Additional environmental sensors are required for advanced disaster-response applications

---

## 📁 Repository Structure

```text
Surveillance-MorphWalker/
│
├── README.md
│
├── hardware/
│   ├── esp32/
│   ├── motors/
│   ├── servos/
│   └── wiring/
│
├── software/
│   ├── vision/
│   ├── navigation/
│   ├── control/
│   └── streaming/
│
├── mechanical/
│   ├── chassis/
│   ├── wheel-leg/
│   └── assemblies/
│
├── cad/
│
├── documentation/
│
├── images/
│
└── tests/
```

---

## 👥 Project Team

**Department of Robotics and Artificial Intelligence**
**Bangalore Institute of Technology, Bengaluru**

| Team Member        | Role                                                                                   |
| ------------------ | -------------------------------------------------------------------------------------- |
| **Taksha Tangudu** | ROS2 & Gazebo Simulation, Robotic Arm and Wheel CAD Design, ESP32 Master–Slave Control |
| **Vijhortha VS**   | Computer Vision & Perception, Raspberry Pi Programming                                 |
| **Raja R**         | Electronics Management, Mechanical Assembly of Robot and Arm                           |
| **Varun V**        | Mechanism Design, Robot & Arm Assembly, System Architecture Design                     |


### Project Guide

**Prof. Sunitha M. K.**
Assistant Professor
Department of Robotics and Artificial Intelligence
Bangalore Institute of Technology

---

## 📚 References

1. R. Cao, J. Gu, C. Yu, and A. Rosendo, *"OmniWheg: An Omnidirectional Wheel-Leg Transformable Robot,"* IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS), 2022.

2. L. Bai, X. Li, Y. Sun, J. Zheng, and X. Chen, *"A Wheel-Legged Mobile Robot with Adjustable Body Length for Rescue and Search,"* IEEE International Conference on Advanced Robotics and Mechatronics, 2021.

3. B. Katz, J. D. Carlo, and S. Kim, *"Mini Cheetah: A Platform for Pushing the Limits of Dynamic Quadruped Control,"* IEEE International Conference on Robotics and Automation, 2019.

4. I. Mertyuz, A. K. Tanyıldızı, B. Taşar, A. B. Tatar, and O. Yakut, *"Fuhar: A Transformable Wheel-Legged Hybrid Mobile Robot,"* Robotics and Autonomous Systems, 2020.

5. W.-H. Chen, H.-S. Lin, Y.-M. Lin, and P.-C. Lin, *"TurboQuad: A Novel Leg–Wheel Transformable Robot with Smooth and Fast Behavioral Transitions,"* IEEE Transactions on Robotics, 2017.

6. Y.-S. Kim et al., *"Wheel Transformer: A Wheel-Leg Hybrid Robot with Passive Transformable Wheels,"* IEEE Transactions on Robotics, 2014.

7. G. Bradski, *"The OpenCV Library,"* Dr. Dobb's Journal of Software Tools, 2000.

---

## 📄 License

This project is developed for **academic, research, and educational purposes**.

The licensing terms for source code, CAD files, and hardware designs will be defined as the project repository is prepared for public release.

---

## ⭐ Vision

> **MorphWalker is designed to put a robot where humans should not have to go first.**

By combining adaptive locomotion, real-time surveillance, and intelligent decision-making, MorphWalker aims to provide a safer and more versatile platform for inspection and disaster-response robotics.

---

# 🤖 Surveillance MorphWalker

### **Adaptive Mobility • Real-Time Surveillance • Intelligent Robotics**
