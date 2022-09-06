
The `benq` platform allows you to control BenQ projectors using a serial connection via [Global Cache iTach IP2SL IP-to-RS232 gateway](https://www.globalcache.com/products/itach/ip2slspecs/).

To add a BenQ device to your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
media_player:
  - platform: benq
    host: 192.168.1.100
    port: 4999
```

<dl>	
  <dt>host:</dt>
  <dd>description: The IP address of the Global Cache IP2SL gateway device to which the Nuvo amplifier is connected to.</dd> 
  <dd>required: true</dd>
  <dd>type: string</dd>
  <dt>port:</dt>
  <dd>description: The TCP port on the Global Cache IP2SL gateway to send serial commands to. Since the IP2SL only has one serial port, the only valid option here is 4999. </dd>
  <dd>required: false</dd>
  <dd>type: string</dd>
