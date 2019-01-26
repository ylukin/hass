
The `nuvo` platform allows you to control [Nuvo Essentia 6-Zone Amplifier](https://www.legrand.us/nuvo/audio-video/wired-audio-systems/nv-e6gm.aspx) using a serial connection via [Global Cache iTach IP2SL IP-to-RS232 gateway](https://www.globalcache.com/products/itach/ip2slspecs/).

To add a Nuvo device to your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
media_player:
  - platform: nuvo
    host: 192.168.1.100
    port: 4999
    zones:
      1:
        name: Main Bedroom
      2:
        name: Living Room
      3:
        name: Kitchen
      4:
        name: Bathroom
      5:
        name: Dining Room
      6:
        name: Guest Bedroom
    sources:
      1:
        name: Sonos
      2:
        name: Chromecast
```

<dl>	
  <dt>host:</dt>
  <dd>description: The IP addres of the Global Cache IP2SL gateway device to which the Nuvo amplifier is connected to.</dd> 
  <dd>required: true</dd>
  <dd>type: string</dd>
  <dt>port:</dt>
  <dd>description: The TCP port on the Global Cache IP2SL gateway to send serial commands to. Since the IP2SL only has one serial port, the only valid option here is 4999. </dd>
  <dd>required: true</dd>
  <dd>type: string</dd>
  <dt>zones:</dt>
  <dd>description: This is the list of zones available. Valid zones are 1, 2, 3, 4, 5 or 6. Each zone must have a name assigned to it.</dd>
  <dd>required: true</dd>
  <dd>type: integer</dd>
  <dt>sources:</dt>
  <dd>description: The list of sources available. Valid source numbers are 1, 2, 3, 4, 5 or 6. Each source number corresponds to the input number on the Nuvo amplifier. Similar to zones, each source must have a name assigned to it.</dd>
  <dd>required: true</dd>
  <dd>type: integer</dd>

