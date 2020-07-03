
The `hai` platform allows you to control [HAI (Leviton) Omni home automation system](https://www.leviton.com/en/products/20a00-2) via [hai-proxy](https://github.com/ylukin/hai-proxy).

Here's an example of `hai` lights in `configuration.yaml` file:

```yaml
light:
  - platform: hai
    host: hai.mydomain.com
    devices:
      - id: 20
        name: Living Room
      - id: 30
        name: Family Room
```

Here's an example of `hai` zones in the `configuration.yaml` file: 

```yaml
binary_sensor:
  - platform: hai
    host: hai.mydomain.com
    zone:
      - id: 10
        name: Garage Door
        device_class: garage_door
      - id: 20
        name: Front Door
        device_class: door
```


<dl>	
  <dt>host:</dt>
  <dd>description: The host name or IP address of the hai-proxy API (Docker container).</dd> 
  <dd>required: true</dd>
  <dd>type: string</dd>
  <dt>id:</dt>
  <dd>description: This is the unit/zone ID as configured in the HAI Omni controller. Valid IDs are 1-255. Each unit/zone must have a name assigned to it.</dd>
  <dd>required: true</dd>
  <dd>type: integer</dd>

