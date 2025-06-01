# 🚀 Balena Cloud Integration for Home Assistant

[![GitHub Release](https://img.shields.io/github/release/eseverson/hass-balena.svg?style=flat-square)](https://github.com/eseverson/hass-balena/releases)
[![GitHub](https://img.shields.io/github/license/eseverson/hass-balena.svg?style=flat-square)](LICENSE)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/custom-components/hacs)

A comprehensive Home Assistant integration for monitoring and managing your Balena Cloud IoT devices.

## 🔔 Features

### 📊 **Device Monitoring**
- **Real-time Status**: Online/offline status with last seen timestamps
- **System Metrics**: CPU usage, memory usage, storage usage, and temperature
- **Fleet Management**: Organize and monitor devices by fleet
- **Device Information**: Hardware details, OS version, supervisor version

### 🎛️ **Device Control**
- **Application Management**: Restart applications and individual services
- **Device Operations**: Reboot and shutdown devices remotely
- **Public URL Management**: Toggle public device URLs with state visibility
- **Environment Variables**: Update device environment variables
- **Bulk Operations**: Manage multiple devices or entire fleets at once

### 🌐 **Services Available**
- `balena_cloud.restart_application` - Restart device applications (with optional service selection)
- `balena_cloud.reboot_device` - Reboot devices (with force option)
- `balena_cloud.shutdown_device` - Shutdown devices (with force option)
- `balena_cloud.update_environment` - Update device environment variables
- `balena_cloud.enable_device_url` - Enable public device URLs
- `balena_cloud.disable_device_url` - Disable public device URLs
- `balena_cloud.get_device_url` - Get device public URL
- `balena_cloud.bulk_restart` - Bulk restart applications across devices or fleets
- `balena_cloud.bulk_reboot` - Bulk reboot devices across fleets

### 📱 **Entity Types**
- **Sensors**: CPU percentage, memory percentage, storage percentage, temperature, fleet information, IP address, MAC address
- **Binary Sensors**: Device connectivity and update status
- **Switches**: Public URL management and device power control
- **Buttons**: Quick actions (restart, reboot, shutdown)

## 📦 Installation

### **Option 1: HACS Installation** *(Recommended)*

1. **Open HACS** in your Home Assistant instance
2. **Go to "Integrations"**
3. **Click "Explore & Download Repositories"**
4. **Search for "Balena Cloud"**
5. **Download and restart Home Assistant**
6. **Add the integration** via Settings → Devices & Services

### **Option 2: Manual Installation**

1. **Download** the integration:
   ```bash
   git clone https://github.com/eseverson/hass-balena.git
   cd hass-balena
   ```

2. **Install** to Home Assistant:
   ```bash
   chmod +x install_local.sh
   ./install_local.sh
   ```

3. **Restart** Home Assistant completely

## ⚙️ Configuration

1. **Get API Token**:
   - Go to [Balena Cloud Dashboard](https://dashboard.balena-cloud.com/)
   - Navigate to Account Settings → Access tokens
   - Create a new API token with appropriate scope

2. **Add Integration**:
   - Go to Settings → Devices & Services
   - Click "Add Integration"
   - Search for "Balena Cloud"
   - Enter your API token
   - Select the fleets you want to monitor

3. **Configure Options**:
   - **Update Interval**: How often to poll for device updates (10-3600 seconds, default: 30)
   - **Include Offline Devices**: Whether to show offline devices (default: true)

## 🎯 Use Cases & Examples

### **IoT Fleet Management**
Monitor device health across your IoT deployment and automate maintenance:

```yaml
# Monitor fleet health and get notifications
automation:
  - alias: "Fleet Health Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.fleet_overview_offline_devices
        above: 5
    action:
      - service: notify.mobile_app
        data:
          title: "Fleet Alert"
          message: "{{ trigger.to_state.state }} devices are offline"

# Auto-restart devices with high CPU usage
automation:
  - alias: "Auto-restart high CPU devices"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_device_cpu_percentage
        above: 95
        for: "00:10:00"
    action:
      - service: balena_cloud.restart_application
        data:
          device_uuid: "{{ state_attr('sensor.my_device_cpu_percentage', 'device_uuid') }}"
          confirm: true
```

### **Development & Testing**
Streamline your development workflow:

```yaml
# Restart development fleet after code push
automation:
  - alias: "Restart dev fleet on deployment"
    trigger:
      - platform: webhook
        webhook_id: "github_deploy"
    action:
      - service: balena_cloud.bulk_restart
        data:
          fleet_id: 1234567
          service_name: "main"
          confirm: true

# Toggle public URLs for demo devices
script:
  demo_enable:
    alias: "Enable Demo URLs"
    sequence:
      - service: switch.turn_on
        target:
          entity_id:
            - switch.demo_device_1_public_url
            - switch.demo_device_2_public_url
```

### **Production Monitoring**
Keep your production environment healthy:

```yaml
# Temperature monitoring with alerts
automation:
  - alias: "High temperature alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.production_device_temperature
        above: 70
    action:
      - service: notify.slack
        data:
          message: "🔥 Device {{ state_attr('sensor.production_device_temperature', 'device_name') }} temperature: {{ states('sensor.production_device_temperature') }}°C"

# Automatic environment variable updates
automation:
  - alias: "Update device timezone"
    trigger:
      - platform: state
        entity_id: input_select.timezone
    action:
      - service: balena_cloud.update_environment
        data:
          device_uuid: "{{ state_attr('binary_sensor.my_device_online', 'device_uuid') }}"
          variables:
            TZ: "{{ states('input_select.timezone') }}"
```

## 🛠️ Development

### **Requirements**
- Home Assistant 2023.1.0 or newer
- Python 3.11+
- Balena Cloud account with API access
- Balena SDK 15.0.0+

### **Local Development**
```bash
# Clone repository
git clone https://github.com/eseverson/hass-balena.git
cd hass-balena

# Install development dependencies
pip install -r tests/requirements.txt

# Run tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_units.py -v       # Unit tests
python -m pytest tests/test_integration.py -v # Integration tests
```

### **Local Validation**

Run the validation script to check your changes:

```bash
python scripts/validate_local.py
```

This validates:
- ✅ Manifest configuration
- ✅ Services configuration
- ✅ Test dependencies
- ✅ Code quality checks

### **Testing with Real Devices**

For testing with actual Balena devices:

```bash
# Set your API token
export BALENA_API_TOKEN="your_token_here"

# Run integration tests (requires real devices)
python -m pytest tests/test_api_integration.py -v --token=$BALENA_API_TOKEN
```

### **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`python -m pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 🔧 Troubleshooting

### **Common Issues**

**Authentication Errors**
- Verify your API token has appropriate permissions
- Check that the token hasn't expired
- Ensure your Balena Cloud account has access to the fleets

**Device Not Showing**
- Verify devices are online and connected to Balena Cloud
- Check if "Include Offline Devices" option is enabled
- Ensure the selected fleets contain the expected devices

**High CPU Usage**
- Increase the update interval in integration options
- Disable monitoring for offline devices if not needed
- Check Home Assistant logs for API rate limiting

### **Enable Debug Logging**

Add to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.balena_cloud: debug
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Balena Team**: For the excellent IoT platform and comprehensive SDK
- **Home Assistant Community**: For the amazing home automation platform
- **Contributors**: Everyone who helped improve this integration

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/eseverson/hass-balena/issues)
- **Discussions**: [GitHub Discussions](https://github.com/eseverson/hass-balena/discussions)
- **Documentation**: [GitHub Wiki](https://github.com/eseverson/hass-balena/wiki)
- **Balena Documentation**: [Balena Docs](https://www.balena.io/docs/)

---

**Made with ❤️ for the Home Assistant and Balena communities**