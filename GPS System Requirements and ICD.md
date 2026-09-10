### GPS Telemetry System Requirements and Interface Control Document (ICD)

#### 1\. Introduction and System Overview

##### 1.1. System Strategy and Strategic Importance

In high-reliability aerospace and fleet management contexts, the integrity of spatial data acquisition is mission-critical. The GPS Telemetry System provides a deterministic framework for continuous coordinate acquisition and localized logging. By employing standardized communication protocols and rigorous error-handling architectures, the system ensures that fleet managers possess high-fidelity records for post-mission spatial analysis and real-time operational situational awareness.

##### 1.2. Document Scope and Goal

The primary objective of this specification is to define the requirements for obtaining GPS coordinates from hardware interfaces and ensuring data integrity during transition to local storage. This document governs the ingestion of raw NMEA data, the extraction of geodetic coordinates, and the appending of processed telemetry to a standardized telemetry.csv file for long-term archiving.

##### 1.3. Primary User Story

The following functional utility grounds the technical requirements detailed herein:"As a fleet manager, I want the system to continuously read GPS coordinates from our vehicle's hardware so that I can log its location."

##### 1.4. System Identification

The GPS Telemetry System relies on standard $GPGGA NMEA ASCII sentences. To ensure high-reliability development and prevent hardware latch-ups during the prototyping phase, the system utilizes a transition path from a simulated Linux pseudo-terminal (PTY) environment to physical serial deployment.&nbsp;

#### 2\. Hardware and Electrical Interface Specifications

##### 2.1. Communication Layer Context

The system utilizes a Universal Asynchronous Receiver-Transmitter (UART) protocol. Standardizing on UART 8N1 provides a low-level, low-latency telemetry path. This configuration ensures that the communication layer remains consistent whether the system is interfaced with physical hardware or a software-defined "Hardware Double."

##### 2.2. UART Configuration (Req: GPS-E-0210)

The system shall strictly adhere to the following serial settings to maintain parity with space-grade Science Unit standards:| Parameter | Setting | Applicable Requirement || \------ | \------ | \------ || **Baud Rate** | 9600 | GPS-E-0210 || **Data Width** | 8-bit | GPS-E-0210 || **Parity** | None | GPS-E-0210 || **Start Bit** | 1 | GPS-E-0210 || **Stop Bit** | 1 | GPS-E-0210 |

##### 2.3. Simulation Protocol (Req: GPS-E-0010)

For development iterations, the system shall simulate physical hardware using a Linux pseudo-terminal (PTY) master/slave pair. The slave device (e.g., /dev/pts/N) shall act as a drop-in replacement for the physical serial port.**Synthesis:**  This allows the gps\_client.py implementation to remain hardware-agnostic. By interacting with the PTY exactly as it would a hardware UART, the system enables a seamless transition to physical flight hardware without modifying core logic.

##### 2.4. Integration Limits (Req: GPS-E-0020)

To preserve the physical integrity of serial interfaces during integration, the system shall be limited to a maximum of 10 mate/de-mate cycles for physical flight-grade connectors, in accordance with the FIPEX-E-0020 model.

#### 3\. Software Interface and Data Formatting Standards

##### 3.1. Strategic Data Integrity

Standardized data ordering and timing constraints are critical to prevent system blocking and potential data corruption. Deterministic software interfaces eliminate the risk of infinite loops and ensure cross-platform compatibility.

##### 3.2. Byte Order Specification (Req: GPS-SW-0015)

The system shall strictly enforce  **Little Endian**  byte order (Least Significant Byte first) for all multi-byte sequences.**Synthesis:**  This prevents catastrophic spatial errors when moving data between different processor architectures. Whether the data is processed on an ARM-based embedded controller or an x86 workstation, the interpretation of the telemetry remains identical.

##### 3.3. Timing and Timeouts (Req: GPS-SW-0270)

The system shall enforce a deterministic  **500ms timeout**  for all incoming serial packets. If a packet is not completed or the serial buffer is empty for the duration of the timeout, the system shall trigger a SyncError.**Synthesis:**  This timeout is the primary tool for detecting a "frozen" simulation or a physical hardware disconnect. It prevents the system from entering a permanent "blocked" state, allowing the state machine to transition to an error recovery routine.

##### 3.4. Data Transmission Order (Req: GPS-SW-0016)

In alignment with FIPEX source models, data transmission shall be bit-ordered such that the Least Significant Bit (LSB) of every byte is sent first. This rule applies even though the NMEA data is transmitted as ASCII characters.

#### 4\. Operational State Machine and State Descriptions

##### 4.1. Deterministic Framework

The GPS Telemetry System operates through four primary states. This state machine provides a deterministic framework for system management and error recovery without human intervention.

##### 4.2. Functional State Table

State,Description,Transition Logic,Applicable Req

INIT,Hardware and UART/PTY initialization.,Auto-transition to STANDBY upon success.,GPS-SM-0010

STANDBY,Idle state. PTY connection is active.,Switch to SCIENCE via CMD\_ID script trigger.,GPS-SM-0020

SCIENCE,Active Logging. Parses $GPGGA to CSV.,Transition to ERROR on 500ms timeout.,GPS-SM-0030

ERROR,Handling of UART drops or sync errors.,Executes 5-step recovery procedure.,GPS-SM-0040

##### 4.3. Error Handling Procedure (Req: GPS-SW-0140)

If an error or timeout occurs during operation, the system shall execute the following sequence precisely:

1. **ABORT**  the current script and operations.  
2. Request a  **SU\_R\_SDP**  (Science Data) packet.  
3. Request a  **SU\_R\_HK**  (Housekeeping) packet.  
4. Produce an  **OBC\_SU\_HK**  packet (even if the hardware does not respond).  
5. **TURN OFF**  the unit or simulation stream to clear the communication buffer.

#### 5\. Command, Control, and Data Handling (CCDH)

##### 5.1. Command and Control Intelligence

The CCDH layer automates the transition between operational states and ensures raw NMEA data is safely converted into non-volatile storage.

##### 5.2. Command Packet Structure (Req: GPS-SW-0170)

The system shall utilize the following fixed-frame packet structure for all commands:

* **Start Byte:**  0x7E (Fixed frame start).  
* **CMD\_ID:**  1 Byte (Command identifier).  
* **LEN:**  1 Byte (Number of data bytes to follow).  
* **DATA:**  Optional (Length specified by LEN).  
* **XOR:**  1 Byte. The system shall calculate the bitwise XOR over the  **CMD\_ID, LEN, and DATA**  fields for error detection.

##### 5.3. NMEA Parsing and CSV Storage (Req: GPS-SW-0025)

The gps\_client.py implementation shall decode the $GPGGA ASCII string. The logic shall extract the Latitude, Longitude, and UTC Timestamp. These values shall be appended to telemetry.csv in a continuous loop during the SCIENCE state.

##### 5.4. Memory Management and Redundancy (Req: GPS-SW-0040)

To ensure no data loss during extended missions, the logging device shall possess at least  **two independent mass memory units** . The system shall reserve at least  **10Mbyte**  of memory per unit for science data and housekeeping logs.

#### 6\. Verification and Implementation Tasks

##### 6.1. Strategic Verification

Verification shall follow a "Read-Write-Verify" loop, utilizing an adversarial approach to test system resilience against simulated hardware failures.

##### 6.2. Task Decomposition

The following implementation tasks are required for system deployment:

1. **PTY Hardware Double:**  Implement gps\_double.py to open pty.openpty() and stream hardcoded $GPGGA NMEA sentences every 1 second.  
2. **UART Connection Logic:**  Establish the serial loop in gps\_client.py using 9600 8N1 and the mandatory 500ms timeout.  
3. **Parser and State Logic:**  Implement the ASCII NMEA parser and the state transitions governed by CMD\_ID scripts.  
4. **Error Sequence:**  Code the 5-step FIPEX-modeled recovery sequence to trigger upon SyncError.

##### 6.3. Adversarial Verification

The system shall be verified by testing the gps\_double.py output against a standard terminal (e.g., screen /dev/pts/N 9600). This ensures that telemetry generates correctly and that the client handles a sudden loss of the PTY connection without a system latch-up.

##### 6.4. Final Summary

This Requirements and Interface Control Document serves as the absolute ground truth for the GPS Telemetry System implementation. All software artifacts and verification procedures shall align with these safety and reliability standards.

&nbsp;