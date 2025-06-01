# Changelog

All notable changes to the Balena Cloud Home Assistant integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### ✨ Added
- Initial release preparation

## [1.0.0] - 2024-12-19

### ✨ Added
- Complete Balena Cloud Home Assistant integration
- Official Balena SDK integration (balena-sdk>=15.0.0)
- Real-time device monitoring with sensors for:
  - CPU usage percentage
  - Memory usage and percentage
  - Storage usage and percentage
  - Device temperature
  - Online/offline status
- Device control capabilities:
  - Restart applications
  - Reboot devices
  - Shutdown devices
  - Enable/disable device public URLs
- Fleet management features:
  - Multi-fleet support
  - Bulk device operations
  - Fleet health monitoring
- Binary sensors for device status:
  - Online/offline detection
  - Update status monitoring
  - Service health checks
- Button entities for quick actions:
  - One-click device restart
  - Application restart
  - Device reboot
  - Device shutdown
- 15 comprehensive Home Assistant services:
  - `balena_cloud.restart_application`
  - `balena_cloud.reboot_device`
  - `balena_cloud.shutdown_device`
  - `balena_cloud.enable_device_url`
  - `balena_cloud.disable_device_url`
  - `balena_cloud.get_device_url`
  - And 9 more device management services
- Comprehensive configuration flow with:
  - API token validation
  - Fleet selection interface
  - Error handling and validation
- Advanced options management:
  - Configurable update intervals (10-3600 seconds)
  - Include/exclude offline devices
  - Real-time configuration updates
- Professional integration features:
  - Official Balena logo and branding
  - HACS (Home Assistant Community Store) support
  - Comprehensive documentation
  - Professional GitHub repository structure

### 🔧 Technical Features
- Async/await pattern throughout for optimal performance
- Retry mechanisms with exponential backoff
- Rate limiting compliance with Balena Cloud API
- Comprehensive error handling and logging
- Input validation and sanitization
- Secure API token handling
- Memory-efficient data processing
- Real-time coordinator updates
- Device availability tracking
- Automatic offline device handling

### 📚 Documentation
- Comprehensive README with installation guides
- HACS integration instructions
- Manual installation procedures
- Configuration examples and use cases
- API token setup guide
- Troubleshooting documentation
- Developer contribution guidelines

### 🧪 Testing
- Comprehensive test suite with 127 tests
- Unit tests for all major components
- Integration tests with mocked Balena API
- Cross-platform compatibility testing
- End-to-end workflow testing
- Security validation testing
- Performance and reliability testing
- GitHub Actions CI/CD pipeline

### 🛡️ Security
- Secure API token storage and handling
- Input validation and sanitization
- Rate limiting and request throttling
- No sensitive data exposure in logs
- Secure credential management
- API authentication best practices

### 🏠 Home Assistant Integration
- Native Home Assistant device integration
- Device registry integration with proper device info
- Entity registry with unique IDs
- Proper entity naming and categorization
- Device class assignments for sensors
- Icon assignments using Material Design Icons
- Integration with Home Assistant automations
- Support for Home Assistant 2023.1.0+

### 📦 Installation & Distribution
- HACS integration for easy installation
- Manual installation support
- Automated release pipeline with GitHub Actions
- Professional release packages
- Comprehensive installation documentation
- Icon hosting via GitHub repository