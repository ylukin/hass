# Nuvo Multi-Zone Amplifier

The `nuvo` integration allows you to control [Nuvo Essentia 6-Zone Amplifier](https://www.legrand.us/nuvo/audio-video/wired-audio-systems/nv-e6gm.aspx) using a serial connection via [Global Cache iTach IP2SL IP-to-RS232 gateway](https://www.globalcache.com/products/itach/ip2slspecs/).

## Installation

This is a custom component and is not included in Home Assistant core. You must install it manually before you can configure it.

1. Copy the entire `nuvo` folder from this repository into your Home Assistant configuration directory:
   ```
   /config/custom_components/nuvo/
   ```

2. Restart Home Assistant to load the custom component

3. Once Home Assistant restarts, you can proceed with configuration (see below)

## Configuration

This integration is configured via the Home Assistant UI.

### Adding the Integration

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for **Nuvo Multi-Zone Amplifier**
4. Enter the connection details:
   - **Name**: Friendly name for this integration (optional, defaults to "Nuvo E6G")
   - **Host**: IP address of the Global Cache IP2SL gateway
   - **Port**: TCP port on the IP2SL gateway (default: 4999)
   - **Zones**: Names for each zone (1-6) you want to use
   - **Sources**: Names for each source (1-6) you want to use

### Configuration Options

- **host** (required): The IP address of the Global Cache IP2SL gateway device to which the Nuvo amplifier is connected
- **port** (required): The TCP port on the Global Cache IP2SL gateway to send serial commands to. Since the IP2SL only has one serial port, use 4999
- **zones**: Names for zones 1-6. Each zone you configure will appear as a separate media player entity
- **sources**: Names for sources 1-6. Each source number corresponds to the input number on the Nuvo amplifier

### Modifying Configuration

You can modify zone and source names after setup:

1. Go to **Settings** > **Devices & Services**
2. Find the **Nuvo Multi-Zone Amplifier** integration
3. Click **Configure**
4. Update zone and source names as needed

### YAML Import (Legacy)

For backward compatibility, YAML configuration is still supported but will be automatically imported to a UI config entry:

```yaml
# Legacy configuration.yaml entry (will be imported)
media_player:
  - platform: nuvo
    host: 192.168.1.100
    port: 4999
    zones:
      1:
        name: Main Bedroom
      2:
        name: Living Room
    sources:
      1:
        name: Sonos
      2:
        name: Chromecast
```

After import, you can remove this from your configuration.yaml and manage the integration via the UI.
