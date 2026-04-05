# Hardware & IoT Integration Roadmap

This roadmap outlines the long-term vision for transforming JARVIS from a desktop software agent into a physical home controller, inspired by classic JARVIS architectures.

## Phase 33.1: The Bridge Architecture
We have established `hardware/bridge.py` as our API contract. Every new smart home integration must conform to `IoTBridge`:
1. `connect()`
2. `discover_devices()`
3. `execute_action()`

## Phase 33.2: First-Party Integrations
We will target the following common ecosystem bridges first:
1. **Philips Hue (via `phue` api)**:
   - Control lighting states, color, and brightness.
   - Dynamic cinematic lighting (e.g., dimming lights when playing a video).
2. **TP-Link Kasa**:
   - Control smart plugs and relays.

## Phase 33.3: Ambient Hardware Intelligence
Going beyond just digital screens, we want JARVIS to interact with the physical room.

### 1. External Camera Vision
Integrate the current `VisionProvider` with an external webcam to detect:
- Presence (is the user at the desk?)
- Emotion/Posture (tailoring responses).

### 2. Environmental Sensors
- Receive data from DHT11/DHT22 sensors (if connected via Arduino/Raspberry Pi Serial).

## Implementation Rules
1. All hardware triggers must be non-blocking. Use the `EventBus` to emit signals (e.g., `device_state_changed`).
2. API Keys or IP addresses for bridges (e.g., `HUE_BRIDGE_IP`) must be stored in `.env`.
