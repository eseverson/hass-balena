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
- **Public URLs**: Enable/disable public device URLs for remote access
- **Environment Variables**: Update device environment variables

### 🌐 **Services Available**
- `balena_cloud.restart_application` - Restart device applications
- `balena_cloud.reboot_device` - Reboot devices
- `balena_cloud.shutdown_device` - Shutdown devices
- `balena_cloud.enable_device_url` - Enable public device URLs
- `balena_cloud.disable_device_url` - Disable public device URLs
- `balena_cloud.get_device_url` - Get device public URLs
- `balena_cloud.update_environment` - Update environment variables
- `balena_cloud.bulk_restart` - Bulk restart operations
- `balena_cloud.bulk_reboot` - Bulk reboot operations

### 📱 **Entity Types**
- **Sensors**: CPU, memory, storage, temperature metrics
- **Binary Sensors**: Device connectivity and update status
- **Switches**: Device power management
- **Buttons**: Quick actions (restart, reboot, shutdown, URL management)

## 🏗️ **Architecture**

This integration uses the **official Balena SDK** (`balena-sdk>=15.0.0`) for reliable, robust communication with Balena Cloud APIs.

### **Benefits of SDK Migration:**
- ✅ **Official Support**: Maintained by Balena team
- ✅ **Better Error Handling**: Comprehensive exception handling
- ✅ **Automatic Retries**: Built-in retry logic for reliability
- ✅ **Future-Proof**: Access to new Balena features as they're released

## 📦 Installation

### **Option 1: Manual Installation**

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

### **Option 2: HACS Installation** *(Coming Soon)*

*This integration will be available through HACS in the future.*

## ⚙️ Configuration

1. **Get API Token**:
   - Go to [Balena Cloud Dashboard](https://dashboard.balena-cloud.com/)
   - Navigate to Account Settings → Access tokens
   - Create a new API token

2. **Add Integration**:
   - Go to Settings → Devices & Services
   - Click "Add Integration"
   - Search for "Balena Cloud"
   - Enter your API token
   - Select the fleets you want to monitor

3. **Configure Options**:
   - **Update Interval**: How often to poll for device updates (10-3600 seconds)
   - **Include Offline Devices**: Whether to show offline devices

## 🎯 Use Cases

### **IoT Fleet Management**
- Monitor device health across your IoT deployment
- Quick troubleshooting with remote restart/reboot capabilities
- Track resource usage and performance metrics

### **Development & Testing**
- Restart applications during development cycles
- Monitor device performance during testing
- Manage environment variables for different configurations

### **Production Monitoring**
- Real-time alerts for device connectivity issues
- Performance monitoring and resource tracking
- Remote maintenance capabilities

## 🔧 Configuration Example

```yaml
# Example automation to restart device if CPU usage is too high
automation:
  - alias: "Restart high CPU device"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_device_cpu_usage
        above: 90
        for: "00:05:00"
    action:
      - service: balena_cloud.restart_application
        data:
          device_uuid: "{{ state_attr('sensor.my_device_cpu_usage', 'device_uuid') }}"
```

## 🛠️ Development

### **Requirements**
- Home Assistant 2023.1+
- Python 3.11+
- Balena Cloud account with API access

### **Local Development**
```bash
# Clone repository
git clone https://github.com/eseverson/hass-balena.git

# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```

## 📝 Changelog

### **v1.0.0**
- ✨ **Complete SDK Migration**: Migrated from direct HTTP calls to official `balena-sdk`
- 🎨 **Official Branding**: Added Balena logo and proper visual identity
- 🔧 **Enhanced Features**: Added device URL management and shutdown capabilities
- 🐛 **Bug Fixes**: Resolved Home Assistant compatibility issues
- 📚 **Improved Documentation**: Comprehensive setup and usage guides

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Balena Team**: For the excellent IoT platform and SDK
- **Home Assistant Community**: For the amazing home automation platform
- **Contributors**: Everyone who helped improve this integration

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/eseverson/hass-balena/issues)
- **Documentation**: [GitHub Wiki](https://github.com/eseverson/hass-balena/wiki)
- **Balena Documentation**: [Balena Docs](https://www.balena.io/docs/)

---

**Made with ❤️ for the Home Assistant and Balena communities**