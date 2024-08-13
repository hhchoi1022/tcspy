Telescope Control System with python (TCSpy) is an innovative software designed specifically for the efficient management of multiple telescopes through network-based communication. TCSpy aims to achieve several key objectives:

1. **Synchronized Operation of Multiple Telescopes Array**: TCSpy ensures seamless coordination and operation of multiple telescopes array. Through network communication, TCSpy facilitates synchronized actions among telescopes, enabling simultaneous observations.
2. **Support for Diverse Observation Modes**: TCSpy offers variety of observation modes, catering to various astronomical research needs. Using the advantage of multiple telescopes, spectroscopic observation, deep observation, and search observation modes are currently supported. 
3. **Swift Responsiveness for Follow-up Observations of Astronomical Transients**: TCSpy achieves rapid performance in responding to transient astronomical events, such as supernovae, gamma-ray bursts, or gravitational wave alerts. With its efficient communication protocols in real time, TCSpy enables astronomers to quickly follow up on transient events, capturing crucial observations.

To achieve these objectives, TCSpy leverages the ASCOM Alpaca and PWI4 HTTP API for establishing robust network-based communication framework among multiple telescopes. Through the communication, TCSpy establishes connection with a multiple telescopes array through multiple connection levels. At the lowest level, it connects ASCOM devices (camera, filterwheel, and so on) to construct the SingleTelescope instance. Multiple SingleTelescope instances are combined to form MultiTelescopes, enabling the simultaneous operation of multiple telescopes with perfect synchronization across various observation modes. Furthermore, TCSpy dynamically integrates a target database in real-time and efficient target scoring algorithm to facilitate swift execution of not only ordinary observation, but also Targets of Opportunity (ToO) observation. 

**To implement TCSpy, prerequisites include:**

1. ASCOM supported observation devices: TCSpy requires observation devices that is compatible with the ASCOM (AStronomy Common Object Model) platform.
2. Telescope Control System computer (TCS computers): Dedicated computers for each telescope are necessary for the communication between the telescope and MCS computer. For example, if there are 20 telescopes, 20 TCS computers are required. 
3. Main Control System computer (MCS computer):  MCS computer serves as a central hub for coordinating the operations of multiple telescopes, receiving commands and transmitting instructions to individual telescopes via the TCS computers.
4. Network configuration: All MCS and TCS computers must be connected to the same local network for securer and faster communication.
5. High-speed local network speed: A high-speed local network infrastructure is crucial for facilitating rapid data transfer and communication between MCS computer and multiple telescopes. 
6. (Optional) Planewave instruments: For Planewave instruments, TCSpy can establish connections solely with the focuser and mount. This connectivity is possible if the instruments support the PWI4 HTTP API. 

This documentation contains structure of TCSpy in Section 1. In section 2, Installation and configuration of TCSpy will be addressed. Section 3 will include the observation with TCSpy and user-defined application.
